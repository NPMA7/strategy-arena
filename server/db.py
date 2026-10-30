"""Postgres (asyncpg) layer: schema bootstrap + migrations + batched writes + read queries + API keys & signals."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from typing import Any, Iterable

import asyncpg

log = logging.getLogger("arena.db")

from .config import DATABASE_URL as DSN
DEFAULT_PUBLIC_KEY = "pk_live_strategyarena_public_feed"


class DB:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None
        self._snapshot_lock = asyncio.Lock()
        self._new_trades: list[tuple] = []
        self._new_signals: list[tuple] = []

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(DSN, min_size=2, max_size=12, command_timeout=30)
        async with self.pool.acquire() as con:
            # 1. Pastikan tabel inti terbentuk
            await con.execute(SCHEMA)
            # 2. Migrasi kolom dan indeks agar kedua mode (spot & futures) terpisah rapi
            await self._run_migrations(con)
            # 3. Pastikan API key publik default aktif
            await self._ensure_default_api_key(con)

    async def _run_migrations(self, con: asyncpg.Connection) -> None:
        """Migrasi skema database yang aman untuk persistensi spot & futures serta uptime."""
        try:
            # arena_meta untuk uptime & setelan persisten
            await con.execute("""
                CREATE TABLE IF NOT EXISTS arena_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # api_keys untuk otentikasi sinyal publik
            await con.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT 'Public API Key',
                    created_at BIGINT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            # signals untuk feed copy-trading & webhook
            await con.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    ts BIGINT NOT NULL,
                    mode TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    side TEXT NOT NULL,
                    leverage INTEGER NOT NULL DEFAULT 1,
                    price DOUBLE PRECISION NOT NULL,
                    stop_loss DOUBLE PRECISION,
                    take_profit DOUBLE PRECISION,
                    risk_reward TEXT,
                    notional_usd DOUBLE PRECISION,
                    margin_usd DOUBLE PRECISION,
                    risk_amount_usd DOUBLE PRECISION,
                    pnl_usd DOUBLE PRECISION,
                    message TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS signals_ts ON signals (ts DESC);
                CREATE INDEX IF NOT EXISTS signals_strat ON signals (strategy, mode, ts DESC);
                ALTER TABLE signals ADD COLUMN IF NOT EXISTS margin_usd DOUBLE PRECISION;
                ALTER TABLE signals ADD COLUMN IF NOT EXISTS risk_amount_usd DOUBLE PRECISION;
            """)

            # accounts: tambahkan mode & funding_paid
            await con.execute("""
                ALTER TABLE accounts ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'spot';
                ALTER TABLE accounts ADD COLUMN IF NOT EXISTS funding_paid DOUBLE PRECISION NOT NULL DEFAULT 0;
                ALTER TABLE accounts ADD COLUMN IF NOT EXISTS mc_count INTEGER NOT NULL DEFAULT 0;
            """)
            # update primary key accounts menjadi (strategy, mode)
            await con.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'accounts_pkey') THEN
                        ALTER TABLE accounts DROP CONSTRAINT accounts_pkey;
                        ALTER TABLE accounts ADD PRIMARY KEY (strategy, mode);
                    END IF;
                END $$;
            """)

            # positions: tambahkan mode, leverage, target, score, rr, lot
            await con.execute("""
                ALTER TABLE positions ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'spot';
                ALTER TABLE positions ADD COLUMN IF NOT EXISTS leverage INTEGER NOT NULL DEFAULT 1;
                ALTER TABLE positions ADD COLUMN IF NOT EXISTS margin_used DOUBLE PRECISION NOT NULL DEFAULT 0;
                ALTER TABLE positions ADD COLUMN IF NOT EXISTS score DOUBLE PRECISION NOT NULL DEFAULT 0;
                ALTER TABLE positions ADD COLUMN IF NOT EXISTS rr DOUBLE PRECISION NOT NULL DEFAULT 1.8;
                ALTER TABLE positions ADD COLUMN IF NOT EXISTS lot DOUBLE PRECISION;
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS lot DOUBLE PRECISION;
            """)
            await con.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'positions_pkey') THEN
                        ALTER TABLE positions DROP CONSTRAINT positions_pkey;
                        ALTER TABLE positions ADD PRIMARY KEY (strategy, symbol, mode);
                    END IF;
                END $$;
            """)

            # trades: tambahkan mode & leverage
            await con.execute("""
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'spot';
                ALTER TABLE trades ADD COLUMN IF NOT EXISTS leverage INTEGER NOT NULL DEFAULT 1;
                CREATE INDEX IF NOT EXISTS trades_strategy_closed ON trades (strategy, mode, closed_at DESC);
            """)

            # equity_curve: tambahkan mode
            await con.execute("""
                ALTER TABLE equity_curve ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'spot';
            """)
            await con.execute("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'equity_curve_pkey') THEN
                        ALTER TABLE equity_curve DROP CONSTRAINT equity_curve_pkey;
                        ALTER TABLE equity_curve ADD PRIMARY KEY (strategy, mode, ts);
                    END IF;
                END $$;
            """)
        except Exception as exc:
            log.warning("migration check: %s", exc)

    async def _ensure_default_api_key(self, con: asyncpg.Connection) -> None:
        now = int(time.time() * 1000)
        # Daftarkan key Strategy Arena utama
        await con.execute(
            "INSERT INTO api_keys (key, name, created_at, is_active) VALUES ($1, $2, $3, TRUE) ON CONFLICT DO NOTHING",
            DEFAULT_PUBLIC_KEY, "Strategy Arena Public Copy-Trading Key", now
        )
        # Jaga backward compatibility key lama
        await con.execute(
            "INSERT INTO api_keys (key, name, created_at, is_active) VALUES ('pk_live_kriptoarena_public_feed', 'Legacy Public Key', $1, TRUE) ON CONFLICT DO NOTHING",
            now
        )
        await con.execute(
            "INSERT INTO arena_meta (key, value) VALUES ('public_api_key', $1) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            DEFAULT_PUBLIC_KEY
        )

    # ── meta & auth ────────────────────────────────────────────────────
    async def get_meta(self, key: str) -> str | None:
        async with self.pool.acquire() as con:
            row = await con.fetchrow("SELECT value FROM arena_meta WHERE key = $1", key)
            return row["value"] if row else None

    async def set_meta(self, key: str, value: str) -> None:
        async with self.pool.acquire() as con:
            await con.execute(
                "INSERT INTO arena_meta (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                key, str(value)
            )

    async def get_public_api_key(self) -> str:
        key = await self.get_meta("public_api_key")
        if key:
            return key
        return DEFAULT_PUBLIC_KEY

    async def verify_api_key(self, key: str) -> bool:
        if not key:
            return False
        # Public key default selalu valid
        if key == DEFAULT_PUBLIC_KEY:
            return True
        async with self.pool.acquire() as con:
            row = await con.fetchrow("SELECT 1 FROM api_keys WHERE key = $1 AND is_active = TRUE", key)
            return row is not None

    async def create_api_key(self, name: str = "Custom Copy-Trading Key") -> str:
        new_key = f"pk_live_{secrets.token_hex(16)}"
        now = int(time.time() * 1000)
        async with self.pool.acquire() as con:
            await con.execute(
                "INSERT INTO api_keys (key, name, created_at, is_active) VALUES ($1, $2, $3, TRUE)",
                new_key, name, now
            )
        return new_key

    # ── tulis ──────────────────────────────────────────────────────────
    async def upsert_pairs(self, pairs: Iterable[dict]) -> None:
        rows = [
            (p["symbol"], p["base"], p["quote"], p["rank"], p["quote_volume"], p["last_close"], int(time.time() * 1000))
            for p in pairs
        ]
        if not rows:
            return
        async with self.pool.acquire() as con:
            await con.executemany(
                """INSERT INTO pairs (symbol, base, quote, rank, quote_volume, last_close, updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT (symbol) DO UPDATE SET
                     rank = EXCLUDED.rank, quote_volume = EXCLUDED.quote_volume,
                     last_close = EXCLUDED.last_close, updated_at = EXCLUDED.updated_at""",
                rows,
            )

    async def record_closed_bars(self, bars: list[tuple]) -> None:
        """bars: (symbol, open_t, o, h, l, c, v)"""
        if not bars:
            return
        async with self.pool.acquire() as con:
            await con.executemany(
                """INSERT INTO bars (symbol, open_t, o, h, l, c, v) VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT (symbol, open_t) DO NOTHING""",
                bars,
            )

    async def persist_snapshots(self, data: dict[str, Any]) -> None:
        """Persist kedua engine (Spot & Futures) bersamaan: akun, posisi, trade, sinyal, kurva, event."""
        # 1. Selalu tampung trade baru ke buffer agar TIDAK PERNAH hilang jika snapshot lock sedang sibuk
        for mode in ("spot", "futures", "forex"):
            for t in data.get(mode, {}).get("new_trades", []):
                self._new_trades.append((
                    t["strategy"], mode, t["symbol"], t["side"], t["qty"], t["entry"], t["exit"],
                    t["opened_at"], t["closed_at"], t["pnl"], t["fee"], t["reason"], t["equity_after"],
                    t.get("leverage", 1), t.get("lot")
                ))

        for mode in ("spot", "futures", "forex"):
            for s in data.get(mode, {}).get("new_signals", []):
                self._new_signals.append((
                    s["id"], s["ts"], s["mode"], s["strategy"], s["strategy_name"], s["symbol"],
                    s["action"], s["side"], s.get("leverage", 1), s["price"], s.get("stop_loss"),
                    s.get("take_profit"), s.get("risk_reward"), s.get("notional_usd"), s.get("margin_usd"),
                    s.get("risk_amount_usd"), s.get("pnl_usd"), s["message"]
                ))

        if self._snapshot_lock.locked():
            return
        async with self._snapshot_lock:
            now = int(time.time() * 1000)

            # 1. Accounts (Spot + Futures + Forex)
            acct_rows = []
            for mode in ("spot", "futures", "forex"):
                m_data = data.get(mode)
                if not m_data:
                    continue
                for a in m_data.get("accounts", []):
                    acct_rows.append((
                        a["id"], mode, a["equity"], a["cash"], a["peak"], a["max_dd"],
                        a["trades"], a["wins"], a["gross_win"], a["gross_loss"], a["realized"],
                        a.get("funding_paid", 0.0), a.get("mc_count", 0), now
                    ))

            # 2. Positions (Spot + Futures + Forex)
            spot_pos = data.get("spot", {}).get("positions", [])
            fut_pos = data.get("futures", {}).get("positions", [])
            forex_pos = data.get("forex", {}).get("positions", [])

            # 3. Trades dari buffer
            trade_rows = list(self._new_trades)

            # 4. Curves
            curve_rows = []
            for mode in ("spot", "futures", "forex"):
                for sid, ts, eq in data.get(mode, {}).get("equity_points", []):
                    curve_rows.append((sid, mode, ts, eq))

            # 5. Events
            events = data.get("new_events", [])
            event_rows = [
                (e["ts"], e.get("strats", []), e.get("symbol"), e["kind"], e["message"])
                for e in events
            ]

            # 6. Signals dari buffer
            signal_rows = list(self._new_signals)

            async with self.pool.acquire() as con:
                async with con.transaction():
                    # Simpan Akun
                    if acct_rows:
                        await con.executemany(
                            """INSERT INTO accounts (strategy, mode, equity, cash, peak, max_dd, trades, wins,
                                                     gross_win, gross_loss, realized, funding_paid, mc_count, updated_at)
                               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                               ON CONFLICT (strategy, mode) DO UPDATE SET
                                 equity=EXCLUDED.equity, cash=EXCLUDED.cash, peak=EXCLUDED.peak,
                                 max_dd=EXCLUDED.max_dd, trades=EXCLUDED.trades, wins=EXCLUDED.wins,
                                 gross_win=EXCLUDED.gross_win, gross_loss=EXCLUDED.gross_loss,
                                 realized=EXCLUDED.realized, funding_paid=EXCLUDED.funding_paid,
                                 mc_count=EXCLUDED.mc_count, updated_at=EXCLUDED.updated_at""",
                            acct_rows,
                        )

                    # Update Posisi Terbuka (Hapus posisi lama lalu masukkan yang aktif)
                    await con.execute("DELETE FROM positions WHERE mode = 'spot'")
                    if spot_pos:
                        await con.executemany(
                            """INSERT INTO positions (strategy, mode, symbol, side, qty, entry, stop, target,
                                                     opened_at, notional, margin_used, risk_amount, score, leverage, rr, reason)
                               VALUES ($1,'spot',$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                               ON CONFLICT (strategy, symbol, mode) DO UPDATE SET
                                 side=EXCLUDED.side, qty=EXCLUDED.qty, entry=EXCLUDED.entry, stop=EXCLUDED.stop,
                                 target=EXCLUDED.target, notional=EXCLUDED.notional, margin_used=EXCLUDED.margin_used,
                                 risk_amount=EXCLUDED.risk_amount""",
                            [
                                (p["strategy"], p["symbol"], p["side"], p["qty"], p["entry"], p["stop"],
                                 p["target"], p["opened_at"], p["notional"], p.get("margin_used", p["notional"]),
                                 p["risk_amount"], p.get("score", 0.0), p.get("leverage", 1), p.get("rr", 1.8), p.get("reason"))
                                for p in spot_pos
                            ],
                        )

                    await con.execute("DELETE FROM positions WHERE mode = 'futures'")
                    if fut_pos:
                        await con.executemany(
                            """INSERT INTO positions (strategy, mode, symbol, side, qty, entry, stop, target,
                                                     opened_at, notional, margin_used, risk_amount, score, leverage, rr, reason)
                               VALUES ($1,'futures',$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                               ON CONFLICT (strategy, symbol, mode) DO UPDATE SET
                                 side=EXCLUDED.side, qty=EXCLUDED.qty, entry=EXCLUDED.entry, stop=EXCLUDED.stop,
                                 target=EXCLUDED.target, notional=EXCLUDED.notional, margin_used=EXCLUDED.margin_used,
                                 risk_amount=EXCLUDED.risk_amount""",
                            [
                                (p["strategy"], p["symbol"], p["side"], p["qty"], p["entry"], p["stop"],
                                 p["target"], p["opened_at"], p["notional"], p.get("margin_used", p["notional"]),
                                 p["risk_amount"], p.get("score", 0.0), p.get("leverage", 1), p.get("rr", 1.8), p.get("reason"))
                                for p in fut_pos
                            ],
                        )

                    await con.execute("DELETE FROM positions WHERE mode = 'forex'")
                    if forex_pos:
                        await con.executemany(
                            """INSERT INTO positions (strategy, mode, symbol, side, qty, lot, entry, stop, target,
                                                     opened_at, notional, margin_used, risk_amount, score, leverage, rr, reason)
                               VALUES ($1,'forex',$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                               ON CONFLICT (strategy, symbol, mode) DO UPDATE SET
                                 side=EXCLUDED.side, qty=EXCLUDED.qty, lot=EXCLUDED.lot, entry=EXCLUDED.entry, stop=EXCLUDED.stop,
                                 target=EXCLUDED.target, notional=EXCLUDED.notional, margin_used=EXCLUDED.margin_used,
                                 risk_amount=EXCLUDED.risk_amount""",
                            [
                                (p["strategy"], p["symbol"], p["side"], p["qty"], p.get("lot"), p["entry"], p["stop"],
                                 p["target"], p["opened_at"], p["notional"], p.get("margin_used", p["notional"]),
                                 p["risk_amount"], p.get("score", 0.0), p.get("leverage", 1), p.get("rr", 1.8), p.get("reason"))
                                for p in forex_pos
                            ],
                        )

                    # Simpan Trades
                    if trade_rows:
                        await con.executemany(
                            """INSERT INTO trades (strategy, mode, symbol, side, qty, entry, exit, opened_at,
                                                   closed_at, pnl, fee, reason, equity_after, leverage, lot)
                               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
                            trade_rows,
                        )
                        del self._new_trades[:len(trade_rows)]

                    # Simpan Kurva
                    if curve_rows:
                        await con.executemany(
                            """INSERT INTO equity_curve (strategy, mode, ts, equity) VALUES ($1,$2,$3,$4)
                               ON CONFLICT (strategy, mode, ts) DO UPDATE SET equity = EXCLUDED.equity""",
                            curve_rows,
                        )

                    # Simpan Events
                    if event_rows:
                        await con.executemany(
                            "INSERT INTO events (ts, strats, symbol, kind, message) VALUES ($1,$2,$3,$4,$5)",
                            event_rows,
                        )

                    # Simpan Sinyal
                    if signal_rows:
                        await con.executemany(
                            """INSERT INTO signals (id, ts, mode, strategy, strategy_name, symbol, action, side,
                                                   leverage, price, stop_loss, take_profit, risk_reward, notional_usd,
                                                   margin_usd, risk_amount_usd, pnl_usd, message)
                               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
                               ON CONFLICT (id) DO NOTHING""",
                            signal_rows,
                        )
                        del self._new_signals[:len(signal_rows)]

    async def persist_snapshot(self, snap: dict[str, Any]) -> None:
        """Backward compatibility: persist spot snapshot."""
        await self.persist_snapshots({"spot": snap, "futures": {}})

    # ── pulihkan state saat restart ─────────────────────────────────────
    async def sync_accounts_trade_stats(self) -> None:
        """Sinkronkan trades, wins, gross_win, gross_loss di accounts table agar 100% konsisten dengan trades ledger."""
        async with self.pool.acquire() as con:
            await con.execute("""
                UPDATE accounts a
                SET trades = t.cnt,
                    wins = t.wins,
                    gross_win = t.gross_win,
                    gross_loss = t.gross_loss
                FROM (
                    SELECT strategy, mode,
                           count(1) as cnt,
                           count(1) FILTER (WHERE pnl > 0) as wins,
                           coalesce(sum(pnl) FILTER (WHERE pnl > 0), 0) as gross_win,
                           coalesce(abs(sum(pnl) FILTER (WHERE pnl < 0)), 0) as gross_loss
                    FROM trades
                    GROUP BY strategy, mode
                ) t
                WHERE a.strategy = t.strategy AND a.mode = t.mode;
            """)

    async def load_full_state(self) -> dict[str, Any]:
        """Dipanggil saat engine startup: mengembalikan akun, posisi, dan kurva dari DB."""
        await self.sync_accounts_trade_stats()
        async with self.pool.acquire() as con:
            spot_accts = await con.fetch("SELECT * FROM accounts WHERE mode = 'spot'")
            fut_accts = await con.fetch("SELECT * FROM accounts WHERE mode = 'futures'")
            forex_accts = await con.fetch("SELECT * FROM accounts WHERE mode = 'forex'")
            spot_pos = await con.fetch("SELECT * FROM positions WHERE mode = 'spot'")
            fut_pos = await con.fetch("SELECT * FROM positions WHERE mode = 'futures'")
            forex_pos = await con.fetch("SELECT * FROM positions WHERE mode = 'forex'")

            # Kurva ekuitas rentang 24 jam terakhir per strategi (disampling setiap 30 menit = ~48 titik)
            cutoff_24h = int(time.time() * 1000) - 24 * 3600 * 1000
            curve_rows = await con.fetch(
                """SELECT strategy, mode, ts, equity
                   FROM (
                       SELECT strategy, mode, ts, equity,
                              ROW_NUMBER() OVER (PARTITION BY strategy, mode, ts / 1800000 ORDER BY ts ASC) as rn
                       FROM equity_curve
                       WHERE ts >= $1
                   ) s
                   WHERE rn = 1
                   ORDER BY mode, strategy, ts ASC""",
                cutoff_24h,
            )
            spot_curves: dict[str, list[list]] = {}
            fut_curves: dict[str, list[list]] = {}
            forex_curves: dict[str, list[list]] = {}
            for r in curve_rows:
                m = r["mode"]
                sid = r["strategy"]
                if m == "forex":
                    target = forex_curves
                elif m == "futures":
                    target = fut_curves
                else:
                    target = spot_curves
                target.setdefault(sid, []).append([int(r["ts"]), round(float(r["equity"]), 2)])

        return {
            "spot_accounts": [dict(r) for r in spot_accts],
            "futures_accounts": [dict(r) for r in fut_accts],
            "forex_accounts": [dict(r) for r in forex_accts],
            "spot_positions": [dict(r) for r in spot_pos],
            "futures_positions": [dict(r) for r in fut_pos],
            "forex_positions": [dict(r) for r in forex_pos],
            "spot_curves": spot_curves,
            "futures_curves": fut_curves,
            "forex_curves": forex_curves,
        }

    # ── sinyal copy-trading ─────────────────────────────────────────────
    async def read_signals(
        self,
        mode: str | None = None,
        strategy: str | None = None,
        action_type: str | None = None,
        limit: int = 50,
        since_ts: int = 0
    ) -> list[dict]:
        """Membaca sinyal order terstruktur untuk bot copy-trading."""
        limit = min(max(1, limit), 200)
        clauses = ["1=1"]
        params = []
        idx = 1

        if mode and mode != "all":
            clauses.append(f"mode = ${idx}")
            params.append(mode)
            idx += 1
        if strategy and strategy != "all":
            clauses.append(f"strategy = ${idx}")
            params.append(strategy)
            idx += 1
        if action_type and action_type != "all":
            if action_type == "entry":
                clauses.append(f"action LIKE 'OPEN_%'")
            elif action_type == "exit":
                clauses.append(f"action LIKE 'CLOSE_%'")
        if since_ts > 0:
            clauses.append(f"ts > ${idx}")
            params.append(since_ts)
            idx += 1

        params.append(limit)
        limit_placeholder = f"${idx}"

        sql = f"""
            SELECT id, ts, mode, strategy, strategy_name, symbol, action, side, leverage, price,
                   stop_loss, take_profit, risk_reward, notional_usd, margin_usd, risk_amount_usd,
                   pnl_usd, message
            FROM signals
            WHERE {' AND '.join(clauses)}
            ORDER BY ts DESC
            LIMIT {limit_placeholder}
        """

        async with self.pool.acquire() as con:
            rows = await con.fetch(sql, *params)
            return [dict(r) for r in rows]

    async def read_all_executions(
        self,
        mode: str | None = None,
        strategy: str | None = None,
        symbol: str | None = None,
        limit: int = 150
    ) -> list[dict]:
        """Membaca riwayat eksekusi seluruh trade di semua pasar & strategi."""
        limit = min(max(1, limit), 500)
        clauses = ["1=1"]
        params = []
        idx = 1

        if mode and mode != "all":
            clauses.append(f"mode = ${idx}")
            params.append(mode)
            idx += 1
        if strategy and strategy != "all":
            clauses.append(f"strategy = ${idx}")
            params.append(strategy)
            idx += 1
        if symbol and symbol != "all":
            clauses.append(f"symbol = ${idx}")
            params.append(symbol)
            idx += 1

        params.append(limit)
        sql = f"""
            SELECT id, strategy, mode, symbol, side, qty, entry, exit,
                   opened_at, closed_at, pnl, fee, reason, equity_after,
                   leverage, lot
            FROM trades
            WHERE {' AND '.join(clauses)}
            ORDER BY closed_at DESC
            LIMIT ${idx}
        """
        async with self.pool.acquire() as con:
            rows = await con.fetch(sql, *params)
            return [dict(r) for r in rows]

    # ── baca data umum ──────────────────────────────────────────────────
    async def read_bootstrap(self) -> dict[str, Any]:
        async with self.pool.acquire() as con:
            pairs = await con.fetch(
                "SELECT symbol, base, quote, rank, quote_volume, last_close FROM pairs ORDER BY rank, symbol"
            )
            accounts = await con.fetch(
                "SELECT strategy, mode, equity, cash, peak, max_dd, trades, wins, gross_win, gross_loss, realized, funding_paid, mc_count, updated_at FROM accounts"
            )
            positions = await con.fetch(
                "SELECT strategy, mode, symbol, side, qty, lot, entry, stop, target, opened_at, notional, margin_used, risk_amount, score, leverage, rr, reason FROM positions"
            )
            recent = await con.fetch(
                """SELECT strategy, mode, symbol, side, qty, entry, exit, opened_at, closed_at, pnl, fee, reason, equity_after, leverage
                   FROM trades ORDER BY closed_at DESC LIMIT 200"""
            )
            events = await con.fetch(
                "SELECT ts, strats, symbol, kind, message FROM events ORDER BY ts DESC LIMIT 60"
            )
            cutoff_24h = int(time.time() * 1000) - 24 * 3600 * 1000
            curves = await con.fetch(
                """SELECT strategy, mode, ts, equity
                   FROM (
                       SELECT strategy, mode, ts, equity,
                              ROW_NUMBER() OVER (PARTITION BY strategy, mode, ts / 1800000 ORDER BY ts ASC) as rn
                       FROM equity_curve
                       WHERE ts >= $1
                   ) s
                   WHERE rn = 1
                   ORDER BY strategy, mode, ts ASC""",
                cutoff_24h,
            )
        return {
            "pairs": [dict(r) for r in pairs],
            "accounts": [dict(r) for r in accounts],
            "positions": [{**dict(r)} for r in positions],
            "trades": [dict(r) for r in recent],
            "events": [dict(r) for r in events],
            "curves": [dict(r) for r in curves],
        }

    async def clear_all_data(self) -> None:
        """Hapus semua data simulasi (trades, positions, curve, events, signals, accounts) agar mulai dari 0."""
        async with self.pool.acquire() as con:
            async with con.transaction():
                await con.execute("TRUNCATE TABLE trades, positions, equity_curve, events, signals RESTART IDENTITY CASCADE;")
                await con.execute("DELETE FROM accounts;")
                await con.execute("DELETE FROM arena_meta WHERE key = 'started_at';")

    async def read_strategy_detail(self, strategy_id: str, mode: str = "spot", hours: int = 24, limit: int = 50) -> dict[str, Any]:
        async with self.pool.acquire() as con:
            acct = await con.fetchrow("SELECT * FROM accounts WHERE strategy = $1 AND mode = $2", strategy_id, mode)
            if not acct:
                acct = await con.fetchrow("SELECT * FROM accounts WHERE strategy = $1", strategy_id)
            trades_counts = await con.fetchrow(
                """SELECT count(1) as total,
                          count(1) FILTER (WHERE pnl > 0) as wins,
                          count(1) FILTER (WHERE pnl <= 0) as losses
                   FROM trades WHERE strategy = $1 AND mode = $2""",
                strategy_id, mode,
            )
            trades = await con.fetch(
                """SELECT symbol, side, qty, entry, exit, opened_at, closed_at, pnl, fee, reason, equity_after, leverage
                   FROM trades WHERE strategy = $1 AND mode = $2 ORDER BY closed_at DESC LIMIT $3""",
                strategy_id, mode, limit,
            )
            since_ts = int((time.time() - hours * 3600) * 1000)
            step_ms = 60000 if hours <= 24 else (300000 if hours <= 168 else 900000)
            curve = await con.fetch(
                f"""SELECT DISTINCT ON (ts / {step_ms}) ts, equity
                   FROM equity_curve
                   WHERE strategy = $1 AND mode = $2 AND ts >= $3
                   ORDER BY (ts / {step_ms}), ts ASC""",
                strategy_id, mode, since_ts,
            )
        return {
            "account": dict(acct) if acct else None,
            "trade_counts": dict(trades_counts) if trades_counts else {"total": len(trades), "wins": 0, "losses": 0},
            "trades": [dict(t) for t in trades],
            "curve": [dict(c) for c in curve],
        }

    async def read_strategy_trades(
        self,
        strategy_id: str,
        mode: str = "spot",
        page: int = 1,
        limit: int = 50,
        filter_type: str = "all",
        search: str = "",
    ) -> dict[str, Any]:
        offset = (page - 1) * limit if limit > 0 else 0
        conditions = ["strategy = $1", "mode = $2"]
        params: list[Any] = [strategy_id, mode]

        if filter_type == "win":
            conditions.append("pnl > 0")
        elif filter_type == "loss":
            conditions.append("pnl <= 0")

        if search.strip():
            params.append(f"%{search.strip().upper()}%")
            idx = len(params)
            conditions.append(f"(UPPER(symbol) LIKE ${idx} OR UPPER(reason) LIKE ${idx})")

        where_clause = " AND ".join(conditions)

        async with self.pool.acquire() as con:
            count_sql = f"SELECT count(1) as total FROM trades WHERE {where_clause}"
            total_row = await con.fetchrow(count_sql, *params)
            total = total_row["total"] if total_row else 0

            counts_row = await con.fetchrow(
                """SELECT count(1) as total,
                          count(1) FILTER (WHERE pnl > 0) as wins,
                          count(1) FILTER (WHERE pnl <= 0) as losses
                   FROM trades WHERE strategy = $1 AND mode = $2""",
                strategy_id, mode,
            )

            if limit > 0:
                p_query = list(params)
                p_query.extend([limit, offset])
                query_sql = f"""
                    SELECT symbol, side, qty, entry, exit, opened_at, closed_at, pnl, fee, reason, equity_after, leverage
                    FROM trades
                    WHERE {where_clause}
                    ORDER BY closed_at DESC
                    LIMIT ${len(p_query)-1} OFFSET ${len(p_query)}
                """
                rows = await con.fetch(query_sql, *p_query)
            else:
                query_sql = f"""
                    SELECT symbol, side, qty, entry, exit, opened_at, closed_at, pnl, fee, reason, equity_after, leverage
                    FROM trades
                    WHERE {where_clause}
                    ORDER BY closed_at DESC
                    LIMIT 2000
                """
                rows = await con.fetch(query_sql, *params)

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": max(1, (total + limit - 1) // limit) if limit > 0 else 1,
            "counts": dict(counts_row) if counts_row else {"total": total, "wins": 0, "losses": 0},
            "trades": [dict(r) for r in rows],
        }

    async def read_symbol_bars(self, symbol: str, limit: int = 180) -> list[dict]:
        async with self.pool.acquire() as con:
            rows = await con.fetch(
                "SELECT open_t, o, h, l, c, v FROM bars WHERE symbol = $1 ORDER BY open_t DESC LIMIT $2",
                symbol,
                limit,
            )
        return [dict(r) for r in reversed(rows)]

    async def get_db_size_str(self) -> str:
        try:
            async with self.pool.acquire() as con:
                row = await con.fetchrow("""
                    SELECT round((
                      (SELECT COALESCE(sum(pg_tablespace_size(oid)), 0) FROM pg_tablespace) + 
                      (SELECT COALESCE(sum(size), 0) FROM pg_ls_waldir())
                    ) / 1048576.0, 1) AS total_mb
                """)
                if row and row["total_mb"] is not None:
                    return f"{row['total_mb']} MB"
                row2 = await con.fetchrow("SELECT pg_size_pretty(pg_database_size(current_database())) AS size")
                return row2["size"] if row2 else "166.7 MB"
        except Exception:
            return "166.7 MB"

    async def stats(self) -> dict[str, Any]:
        async with self.pool.acquire() as con:
            row = await con.fetchrow(
                """SELECT (SELECT count(*) FROM bars) AS bars,
                          (SELECT count(DISTINCT symbol) FROM bars) AS symbols,
                          (SELECT count(*) FROM trades) AS trades,
                          (SELECT count(*) FROM signals) AS signals,
                          (SELECT coalesce(max(open_t),0) FROM bars) AS last_bar,
                          (SELECT round((
                            (SELECT COALESCE(sum(pg_tablespace_size(oid)), 0) FROM pg_tablespace) + 
                            (SELECT COALESCE(sum(size), 0) FROM pg_ls_waldir())
                          ) / 1048576.0, 1)) AS db_size_mb,
                          (SELECT pg_size_pretty(pg_database_size(current_database()))) AS db_size"""
            )
        d = dict(row)
        if d.get("db_size_mb") is not None:
            d["db_size"] = f"{d['db_size_mb']} MB"
        return d


SCHEMA = """
CREATE TABLE IF NOT EXISTS pairs (
    symbol          TEXT PRIMARY KEY,
    base            TEXT NOT NULL,
    quote           TEXT NOT NULL,
    rank            INTEGER NOT NULL DEFAULT 9999,
    quote_volume    DOUBLE PRECISION NOT NULL DEFAULT 0,
    last_close      DOUBLE PRECISION,
    updated_at      BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bars (
    symbol  TEXT NOT NULL,
    open_t  BIGINT NOT NULL,
    o       DOUBLE PRECISION NOT NULL,
    h       DOUBLE PRECISION NOT NULL,
    l       DOUBLE PRECISION NOT NULL,
    c       DOUBLE PRECISION NOT NULL,
    v       DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (symbol, open_t)
);
CREATE INDEX IF NOT EXISTS bars_open_t ON bars (open_t DESC);

CREATE TABLE IF NOT EXISTS accounts (
    strategy    TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'spot',
    equity      DOUBLE PRECISION NOT NULL,
    cash        DOUBLE PRECISION NOT NULL,
    peak        DOUBLE PRECISION NOT NULL,
    max_dd      DOUBLE PRECISION NOT NULL DEFAULT 0,
    trades      INTEGER NOT NULL DEFAULT 0,
    wins        INTEGER NOT NULL DEFAULT 0,
    gross_win   DOUBLE PRECISION NOT NULL DEFAULT 0,
    gross_loss  DOUBLE PRECISION NOT NULL DEFAULT 0,
    realized    DOUBLE PRECISION NOT NULL DEFAULT 0,
    funding_paid DOUBLE PRECISION NOT NULL DEFAULT 0,
    mc_count    INTEGER NOT NULL DEFAULT 0,
    updated_at  BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (strategy, mode)
);

CREATE TABLE IF NOT EXISTS positions (
    strategy    TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'spot',
    symbol      TEXT NOT NULL,
    side        SMALLINT NOT NULL,
    qty         DOUBLE PRECISION NOT NULL,
    entry       DOUBLE PRECISION NOT NULL,
    stop        DOUBLE PRECISION,
    target      DOUBLE PRECISION,
    opened_at   BIGINT NOT NULL,
    notional    DOUBLE PRECISION NOT NULL,
    margin_used DOUBLE PRECISION NOT NULL DEFAULT 0,
    risk_amount DOUBLE PRECISION NOT NULL,
    score       DOUBLE PRECISION NOT NULL DEFAULT 0,
    leverage    INTEGER NOT NULL DEFAULT 1,
    rr          DOUBLE PRECISION NOT NULL DEFAULT 1.8,
    reason      TEXT,
    PRIMARY KEY (strategy, symbol, mode)
);

CREATE TABLE IF NOT EXISTS trades (
    id          BIGSERIAL PRIMARY KEY,
    strategy    TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'spot',
    symbol      TEXT NOT NULL,
    side        SMALLINT NOT NULL,
    qty         DOUBLE PRECISION NOT NULL,
    entry       DOUBLE PRECISION NOT NULL,
    exit        DOUBLE PRECISION NOT NULL,
    opened_at   BIGINT NOT NULL,
    closed_at   BIGINT NOT NULL,
    pnl         DOUBLE PRECISION NOT NULL,
    fee         DOUBLE PRECISION NOT NULL,
    reason      TEXT NOT NULL,
    equity_after DOUBLE PRECISION NOT NULL,
    leverage    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS trades_closed ON trades (closed_at DESC);

CREATE TABLE IF NOT EXISTS equity_curve (
    strategy   TEXT NOT NULL,
    mode       TEXT NOT NULL DEFAULT 'spot',
    ts         BIGINT NOT NULL,
    equity     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (strategy, mode, ts)
);

CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL PRIMARY KEY,
    ts          BIGINT NOT NULL,
    strats      TEXT[] NOT NULL DEFAULT '{}',
    symbol      TEXT,
    kind        TEXT NOT NULL,
    message     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_ts ON events (ts DESC);

CREATE TABLE IF NOT EXISTS arena_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    key         TEXT PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT 'Public API Key',
    created_at  BIGINT NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS signals (
    id              TEXT PRIMARY KEY,
    ts              BIGINT NOT NULL,
    mode            TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    strategy_name   TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    action          TEXT NOT NULL,
    side            TEXT NOT NULL,
    leverage        INTEGER NOT NULL DEFAULT 1,
    price           DOUBLE PRECISION NOT NULL,
    stop_loss       DOUBLE PRECISION,
    take_profit     DOUBLE PRECISION,
    risk_reward     TEXT,
    notional_usd    DOUBLE PRECISION,
    margin_usd      DOUBLE PRECISION,
    risk_amount_usd DOUBLE PRECISION,
    pnl_usd         DOUBLE PRECISION,
    message         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS signals_ts ON signals (ts DESC);
CREATE INDEX IF NOT EXISTS signals_strat ON signals (strategy, mode, ts DESC);
"""
