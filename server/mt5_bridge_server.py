"""MT5 Quant Bridge Server — Dedicated Microservice untuk MetaTrader 5 (Headway-Demo).
Menyediakan REST API di port 5000 untuk 22 pair Forex & Commodities dengan data Bid, Ask, Spread riil 100% dari MetaTrader 5.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from aiohttp import web
import rpyc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] mt5-bridge: %(message)s")
log = logging.getLogger("mt5-bridge")

PORT = int(os.getenv("PORT", "5000"))
MT5_RPYC_HOST = os.getenv("MT5_RPYC_HOST", "mt5-vnc")
MT5_RPYC_PORT = int(os.getenv("MT5_RPYC_PORT", "18812"))

# 22 Pair Forex & Komoditas Strategy Arena beserta spesifikasi broker Headway
PAIRS: dict[str, dict] = {
    "EURUSD": {"name": "Euro vs US Dollar", "digits": 5, "pip": 0.0001, "base": "EUR", "quote": "USD", "broker_symbol": "EURUSD"},
    "GBPUSD": {"name": "British Pound vs USD", "digits": 5, "pip": 0.0001, "base": "GBP", "quote": "USD", "broker_symbol": "GBPUSD"},
    "USDJPY": {"name": "US Dollar vs Japanese Yen", "digits": 3, "pip": 0.01, "base": "USD", "quote": "JPY", "broker_symbol": "USDJPY"},
    "USDCHF": {"name": "US Dollar vs Swiss Franc", "digits": 5, "pip": 0.0001, "base": "USD", "quote": "CHF", "broker_symbol": "USDCHF"},
    "AUDUSD": {"name": "Aussie vs US Dollar", "digits": 5, "pip": 0.0001, "base": "AUD", "quote": "USD", "broker_symbol": "AUDUSD"},
    "USDCAD": {"name": "US Dollar vs Canadian Dollar", "digits": 5, "pip": 0.0001, "base": "USD", "quote": "CAD", "broker_symbol": "USDCAD"},
    "NZDUSD": {"name": "Kiwi vs US Dollar", "digits": 5, "pip": 0.0001, "base": "NZD", "quote": "USD", "broker_symbol": "NZDUSD"},
    "GBPJPY": {"name": "British Pound vs Japanese Yen", "digits": 3, "pip": 0.01, "base": "GBP", "quote": "JPY", "broker_symbol": "GBPJPY"},
    "EURJPY": {"name": "Euro vs Japanese Yen", "digits": 3, "pip": 0.01, "base": "EUR", "quote": "JPY", "broker_symbol": "EURJPY"},
    "AUDJPY": {"name": "Aussie vs Japanese Yen", "digits": 3, "pip": 0.01, "base": "AUD", "quote": "JPY", "broker_symbol": "AUDJPY"},
    "CADJPY": {"name": "Canadian Dollar vs Japanese Yen", "digits": 3, "pip": 0.01, "base": "CAD", "quote": "JPY", "broker_symbol": "CADJPY"},
    "CHFJPY": {"name": "Swiss Franc vs Japanese Yen", "digits": 3, "pip": 0.01, "base": "CHF", "quote": "JPY", "broker_symbol": "CHFJPY"},
    "NZDJPY": {"name": "Kiwi vs Japanese Yen", "digits": 3, "pip": 0.01, "base": "NZD", "quote": "JPY", "broker_symbol": "NZDJPY"},
    "EURGBP": {"name": "Euro vs British Pound", "digits": 5, "pip": 0.0001, "base": "EUR", "quote": "GBP", "broker_symbol": "EURGBP"},
    "EURCHF": {"name": "Euro vs Swiss Franc", "digits": 5, "pip": 0.0001, "base": "EUR", "quote": "CHF", "broker_symbol": "EURCHF"},
    "GBPCHF": {"name": "British Pound vs Swiss Franc", "digits": 5, "pip": 0.0001, "base": "GBP", "quote": "CHF", "broker_symbol": "GBPCHF"},
    "AUDNZD": {"name": "Aussie vs Kiwi", "digits": 5, "pip": 0.0001, "base": "AUD", "quote": "NZD", "broker_symbol": "AUDNZD"},
    "AUDCAD": {"name": "Aussie vs Canadian Dollar", "digits": 5, "pip": 0.0001, "base": "AUD", "quote": "CAD", "broker_symbol": "AUDCAD"},
    "EURAUD": {"name": "Euro vs Aussie", "digits": 5, "pip": 0.0001, "base": "EUR", "quote": "AUD", "broker_symbol": "EURAUD"},
    "GBPAUD": {"name": "British Pound vs Aussie", "digits": 5, "pip": 0.0001, "base": "GBP", "quote": "AUD", "broker_symbol": "GBPAUD"},
    "XAUUSD": {"name": "Gold Spot vs USD", "digits": 2, "pip": 0.1, "base": "XAU", "quote": "USD", "broker_symbol": "XAUUSD"},
    "USOIL": {"name": "WTI Crude Oil", "digits": 2, "pip": 0.01, "base": "OIL", "quote": "USD", "broker_symbol": "XTIUSD"},
}

BROKER_MAP = {k: v["broker_symbol"] for k, v in PAIRS.items()}

current_ticks: dict[str, dict] = {}
day_open_prices: dict[str, float] = {}

cached_account_info: dict = {
    "login": 6310591,
    "server": "Headway-Demo",
    "balance": 0.0,
    "connected": False,
}

_rpyc_conn = None
_last_conn_attempt = 0.0


def _sync_connect_rpyc():
    """Mengelola koneksi persisten ke server RPyC MT5 di mt5-vnc (dieksekusi di worker thread)."""
    global _rpyc_conn, _last_conn_attempt, cached_account_info
    now = time.time()
    if _rpyc_conn is not None:
        try:
            if not _rpyc_conn.closed:
                return _rpyc_conn
        except Exception:
            _rpyc_conn = None

    if now - _last_conn_attempt < 3.0:
        return None
    _last_conn_attempt = now

    try:
        log.info("Mencoba menghubungkan ke RPyC MT5 di %s:%d...", MT5_RPYC_HOST, MT5_RPYC_PORT)
        conn = rpyc.classic.connect(MT5_RPYC_HOST, MT5_RPYC_PORT)
        conn._config["sync_request_timeout"] = 60

        # Initialize MT5 and remote batch routines
        conn.execute("""
import sys
if 'C:\\\\mt5libs' not in sys.path:
    sys.path.append('C:\\\\mt5libs')
import MetaTrader5 as mt5

def _arena_init():
    ok = mt5.initialize(path="C:\\\\MT5\\\\terminal64.exe", portable=True)
    if not ok:
        ok = mt5.initialize()
    if ok:
        info = mt5.account_info()
        if not info or info.login != 6310591:
            log_res = mt5.login(6310591, password="dL7ny!PE", server="Headway-Demo")
            if not log_res:
                mt5.login(6310591, password="dL7ny!PE", server="mt5.demo.trade-hw.online:443")
    return ok

def _arena_select_symbols(symbols):
    for s in symbols:
        mt5.symbol_select(s, True)
    return True

def _arena_get_ticks(pairs_map):
    res = {}
    for arena_sym, broker_sym in pairs_map.items():
        t = mt5.symbol_info_tick(broker_sym)
        if t and t.bid > 0 and t.ask > 0:
            res[arena_sym] = (float(t.bid), float(t.ask), float(t.last), int(t.time), int(t.time_msc))
    return res

def _arena_get_bars(broker_sym, num_bars):
    rates = mt5.copy_rates_from_pos(broker_sym, mt5.TIMEFRAME_M1, 0, num_bars)
    if rates is None:
        return []
    out = []
    for r in rates:
        out.append({
            "time": int(r["time"]),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "tick_volume": int(r["tick_volume"]),
            "spread": int(r["spread"]),
        })
    return out
""")

        init_ok = conn.eval("_arena_init()")
        if init_ok:
            conn.eval(f"_arena_select_symbols({list(BROKER_MAP.values())})")
            log.info("✓ Sukses terhubung dan menginisialisasi MT5 di %s:%d", MT5_RPYC_HOST, MT5_RPYC_PORT)
            _rpyc_conn = conn
            cached_account_info["connected"] = True
            try:
                acc = conn.eval("mt5.account_info()")
                if acc:
                    cached_account_info["login"] = int(acc.login)
                    cached_account_info["server"] = str(acc.server)
                    cached_account_info["balance"] = float(acc.balance)
            except Exception:
                pass
            return _rpyc_conn
        else:
            err = conn.eval("mt5.last_error()")
            log.warning("MT5 initialize() di remote RPyC mengembalikan False: %s", err)
            cached_account_info["connected"] = False
            return None
    except Exception as exc:
        log.warning("Gagal connect ke RPyC MT5 (%s:%d): %s", MT5_RPYC_HOST, MT5_RPYC_PORT, exc)
        _rpyc_conn = None
        cached_account_info["connected"] = False
        return None


def _sync_fetch_ticks(conn):
    """Fetch ticks synchronously in worker thread."""
    global cached_account_info
    if conn is None:
        return None
    try:
        ticks_raw = conn.eval(f"_arena_get_ticks({BROKER_MAP})")
        return ticks_raw
    except Exception as exc:
        log.warning("Gagal fetch ticks dari MT5: %s", exc)
        return None


async def tick_updater_loop():
    """Background polling loop yang mengambil harga live MT5 langsung dari broker Headway."""
    global _rpyc_conn
    while True:
        try:
            now_sec = time.time()
            now_ms = int(now_sec * 1000)
            conn = await asyncio.to_thread(_sync_connect_rpyc)

            if conn is not None:
                ticks_raw = await asyncio.to_thread(_sync_fetch_ticks, conn)
                if ticks_raw and isinstance(ticks_raw, dict):
                    for sym, (bid, ask, last, t_sec, t_msc) in ticks_raw.items():
                        meta = PAIRS.get(sym)
                        if not meta:
                            continue
                        digits = meta["digits"]
                        pip = meta["pip"]

                        bid = round(bid, digits)
                        ask = round(ask, digits)
                        mid = round((bid + ask) / 2.0, digits)
                        spr_points = round(ask - bid, digits)
                        spr_pips = round(spr_points / pip, 1)

                        if sym not in day_open_prices:
                            day_open_prices[sym] = mid
                        day_open = day_open_prices[sym]
                        change_pct = round(((mid - day_open) / day_open) * 100.0, 2) if day_open > 0 else 0.0

                        current_ticks[sym] = {
                            "symbol": sym,
                            "name": meta["name"],
                            "base": meta["base"],
                            "quote": meta["quote"],
                            "bid": bid,
                            "ask": ask,
                            "last": mid,
                            "price": bid,
                            "spread": spr_points,
                            "spread_pips": spr_pips,
                            "change": change_pct,
                            "digits": digits,
                            "pip": pip,
                            "time": t_sec if t_sec > 0 else int(now_sec),
                            "time_msc": t_msc if t_msc > 0 else now_ms,
                            "source": "mt5-live",
                        }
                elif ticks_raw is None:
                    _rpyc_conn = None
                    cached_account_info["connected"] = False

            await asyncio.sleep(0.3)
        except Exception as exc:
            log.warning("Tick loop exception: %s", exc)
            await asyncio.sleep(1)


# Route Handlers
async def handle_health(request):
    return web.json_response({
        "status": "healthy",
        "service": "mt5-bridge",
        "server": cached_account_info.get("server") or "Headway-Demo",
        "account": cached_account_info.get("login") or 6310591,
        "balance": cached_account_info.get("balance", 0.0),
        "broker": "Headway",
        "live_feed": "MetaTrader 5 Real-Time Price Bridge (Headway)",
        "connected": True,
        "mt5_live_connected": cached_account_info.get("connected", False),
        "symbols_count": len(current_ticks),
        "gold_price": current_ticks.get("XAUUSD", {}).get("price", 0.0),
        "oil_price": current_ticks.get("USOIL", {}).get("price", 0.0),
        "eurusd": current_ticks.get("EURUSD", {}).get("price", 0.0),
        "usdjpy": current_ticks.get("USDJPY", {}).get("price", 0.0),
        "gbpusd": current_ticks.get("GBPUSD", {}).get("price", 0.0),
    })


async def handle_ticks(request):
    """Mengembalikan seluruh 22 live ticks Forex & Metals lengkap dengan Bid/Ask/Spread."""
    return web.json_response(current_ticks)


async def handle_symbol_tick(request):
    sym = request.match_info.get("symbol", "").upper()
    if sym in current_ticks:
        t = current_ticks[sym]
        return web.json_response({
            "bid": t["bid"],
            "ask": t["ask"],
            "last": t["last"],
            "spread": t["spread"],
            "spread_pips": t["spread_pips"],
            "time": t["time"],
            "source": t.get("source", "mt5-live"),
        })
    return web.json_response({"error": f"Symbol {sym} not found"}, status=404)


async def handle_fetch_data_pos(request):
    """Mengembalikan bar candle M1 riil langsung dari MT5 terminal jika terhubung."""
    sym = request.query.get("symbol", "EURUSD").upper()
    num_bars = int(request.query.get("num_bars", "100"))
    num_bars = min(max(num_bars, 10), 500)
    broker_sym = BROKER_MAP.get(sym, sym)

    conn = get_rpyc_connection()
    if conn:
        try:
            bars = conn.eval(f"_arena_get_bars('{broker_sym}', {num_bars})")
            if bars and isinstance(bars, list) and len(bars) > 0:
                return web.json_response(bars)
        except Exception as exc:
            log.warning("Gagal fetch bars dari MT5 untuk %s: %s", sym, exc)

    return web.json_response([], status=503)


async def init_app():
    app = web.Application()
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/ticks", handle_ticks)
    app.router.add_get("/symbol_info_tick/{symbol}", handle_symbol_tick)
    app.router.add_get("/fetch_data_pos", handle_fetch_data_pos)

    # Start tick loop
    asyncio.create_task(tick_updater_loop())
    return app


if __name__ == "__main__":
    app = init_app()
    log.info("MT5 Headway Bridge Server running on http://0.0.0.0:%d", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT)
