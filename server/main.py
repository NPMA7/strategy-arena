"""Strategy Arena — FastAPI orchestrator.

Komponen:
  BinanceFeed  : stream trade semua pair USDT di daftar teratas
  Engine       : 53 strategi, bar tertutup → sinyal → order → akun
  Postgres     : candles, akun, posisi, trade, kurva ekuitas, event
  /ws           : push kondisi arena tiap 1 detik ke UI
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Depends, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .bars import BarRing
from .binance import BinanceFeed
from .db import DB
from .engine import Engine, START_EQUITY, MIN_BARS, calculate_forex_pnl
from .forex_feed import ForexFeed
from .strategies import FOREX_PAIRS, FOREX_STRATEGIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s | %(message)s")
log = logging.getLogger("arena")

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
from .config import START_EQUITY, SNAPSHOT_SEC, ADMIN_RESET_KEY, get_client_config
PRICE_TICK_SEC = 0.5

db = DB()
rings: dict[str, BarRing] = {}
spot_engine: Engine | None = None
futures_engine: Engine | None = None
forex_engine: Engine | None = None
feed: BinanceFeed | None = None
forex_feed: ForexFeed | None = None
futures_symbols: set[str] = set()  # symbols eligible for futures trading
forex_symbols: set[str] = set(FOREX_PAIRS)
state = {
    "started": time.time(),
    "last_publish": 0.0,
    "pending_db": None,
    "public_api_key": "pk_live_strategyarena_public_feed",
}


class SignalHub:
    """WebSocket Hub khusus untuk stream sinyal copy-trading real-time."""

    def __init__(self) -> None:
        self.clients: dict[WebSocket, dict] = {}
        self.lock = asyncio.Lock()

    async def add(self, ws: WebSocket, filter_opts: dict) -> None:
        async with self.lock:
            self.clients[ws] = filter_opts

    async def drop(self, ws: WebSocket) -> None:
        async with self.lock:
            self.clients.pop(ws, None)

    async def broadcast_signal(self, sig: dict) -> None:
        async with self.lock:
            if not self.clients:
                return
            dead = []
            msg = _dumps({"type": "signal", "signal": sig})
            for ws, opts in list(self.clients.items()):
                strat = opts.get("strategy")
                mode = opts.get("mode")
                if strat and strat != "all":
                    allowed_strats = {s.strip() for s in strat.split(",")} if "," in strat else {strat}
                    if sig.get("strategy") not in allowed_strats:
                        continue
                if mode and mode != "all" and sig.get("mode") != mode:
                    continue
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.clients.pop(ws, None)


signal_hub = SignalHub()


class Hub:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def add(self, ws: WebSocket) -> None:
        async with self.lock:
            self.clients.add(ws)

    async def drop(self, ws: WebSocket) -> None:
        async with self.lock:
            self.clients.discard(ws)

    async def broadcast(self, payload: str) -> None:
        async with self.lock:
            dead = []
            for ws in self.clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.clients.discard(ws)


hub = Hub()


async def on_trade(symbol: str, price: float, qty: float, ts_ms: float) -> None:
    ring = rings.get(symbol)
    if ring is None:
        ring = rings[symbol] = BarRing(offset_ms=(abs(hash(symbol)) % 60) * 1000)
    bar_closed = ring.on_trade(ts_ms, price, qty)
    if bar_closed:
        # Spot engine processes ALL crypto pairs
        if spot_engine is not None and symbol not in forex_symbols:
            spot_engine.on_bar_closed(symbol, ring.views(), price)
        # Futures engine only processes futures-eligible crypto pairs
        if futures_engine is not None and symbol in futures_symbols:
            futures_engine.on_bar_closed(symbol, ring.views(), price)
        # Forex engine processes forex pairs
        if forex_engine is not None and symbol in forex_symbols:
            forex_engine.on_bar_closed(symbol, ring.views(), price)
    # Check stops on engines every tick
    if spot_engine is not None and symbol not in forex_symbols:
        spot_engine.check_stops(symbol, price)
    if futures_engine is not None and symbol in futures_symbols:
        futures_engine.check_stops(symbol, price)
    if forex_engine is not None and symbol in forex_symbols:
        forex_engine.check_stops(symbol, price)


def get_all_prices() -> dict[str, float]:
    """Mengumpulkan harga terakhir dari ring buffer, dengan fallback ke ticker 24j
    sehingga tidak pernah ada pair yang kosong (—)."""
    out: dict[str, float] = {}
    if feed:
        for p in feed.pairs():
            sym = p["symbol"]
            r = rings.get(sym)
            if r and r.n > 0 and r.last_close > 0:
                out[sym] = round(r.last_close, 8)
            elif p.get("last_close"):
                out[sym] = round(float(p["last_close"]), 8)
    if forex_feed:
        for p in forex_feed.pairs():
            sym = p["symbol"]
            r = rings.get(sym)
            dec = p.get("digits") or (5 if ("JPY" in sym or sym in ("USOIL", "XTIUSD")) else (2 if sym == "XAUUSD" else 5))
            if r and r.n > 0 and r.last_close > 0:
                out[sym] = round(r.last_close, dec)
            elif p.get("last_close"):
                out[sym] = round(float(p["last_close"]), dec)
    for s, r in rings.items():
        if r.n > 0 and r.last_close > 0 and s not in out:
            out[s] = round(r.last_close, 8)
    return out


_cached_db_size = "166.7 MB"


def build_live_state_payload() -> dict:
    if spot_engine is None or futures_engine is None:
        return {"type": "state", "spot": None, "futures": None, "forex": None}
    now = time.time()
    spot_snap = spot_engine.snapshot()
    fut_snap = futures_engine.snapshot()
    forex_snap = forex_engine.snapshot() if forex_engine else {"accounts": [], "positions": [], "curves": {}}
    prices = get_all_prices()
    for a in spot_snap["accounts"]:
        a["balance"] = round(a.get("cash", a["equity"]), 2)
        a["ret"] = a["balance"] / START_EQUITY - 1.0
    for a in fut_snap["accounts"]:
        a["balance"] = round(a.get("cash", a["equity"]), 2)
        a["ret"] = a["balance"] / START_EQUITY - 1.0
    for a in forex_snap["accounts"]:
        a["balance"] = round(a.get("cash", a["equity"]), 2)
        a["ret"] = a["balance"] / START_EQUITY - 1.0
    return {
        "type": "state",
        "t": int(now * 1000),
        "uptime": int(now - state["started"]),
        "config": get_client_config(),
        "db_size": _cached_db_size,
        "feed": {
            "connected": (feed.connected if feed else False) or (forex_feed.connected if forex_feed else False),
            "symbols": (len(feed.symbols) if feed else 0) + (len(forex_symbols) if forex_feed else 0),
            "messages": (feed.messages if feed else 0) + (forex_feed.ticks_count if forex_feed else 0),
            "last_msg_age": round(now - feed.last_msg, 2) if feed and feed.last_msg else None,
            "db_size": _cached_db_size,
        },
        "stats": {
            "bars": spot_engine.bars_processed + (forex_engine.bars_processed if forex_engine else 0),
            "spot_signals": spot_engine.signal_count,
            "futures_signals": futures_engine.signal_count,
            "forex_signals": forex_engine.signal_count if forex_engine else 0,
            "db_size": _cached_db_size,
        },
        "prices": prices,
        "pairs": (feed.pairs() if feed else []) + (forex_feed.pairs() if forex_feed else []),
        "spot": {"accounts": spot_snap["accounts"], "positions": spot_snap["positions"], "curves": spot_snap.get("curves", {}), "events": spot_engine.events[-40:], "pairs": feed.pairs() if feed else []},
        "futures": {"accounts": fut_snap["accounts"], "positions": fut_snap["positions"], "curves": fut_snap.get("curves", {}), "events": futures_engine.events[-40:], "pairs": feed.get_futures_pairs() if feed else []},
        "forex": {"accounts": forex_snap["accounts"], "positions": forex_snap["positions"], "curves": forex_snap.get("curves", {}), "events": forex_engine.events[-40:] if forex_engine else [], "pairs": forex_feed.pairs() if forex_feed else []},
    }


async def publisher() -> None:
    """Kirim state semua mode ke UI dan persist snapshot semua engine ke Postgres."""
    global _cached_db_size
    last_trade_flush = 0.0
    while True:
        try:
            await asyncio.sleep(PRICE_TICK_SEC)
            if spot_engine is None or futures_engine is None:
                continue
            now = time.time()
            payload = build_live_state_payload()
            await hub.broadcast(_dumps(payload))

            # Persist snapshot periodik ketiga engine (spot, futures, forex) dan sinyal copy-trade
            if now - last_trade_flush >= SNAPSHOT_SEC:
                last_trade_flush = now
                spot_snap = spot_engine.snapshot()
                fut_snap = futures_engine.snapshot()
                forex_snap = forex_engine.snapshot() if forex_engine else {"accounts": [], "positions": [], "curves": {}}
                spot_flushed = spot_engine.drain()
                fut_flushed = futures_engine.drain()
                forex_flushed = forex_engine.drain() if forex_engine else {}

                # Siarkan sinyal baru ke WebSocket /ws/signals
                all_signals = spot_flushed.get("new_signals", []) + fut_flushed.get("new_signals", []) + forex_flushed.get("new_signals", [])
                for sig in all_signals:
                    asyncio.create_task(signal_hub.broadcast_signal(sig))

                snap_data = {
                    "spot": {
                        "accounts": spot_snap["accounts"],
                        "positions": spot_snap["positions"],
                        **spot_flushed,
                    },
                    "futures": {
                        "accounts": fut_snap["accounts"],
                        "positions": fut_snap["positions"],
                        **fut_flushed,
                    },
                    "forex": {
                        "accounts": forex_snap["accounts"],
                        "positions": forex_snap["positions"],
                        **forex_flushed,
                    },
                    "new_events": spot_engine.events[-10:] + futures_engine.events[-10:] + (forex_engine.events[-10:] if forex_engine else []),
                }
                try:
                    await db.persist_snapshots(snap_data)
                    _cached_db_size = await db.get_db_size_str()
                except Exception as exc:
                    log.warning("persist gagal: %s", exc)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            log.error("publisher loop error: %s", exc, exc_info=True)


def _dumps(obj) -> str:
    import json
    return json.dumps(obj, separators=(",", ":"), default=str)


async def pair_refresh_loop() -> None:
    """Perbarui pair dan auto-seed pair baru yang masuk ke peringkat volume."""
    while True:
        await asyncio.sleep(60)
        if feed:
            try:
                pairs = feed.pairs()
                await db.upsert_pairs(pairs)
                # Auto-seed pair baru yang belum ada candle di ring buffer
                unseeded = [s for s in feed.symbols if s not in rings or rings[s].n < MIN_BARS]
                if unseeded:
                    log.info("seeding klines untuk pair baru (%d pair): %s", len(unseeded), unseeded)
                    await feed.seed_klines(unseeded, rings, limit=250)
            except Exception as exc:
                log.warning("upsert/seed pairs gagal: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global spot_engine, futures_engine, forex_engine, feed, forex_feed, futures_symbols, forex_symbols
    connected = False
    for attempt in range(30):
        try:
            await db.connect()
            connected = True
            break
        except Exception as exc:
            log.warning("menunggu postgres (%d): %s", attempt + 1, exc)
            await asyncio.sleep(2)
    if not connected:
        raise RuntimeError("Postgres tidak tersedia")

    # Pulihkan started_at dari DB agar uptime tidak ter-reset saat restart
    saved_started = await db.get_meta("started_at")
    if saved_started:
        try:
            state["started"] = float(saved_started)
            log.info("Memulihkan started_at: %.0f (uptime kontinu)", state["started"])
        except Exception:
            state["started"] = time.time()
            await db.set_meta("started_at", str(state["started"]))
    else:
        state["started"] = time.time()
        await db.set_meta("started_at", str(state["started"]))

    # Dapatkan public API key dari DB
    state["public_api_key"] = await db.get_public_api_key()

    # Triple engine: spot (long only) + futures (long/short, leverage, funding) + forex (22 pairs, 22 strats)
    spot_engine = Engine(rings, mode="spot")
    futures_engine = Engine(rings, mode="futures")
    forex_engine = Engine(rings, mode="forex")

    # Pulihkan saldo, trade, drawdowns, dan posisi terbuka dari PostgreSQL
    saved_state = await db.load_full_state()
    if saved_state.get("spot_accounts"):
        spot_engine.restore_state(
            saved_state["spot_accounts"],
            saved_state.get("spot_positions", []),
            saved_state.get("spot_curves", {})
        )
        log.info("Engine spot dipulihkan: %d akun, %d posisi", len(saved_state["spot_accounts"]), len(saved_state.get("spot_positions", [])))
    if saved_state.get("futures_accounts"):
        futures_engine.restore_state(
            saved_state["futures_accounts"],
            saved_state.get("futures_positions", []),
            saved_state.get("futures_curves", {})
        )
        log.info("Engine futures dipulihkan: %d akun, %d posisi", len(saved_state["futures_accounts"]), len(saved_state.get("futures_positions", [])))
    if saved_state.get("forex_accounts"):
        forex_engine.restore_state(
            saved_state["forex_accounts"],
            saved_state.get("forex_positions", []),
            saved_state.get("forex_curves", {})
        )
        log.info("Engine forex dipulihkan: %d akun, %d posisi", len(saved_state["forex_accounts"]), len(saved_state.get("forex_positions", [])))

    # Start Forex Feed & seed 240 M1 bars into rings so indicators can run immediately
    forex_feed = ForexFeed(on_trade)
    forex_feed.seed_rings(rings)
    for a in forex_engine.accounts.values():
        a["warmed"] = True
    await forex_feed.start()
    log.info("Forex feed aktif: %d pair (%d strategi)", len(forex_symbols), len(forex_engine.accounts))

    # Binance Crypto Feed
    feed = BinanceFeed(on_trade)
    try:
        await feed.start()
        await db.upsert_pairs(feed.pairs())
        # Seed historical 1m bars so MIN_BARS (210) is satisfied immediately
        await feed.seed_klines(feed.symbols, rings, limit=250)

        # Get futures-specific pairs (auto-filtered from spot by known futures bases)
        futures_pairs = feed.get_futures_pairs()
        futures_symbols = {p["symbol"] for p in futures_pairs}
        log.info("futures pairs: %d / %d spot pairs", len(futures_symbols), len(feed.symbols))

        # Mark accounts warmed since historical klines are already seeded in ring buffer
        for a in spot_engine.accounts.values():
            a["warmed"] = True
        for a in futures_engine.accounts.values():
            a["warmed"] = True
        log.info("crypto feed seeded & accounts warmed: %d pair", len(feed.symbols))
    except Exception as exc:
        log.error("gagal memulai feed Binance: %r", exc, exc_info=True)

    tasks = [
        asyncio.create_task(publisher(), name="publisher"),
        asyncio.create_task(pair_refresh_loop(), name="pairs"),
    ]
    total_strats = len(spot_engine.accounts) + len(futures_engine.accounts) + len(forex_engine.accounts)
    log.info("arena siap — %d crypto + %d forex pair, %d strategi across 3 mode (spot+futures+forex)",
             len(feed.symbols) if feed else 0, len(forex_symbols), total_strats)
    yield
    for t in tasks:
        t.cancel()
    if forex_feed:
        await forex_feed.stop()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Strategy Arena", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "db_size": _cached_db_size,
        "feed_connected": (feed.connected if feed else False) or (forex_feed.connected if forex_feed else False),
        "symbols": (len(feed.symbols) if feed else 0) + (len(forex_symbols) if forex_feed else 0),
        "bars": (spot_engine.bars_processed if spot_engine else 0) + (forex_engine.bars_processed if forex_engine else 0),
        "messages": (feed.messages if feed else 0) + (forex_feed.ticks_count if forex_feed else 0),
        "clients": len(hub.clients),
        "uptime": int(time.time() - state["started"]),
        "spot_signals": spot_engine.signal_count if spot_engine else -1,
        "futures_signals": futures_engine.signal_count if futures_engine else -1,
        "forex_signals": forex_engine.signal_count if forex_engine else -1,
        "spot_engine_id": id(spot_engine),
        "futures_engine_id": id(futures_engine),
        "forex_engine_id": id(forex_engine),
        "spot_mode": spot_engine.mode if spot_engine else None,
        "futures_mode": futures_engine.mode if futures_engine else None,
        "forex_mode": forex_engine.mode if forex_engine else None,
        "spot_positions": sum(len(a["pos"]) for a in spot_engine.accounts.values()) if spot_engine else -1,
        "futures_positions": sum(len(a["pos"]) for a in futures_engine.accounts.values()) if futures_engine else -1,
        "forex_positions": sum(len(a["pos"]) for a in forex_engine.accounts.values()) if forex_engine else -1,
    }


@app.get("/api/resources")
async def resources():
    """CPU, RAM proses ini + ukuran DB."""
    import os, resource as res_mod
    try:
        # CPU & RAM dari /proc (Linux container)
        with open("/proc/self/stat") as f:
            stat = f.read().split()
        utime = int(stat[13])
        stime = int(stat[14])
        total_ticks = utime + stime
        clk_tck = os.sysconf("SC_CLK_TCK")

        with open("/proc/self/status") as f:
            status = f.read()
        vmrss = 0
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                vmrss = int(line.split()[1])  # kB
                break

        # CPU % sederhana: baca dua kali dengan jeda kecil
        cpu_pct = 0.0
        try:
            with open("/proc/self/stat") as f:
                s1 = f.read().split()
            t1 = time.monotonic()
            await asyncio.sleep(0.2)
            with open("/proc/self/stat") as f:
                s2 = f.read().split()
            t2 = time.monotonic()
            d_ticks = (int(s2[13]) + int(s2[14])) - (int(s1[13]) + int(s1[14]))
            dt = t2 - t1
            ncpu = os.cpu_count() or 1
            cpu_pct = round((d_ticks / clk_tck) / dt / ncpu * 100, 1)
        except Exception:
            pass

        ram_mb = round(vmrss / 1024, 1)
    except Exception:
        cpu_pct = 0.0
        ram_mb = 0.0

    # DB size
    db_mb = 0.0
    try:
        async with db.pool.acquire() as con:
            row = await con.fetchrow(
                "SELECT pg_database_size('arena') / (1024*1024)::float AS mb"
            )
            db_mb = round(row["mb"], 1) if row else 0.0
    except Exception:
        pass

    return {"cpu": cpu_pct, "ram_mb": ram_mb, "db_mb": db_mb}


@app.get("/api/bootstrap")
async def bootstrap():
    data = await db.read_bootstrap()
    for a in data.get("accounts", []):
        a["balance"] = round(a.get("cash", a.get("equity", START_EQUITY)), 2)
        a["ret"] = a["balance"] / START_EQUITY - 1.0
    all_strats = []
    if spot_engine:
        all_strats.extend(spot_engine.snapshot()["accounts"])
    if futures_engine:
        all_strats.extend(futures_engine.snapshot()["accounts"])
    if forex_engine:
        all_strats.extend(forex_engine.snapshot()["accounts"])
    data["strategies"] = [
        {"id": a["id"], "name": a["name"], "family": a["family"], "color": a["color"]}
        for a in all_strats
    ]
    data["stats"] = await db.stats()
    data["feed"] = {"connected": (feed.connected if feed else False) or (forex_feed.connected if forex_feed else False), "symbols": (len(feed.symbols) if feed else 0) + (len(forex_symbols) if forex_feed else 0)}
    return JSONResponse(data)


@app.get("/api/state")
async def get_live_state():
    """Endpoint HTTP polling real-time untuk menjamin web selalu terupdate tanpa refresh."""
    return JSONResponse(build_live_state_payload())


@app.get("/api/strategy/{sid}")
async def strategy_detail(sid: str, mode: str = Query("spot"), hours: int = Query(24, ge=1, le=2160), limit: int = Query(5000, ge=1, le=10000)):
    return JSONResponse(await db.read_strategy_detail(sid, mode=mode, hours=hours, limit=limit))


@app.get("/api/symbol/{symbol}")
async def symbol_bars(symbol: str, limit: int = 180):
    return JSONResponse(await db.read_symbol_bars(symbol.upper(), min(limit, 500)))


@app.get("/api/executions")
async def get_all_executions_endpoint(
    mode: str = Query("all", description="Filter mode: all, spot, futures, forex"),
    strategy: str = Query("all", description="Strategy ID or 'all'"),
    symbol: str = Query("all", description="Symbol or 'all'"),
    limit: int = Query(150, ge=1, le=500),
):
    """Feed terpadu seluruh eksekusi trade dari semua pasar (Spot, Futures, Forex), pairs, dan strategi."""
    # 1. Closed historical trades dari database
    closed_trades = await db.read_all_executions(
        mode=mode,
        strategy=strategy,
        symbol=symbol,
        limit=limit
    )

    strat_names = {}
    for eng in (spot_engine, futures_engine, forex_engine):
        if eng:
            for sid, acct in eng.accounts.items():
                strat_names[sid] = acct.get("name", sid)

    for t in closed_trades:
        t["strategy_name"] = strat_names.get(t["strategy"], t["strategy"])

    # 2. Live open positions dari active engines
    active_positions = []
    prices = get_all_prices()
    engines = []
    if mode in ("spot", "all") and spot_engine:
        engines.append(("spot", spot_engine))
    if mode in ("futures", "all") and futures_engine:
        engines.append(("futures", futures_engine))
    if mode in ("forex", "all") and forex_engine:
        engines.append(("forex", forex_engine))

    allowed_strats = {s.strip() for s in strategy.split(",")} if strategy != "all" else None
    for m_label, eng in engines:
        for sid, acct in eng.accounts.items():
            if allowed_strats is not None and sid not in allowed_strats:
                continue
            for sym, p in acct["pos"].items():
                if symbol != "all" and sym != symbol:
                    continue
                cur_px = prices.get(sym, p["entry"])
                if m_label == "forex":
                    upnl = calculate_forex_pnl(sym, p["entry"], cur_px, p["side"], p.get("lot", 0.10), prices)
                else:
                    upnl = (cur_px - p["entry"]) * p["qty"] * p["side"]
                active_positions.append({
                    "strategy": sid,
                    "strategy_name": acct.get("name", sid),
                    "mode": m_label,
                    "symbol": sym,
                    "side": p["side"],
                    "side_label": "LONG" if p["side"] == 1 else "SHORT",
                    "entry": p["entry"],
                    "mark": cur_px,
                    "qty": p["qty"],
                    "lot": p.get("lot", p["qty"]),
                    "leverage": p.get("leverage", 1),
                    "upnl": round(upnl, 2),
                    "opened_at": p.get("opened_at", 0),
                    "stop": p.get("stop"),
                    "target": p.get("target"),
                    "risk_reward": f"1:{(abs(p['target'] - p['entry']) / max(abs(p['entry'] - p['stop']), 1e-4)):.1f}" if p.get("target") and p.get("stop") else "1:1.8",
                })

    # Urutan terbaru selalu di atas (Newest opened positions first)
    active_positions.sort(key=lambda x: x.get("opened_at", 0), reverse=True)

    db_stats = await db.stats()
    return {
        "ok": True,
        "total_db_trades": db_stats.get("trades", len(closed_trades)),
        "db_size": db_stats.get("db_size", _cached_db_size),
        "open_count": len(active_positions),
        "closed_count": len(closed_trades),
        "open_positions": active_positions,
        "trades": closed_trades,
    }


@app.post("/api/reset")
async def reset_arena(
    admin_key: str | None = Query(None, description="Secret admin reset key"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
):
    """Hapus seluruh data simulasi di database dan reset semua engine (spot, futures, forex) ke state awal dari 0."""
    provided = (x_admin_key or admin_key or "").strip()
    if not ADMIN_RESET_KEY or provided != ADMIN_RESET_KEY:
        raise HTTPException(
            status_code=403,
            detail="Akses ditolak: Endpoint reset diproteksi. Masukkan admin key via header 'X-Admin-Key' atau query parameter '?admin_key=...'."
        )
    global spot_engine, futures_engine, forex_engine
    log.info("Resetting entire arena to 0 via authenticated admin key...")
    await db.clear_all_data()
    now = time.time()
    state["started"] = now
    await db.set_meta("started_at", str(now))
    spot_engine = Engine(rings, mode="spot")
    futures_engine = Engine(rings, mode="futures")
    forex_engine = Engine(rings, mode="forex")
    for a in spot_engine.accounts.values():
        a["warmed"] = True
    for a in futures_engine.accounts.values():
        a["warmed"] = True
    for a in forex_engine.accounts.values():
        a["warmed"] = True
    return {
        "ok": True,
        "message": f"Arena berhasil di-reset ke 0 (modal ${START_EQUITY:,.0f}, 0 trade, 0 MC)",
        "config": get_client_config(),
    }


@app.get("/api/config")
async def get_config():
    """Return runtime configuration derived from .env / system settings."""
    return JSONResponse(get_client_config())


# ── Copy-Trading & Public API v1 ──────────────────────────────────────────

async def get_validated_api_key(api_key: str = Query(..., description="API key (misal public key)")) -> str:
    valid = await db.verify_api_key(api_key)
    if not valid:
        raise HTTPException(status_code=401, detail="API Key tidak valid atau dinonaktifkan")
    return api_key


@app.get("/api/v1/auth/public-key")
async def get_public_key():
    """Mendapatkan public API key aktif dan informasi endpoint copy-trading."""
    pub_key = await db.get_public_api_key()
    return {
        "ok": True,
        "api_key": pub_key,
        "name": "Strategy Arena Public Copy-Trading Feed",
        "rate_limit": "60 requests/minute",
        "description": "Public API Key untuk menyalin sinyal order dan posisi aktif strategi spot & futures secara instan.",
        "endpoints": {
            "positions": "/api/v1/signals/positions?strategy={strategy_id}&mode={spot|futures}&api_key=" + pub_key,
            "feed": "/api/v1/signals/feed?strategy={strategy_id}&mode={spot|futures}&limit=50&api_key=" + pub_key,
            "strategies": "/api/v1/signals/strategies?api_key=" + pub_key,
            "websocket": "/ws/signals?strategy={strategy_id}&mode={spot|futures}&api_key=" + pub_key,
        }
    }


@app.post("/api/v1/auth/generate-key")
async def generate_custom_key(name: str = Query("My Bot Client")):
    """Membuat custom API key untuk bot pribadi."""
    clean_name = name.strip()[:60] if name else "My Bot Client"
    try:
        async with db.pool.acquire() as con:
            count = await con.fetchval("SELECT count(*) FROM api_keys")
            if count and count >= 200:
                raise HTTPException(
                    status_code=429,
                    detail="Batas kuota API key custom tercapai (maks 200). Silakan gunakan public API key default."
                )
    except HTTPException:
        raise
    except Exception as e:
        log.warning(f"Error checking api_keys count: {e}")
    key = await db.create_api_key(name=clean_name)
    return {"ok": True, "api_key": key, "name": clean_name}


@app.get("/api/v1/signals/strategies")
async def list_strategies_api(
    mode: str = Query("all", description="Mode arena: spot, futures, atau all"),
    api_key: str = Depends(get_validated_api_key)
):
    """Peringkat & performa semua strategi untuk memilih strategi terbaik yang ingin disalin."""
    out = []
    engines = []
    if mode in ("spot", "all") and spot_engine:
        engines.append(("spot", spot_engine))
    if mode in ("futures", "all") and futures_engine:
        engines.append(("futures", futures_engine))
    if mode in ("forex", "all") and forex_engine:
        engines.append(("forex", forex_engine))

    for m_label, eng in engines:
        snap = eng.snapshot()
        for a in snap["accounts"]:
            bal = round(a.get("balance", a.get("cash", a["equity"])), 2)
            out.append({
                "strategy": a["id"],
                "name": a["name"],
                "family": a["family"],
                "mode": m_label,
                "balance": bal,
                "equity": round(a["equity"], 2),
                "return_pct": round((bal / START_EQUITY - 1.0) * 100, 2),
                "trades": a["trades"],
                "win_rate_pct": round(a["wins"] / a["trades"] * 100, 1) if a["trades"] > 0 else 0.0,
                "max_drawdown_pct": round(a["max_dd"] * 100, 2),
                "mc_count": a.get("mc_count", 0),
                "open_positions": a.get("open", 0),
                "leverage": a.get("leverage", 1),
            })
    out.sort(key=lambda x: x["balance"], reverse=True)
    return {"ok": True, "total": len(out), "strategies": out}


@app.get("/api/v1/signals/positions")
async def get_active_positions_api(
    strategy: str = Query("all", description="ID strategi atau 'all'"),
    mode: str = Query("all", description="Mode: spot, futures, forex, atau all"),
    api_key: str = Depends(get_validated_api_key)
):
    """Mendapatkan posisi aktif saat ini untuk sinkronisasi portofolio bot copy-trading."""
    positions = []
    prices = get_all_prices()

    engines = []
    if mode in ("spot", "all") and spot_engine:
        engines.append(("spot", spot_engine))
    if mode in ("futures", "all") and futures_engine:
        engines.append(("futures", futures_engine))
    if mode in ("forex", "all") and forex_engine:
        engines.append(("forex", forex_engine))

    allowed_strats = {s.strip() for s in strategy.split(",")} if strategy != "all" else None
    for m_label, eng in engines:
        for sid, acct in eng.accounts.items():
            if allowed_strats is not None and sid not in allowed_strats:
                continue
            for sym, p in acct["pos"].items():
                cur_px = prices.get(sym, p["entry"])
                if m_label == "forex":
                    unrealized_pnl = calculate_forex_pnl(sym, p["entry"], cur_px, p["side"], p.get("lot", 0.10), prices)
                else:
                    unrealized_pnl = (cur_px - p["entry"]) * p["qty"] * p["side"]
                unrealized_pct = ((cur_px / p["entry"] - 1.0) * p["side"]) * p.get("leverage", 1) * 100
                positions.append({
                    "strategy": sid,
                    "strategy_name": acct["name"],
                    "mode": m_label,
                    "symbol": sym,
                    "action": "HOLD_LONG" if p["side"] == 1 else "HOLD_SHORT",
                    "side": "LONG" if p["side"] == 1 else "SHORT",
                    "entry_price": p["entry"],
                    "current_price": cur_px,
                    "stop_loss": p.get("stop"),
                    "take_profit": p.get("target"),
                    "lot": p.get("lot", p["qty"]),
                    "quantity": p["qty"],
                    "leverage": p.get("leverage", 1),
                    "notional_usd": round(p.get("notional", p["qty"] * cur_px), 2),
                    "margin_usd": round(p.get("margin_used", 0.0), 2),
                    "risk_amount_usd": round(p.get("risk_amount", 0.0), 2),
                    "unrealized_pnl_usd": round(unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(unrealized_pct, 2),
                    "opened_at": p.get("opened_at", 0),
                    "duration_sec": int(time.time() - (p.get("opened_at", 0) / 1000)) if p.get("opened_at") else 0,
                })

    return {
        "ok": True,
        "count": len(positions),
        "filter": {"strategy": strategy, "mode": mode},
        "positions": positions
    }


@app.get("/api/v1/signals/feed")
async def get_signals_feed_api(
    strategy: str = Query("all", description="ID strategi atau 'all'"),
    mode: str = Query("all", description="Mode: spot, futures, forex, atau all"),
    limit: int = Query(50, ge=1, le=200),
    action: str = Query("all", description="Filter action: OPEN, CLOSE, all"),
    api_key: str = Depends(get_validated_api_key)
):
    """Riwayat sinyal terstruktur (Open Long/Short, Close TP/SL) dari database."""
    signals = await db.read_signals(
        mode=None if mode == "all" else mode,
        strategy=None if strategy == "all" else strategy,
        action_type=None if action == "all" else action,
        limit=limit
    )
    return {
        "ok": True,
        "count": len(signals),
        "filter": {"strategy": strategy, "mode": mode, "action": action},
        "signals": signals
    }


@app.websocket("/ws/signals")
async def ws_signals_endpoint(
    ws: WebSocket,
    api_key: str = Query(""),
    strategy: str = Query("all"),
    mode: str = Query("all"),
):
    """WebSocket stream sinyal real-time untuk copy-trading otomatis tanpa polling."""
    await ws.accept()
    valid = await db.verify_api_key(api_key)
    if not valid:
        await ws.send_text(_dumps({"error": "Unauthorized", "detail": "API Key tidak valid"}))
        await ws.close(code=4001)
        return

    filter_opts = {"strategy": strategy, "mode": mode}
    await signal_hub.add(ws, filter_opts)

    # Kirim sinyal hello dengan posisi aktif saat ini
    cur_positions = []
    prices = get_all_prices()
    engines = []
    if mode in ("spot", "all") and spot_engine:
        engines.append(("spot", spot_engine))
    if mode in ("futures", "all") and futures_engine:
        engines.append(("futures", futures_engine))
    if mode in ("forex", "all") and forex_engine:
        engines.append(("forex", forex_engine))

    allowed_strats = {s.strip() for s in strategy.split(",")} if strategy != "all" else None
    for m_label, eng in engines:
        for sid, acct in eng.accounts.items():
            if allowed_strats is not None and sid not in allowed_strats:
                continue
            for sym, p in acct["pos"].items():
                cur_positions.append({
                    "strategy": sid,
                    "mode": m_label,
                    "symbol": sym,
                    "side": "LONG" if p["side"] == 1 else "SHORT",
                    "entry_price": p["entry"],
                    "current_price": prices.get(sym, p["entry"]),
                    "stop_loss": p.get("stop"),
                    "take_profit": p.get("target"),
                    "lot": p.get("lot", p["qty"]),
                    "quantity": p["qty"],
                    "leverage": p.get("leverage", 1),
                })

    try:
        await ws.send_text(_dumps({
            "type": "hello",
            "message": "Terhubung ke Strategy Arena Realtime Signal Stream",
            "subscribed": filter_opts,
            "active_positions": cur_positions
        }))
        while True:
            # Tetap jaga koneksi tetap hidup (baca ping/heartbeat dari bot)
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await signal_hub.drop(ws)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    await hub.add(ws)
    try:
        if spot_engine and futures_engine and forex_engine:
            spot_snap = spot_engine.snapshot()
            fut_snap = futures_engine.snapshot()
            forex_snap = forex_engine.snapshot()
            for a in spot_snap["accounts"]:
                a["balance"] = round(a.get("cash", a["equity"]), 2)
                a["ret"] = a["balance"] / START_EQUITY - 1.0
            for a in fut_snap["accounts"]:
                a["balance"] = round(a.get("cash", a["equity"]), 2)
                a["ret"] = a["balance"] / START_EQUITY - 1.0
            for a in forex_snap["accounts"]:
                a["balance"] = round(a.get("cash", a["equity"]), 2)
                a["ret"] = a["balance"] / START_EQUITY - 1.0
            await ws.send_text(_dumps({
                "type": "hello",
                "pairs": (feed.pairs() if feed else []) + (forex_feed.pairs() if forex_feed else []),
                "prices": get_all_prices(),
                "spot": {"accounts": spot_snap["accounts"], "positions": spot_snap["positions"], "curves": spot_snap.get("curves", {}), "events": spot_engine.events[-40:]},
                "futures": {"accounts": fut_snap["accounts"], "positions": fut_snap["positions"], "curves": fut_snap.get("curves", {}), "events": futures_engine.events[-40:], "pairs": feed.get_futures_pairs() if feed else []},
                "forex": {"accounts": forex_snap["accounts"], "positions": forex_snap["positions"], "curves": forex_snap.get("curves", {}), "events": forex_engine.events[-40:], "pairs": forex_feed.pairs() if forex_feed else []},
            }))
        while True:
            await ws.receive_text()  # ping dari klien
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await hub.drop(ws)


ASSETS_DIR = os.path.join(DIST_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/")
async def landing():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    raise HTTPException(status_code=404, detail="Frontend Svelte build tidak ditemukan. Jalankan 'npm run build' di folder frontend/")


@app.get("/crypto-spot")
async def spot_dashboard():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    raise HTTPException(status_code=404, detail="Frontend Svelte build tidak ditemukan. Jalankan 'npm run build' di folder frontend/")


@app.get("/crypto-futures")
async def futures_dashboard():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    raise HTTPException(status_code=404, detail="Frontend Svelte build tidak ditemukan. Jalankan 'npm run build' di folder frontend/")


@app.get("/forex")
async def forex_dashboard():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    raise HTTPException(status_code=404, detail="Frontend Svelte build tidak ditemukan. Jalankan 'npm run build' di folder frontend/")


@app.get("/neural-execution")
@app.get("/executions")
async def neural_executions_dashboard():
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    raise HTTPException(status_code=404, detail="Frontend Svelte build tidak ditemukan. Jalankan 'npm run build' di folder frontend/")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav = os.path.join(DIST_DIR, "favicon.ico")
    if os.path.exists(fav):
        return FileResponse(fav)
    fav_pub = os.path.join(FRONTEND_DIR, "public", "favicon.ico")
    if os.path.exists(fav_pub):
        return FileResponse(fav_pub)
    fav_svg = os.path.join(DIST_DIR, "favicon.svg")
    if os.path.exists(fav_svg):
        return FileResponse(fav_svg)
    raise HTTPException(status_code=404)


@app.get("/favicon.svg", include_in_schema=False)
async def favicon_svg():
    fav = os.path.join(DIST_DIR, "favicon.svg")
    if os.path.exists(fav):
        return FileResponse(fav)
    fav_pub = os.path.join(FRONTEND_DIR, "public", "favicon.svg")
    if os.path.exists(fav_pub):
        return FileResponse(fav_pub)
    raise HTTPException(status_code=404)


@app.get("/logo.svg", include_in_schema=False)
async def logo_svg():
    logo = os.path.join(DIST_DIR, "logo.svg")
    if os.path.exists(logo):
        return FileResponse(logo)
    logo_pub = os.path.join(FRONTEND_DIR, "public", "logo.svg")
    if os.path.exists(logo_pub):
        return FileResponse(logo_pub)
    raise HTTPException(status_code=404)

