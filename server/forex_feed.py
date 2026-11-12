"""Forex Market Feed: Menghubungkan Strategy Arena ke MetaTrader 5 Bridge atau
menyediakan streaming real-time feed untuk seluruh 22 pair Forex & Metals.

Mendukung:
1. Koneksi ke MT5 Bridge (Wine + Flask API di container Linux).
2. Autonomous realistic tick/bar engine jika MT5 Bridge belum terhubung (local dev / pre-VPS).
3. Pre-seed 240 historical 1-minute bars per symbol agar indikator (EMA200, ATR, RSI, BB)
   langsung terisi dan siap dihitung seketika tanpa jeda pemanasan.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import random
import time
from typing import Awaitable, Callable

import aiohttp

log = logging.getLogger("arena.forex")

from .config import MT5_BRIDGE_URL

FOREX_METAS: list[dict] = [
    {"symbol": "XAUUSD", "base": "XAU", "quote": "USD", "name": "Spot Gold / US Dollar", "digits": 2, "base_price": 4094.68, "pip": 0.1, "vol": 0.50},
    {"symbol": "EURUSD", "base": "EUR", "quote": "USD", "name": "Euro / US Dollar", "digits": 5, "base_price": 1.11870, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "GBPUSD", "base": "GBP", "quote": "USD", "name": "British Pound / US Dollar", "digits": 5, "base_price": 1.34131, "pip": 0.0001, "vol": 0.00010},
    {"symbol": "USDJPY", "base": "USD", "quote": "JPY", "name": "US Dollar / Japanese Yen", "digits": 3, "base_price": 158.000, "pip": 0.01, "vol": 0.015},
    {"symbol": "USDCAD", "base": "USD", "quote": "CAD", "name": "US Dollar / Canadian Dollar", "digits": 5, "base_price": 1.40808, "pip": 0.0001, "vol": 0.010},
    {"symbol": "AUDCAD", "base": "AUD", "quote": "CAD", "name": "Aussie / Canadian Dollar", "digits": 5, "base_price": 0.97166, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "AUDJPY", "base": "AUD", "quote": "JPY", "name": "Aussie / Japanese Yen", "digits": 3, "base_price": 109.041, "pip": 0.01, "vol": 0.015},
    {"symbol": "AUDUSD", "base": "AUD", "quote": "USD", "name": "Aussie / US Dollar", "digits": 5, "base_price": 0.69012, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "EURGBP", "base": "EUR", "quote": "GBP", "name": "Euro / British Pound", "digits": 5, "base_price": 0.83405, "pip": 0.0001, "vol": 0.00006},
    {"symbol": "EURAUD", "base": "EUR", "quote": "AUD", "name": "Euro / Aussie", "digits": 5, "base_price": 1.62111, "pip": 0.0001, "vol": 0.00012},
    {"symbol": "EURJPY", "base": "EUR", "quote": "JPY", "name": "Euro / Japanese Yen", "digits": 3, "base_price": 176.768, "pip": 0.01, "vol": 0.015},
    {"symbol": "EURNZD", "base": "EUR", "quote": "NZD", "name": "Euro / Kiwi", "digits": 5, "base_price": 1.99576, "pip": 0.0001, "vol": 0.00015},
    {"symbol": "GBPJPY", "base": "GBP", "quote": "JPY", "name": "British Pound / Japanese Yen", "digits": 3, "base_price": 211.923, "pip": 0.01, "vol": 0.020},
    {"symbol": "GBPAUD", "base": "GBP", "quote": "AUD", "name": "British Pound / Aussie", "digits": 5, "base_price": 1.94353, "pip": 0.0001, "vol": 0.00015},
    {"symbol": "GBPCAD", "base": "GBP", "quote": "CAD", "name": "British Pound / Canadian Dollar", "digits": 5, "base_price": 1.88852, "pip": 0.0001, "vol": 0.012},
    {"symbol": "GBPNZD", "base": "GBP", "quote": "NZD", "name": "British Pound / Kiwi", "digits": 5, "base_price": 2.39270, "pip": 0.0001, "vol": 0.00020},
    {"symbol": "NZDUSD", "base": "NZD", "quote": "USD", "name": "Kiwi / US Dollar", "digits": 5, "base_price": 0.56057, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "NZDCAD", "base": "NZD", "quote": "CAD", "name": "Kiwi / Canadian Dollar", "digits": 5, "base_price": 0.78924, "pip": 0.0001, "vol": 0.00010},
    {"symbol": "XTIUSD", "base": "XTI", "quote": "USD", "name": "WTI Crude Oil / US Dollar", "digits": 3, "base_price": 93.990, "pip": 0.01, "vol": 0.05},
    {"symbol": "USDCHF", "base": "USD", "quote": "CHF", "name": "US Dollar / Swiss Franc", "digits": 5, "base_price": 0.81824, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "EURCHF", "base": "EUR", "quote": "CHF", "name": "Euro / Swiss Franc", "digits": 5, "base_price": 0.91543, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "GBPCHF", "base": "GBP", "quote": "CHF", "name": "British Pound / Swiss Franc", "digits": 5, "base_price": 1.09749, "pip": 0.0001, "vol": 0.00010},
    {"symbol": "CADJPY", "base": "CAD", "quote": "JPY", "name": "Canadian Dollar / Japanese Yen", "digits": 3, "base_price": 112.217, "pip": 0.01, "vol": 0.012},
    {"symbol": "CHFJPY", "base": "CHF", "quote": "JPY", "name": "Swiss Franc / Japanese Yen", "digits": 3, "base_price": 193.095, "pip": 0.01, "vol": 0.018},
    {"symbol": "NZDJPY", "base": "NZD", "quote": "JPY", "name": "Kiwi / Japanese Yen", "digits": 3, "base_price": 88.569, "pip": 0.01, "vol": 0.012},
    {"symbol": "AUDNZD", "base": "AUD", "quote": "NZD", "name": "Aussie / Kiwi", "digits": 5, "base_price": 1.23111, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "CADCHF", "base": "CAD", "quote": "CHF", "name": "Canadian Dollar / Swiss Franc", "digits": 5, "base_price": 0.58113, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "AUDCHF", "base": "AUD", "quote": "CHF", "name": "Aussie / Swiss Franc", "digits": 5, "base_price": 0.56468, "pip": 0.0001, "vol": 0.00008},
]

META_MAP = {m["symbol"]: m for m in FOREX_METAS}


class ForexFeed:
    def __init__(self, on_trade: Callable[[str, float, float, float], Awaitable[None]]) -> None:
        self.on_trade = on_trade
        self.symbols = [m["symbol"] for m in FOREX_METAS]
        self.current_prices: dict[str, float] = {m["symbol"]: m["base_price"] for m in FOREX_METAS}
        self.open_prices_24h: dict[str, float] = {m["symbol"]: m["base_price"] for m in FOREX_METAS}
        self.volumes_24h: dict[str, float] = {m["symbol"]: 50000.0 for m in FOREX_METAS}
        self.latest_ticks: dict[str, dict] = {}
        self._last_quote: dict[str, tuple] = {}
        self._last_bar_min: dict[str, int] = {}
        self.connected = True
        self.is_mt5_live = False
        self.ticks_count = 0
        self._last_mt5_check = 0.0
        self._running = False
        self._task: asyncio.Task | None = None
        self.session: aiohttp.ClientSession | None = None

    def seed_rings(self, rings: dict, initial_ticks: dict | None = None, symbols_only: list[str] | None = None) -> None:
        """Fallback: Seed historical 1m bars jika MT5 historical bars tidak tersedia."""
        from .bars import BarRing
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - (240 * 60 * 1000)
        target_syms = set(symbols_only) if symbols_only is not None else None

        for meta in FOREX_METAS:
            sym = meta["symbol"]
            if target_syms is not None and sym not in target_syms:
                continue
            ring = rings.get(sym)
            if ring is None:
                ring = rings[sym] = BarRing(offset_ms=0)

            base = meta["base_price"]
            if initial_ticks and sym in initial_ticks:
                t_val = initial_ticks[sym]
                t_px = t_val.get("price") or t_val.get("last") or t_val.get("bid")
                if t_px and float(t_px) > 0:
                    base = float(t_px)

            vol = meta["vol"]
            p = base * (1.0 + random.uniform(-0.001, 0.001))
            self.open_prices_24h[sym] = p

            for b in range(240):
                b_ts = start_ms + (b * 60 * 1000)
                if b == 239:
                    c = base
                    o = p
                    h = max(o, c)
                    l = min(o, c)
                else:
                    drift = random.gauss(0, vol * 0.4)
                    o = p
                    c = round(o + drift, meta["digits"])
                    h = round(max(o, c) + abs(random.gauss(0, vol * 0.3)), meta["digits"])
                    l = round(min(o, c) - abs(random.gauss(0, vol * 0.3)), meta["digits"])
                v = round(random.uniform(5, 45), 2)
                ring.seed(b_ts, o, h, l, c, v)
                p = c

            self.current_prices[sym] = base
            ring.price = base
            ring.last_tick = now_ms

    async def seed_rings_from_mt5(self, rings: dict, initial_ticks: dict | None = None, num_bars: int = 1440) -> int:
        """Seed hingga 1440 bar M1 (24 jam) riil dari MT5 Bridge beserta tick_volume asli."""
        from .bars import BarRing
        sem = asyncio.Semaphore(6)
        now_sec = time.time()
        now_ms = int(now_sec * 1000)
        mt5_seeded: set[str] = set()

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async def fetch_sym(meta: dict):
                sym = meta["symbol"]
                url = f"{MT5_BRIDGE_URL}/fetch_data_pos?symbol={sym}&num_bars={num_bars}"
                async with sem:
                    try:
                        async with session.get(url) as resp:
                            if resp.status != 200:
                                return
                            bars = await resp.json()
                            if not isinstance(bars, list) or len(bars) < 10:
                                return
                            # Selaraskan jam server broker MT5 (mis. UTC+2/UTC+3) ke UTC epoch ms
                            last_bar_sec = int(bars[-1]["time"])
                            raw_diff = last_bar_sec - now_sec
                            offset_sec = round(raw_diff / 3600.0) * 3600 if abs(raw_diff) > 600 else 0
                            ring = rings.get(sym)
                            if ring is None:
                                ring = rings[sym] = BarRing(offset_ms=0)
                            for b in bars:
                                b_ts = (int(b["time"]) - offset_sec) * 1000
                                tv = float(b.get("tick_volume") or 0)
                                ring.seed(b_ts, float(b["open"]), float(b["high"]), float(b["low"]), float(b["close"]), tv)
                            last_close = float(bars[-1]["close"])
                            self.current_prices[sym] = last_close
                            self.open_prices_24h[sym] = float(bars[0]["open"])
                            ring.price = last_close
                            ring.last_tick = now_ms
                            mt5_seeded.add(sym)
                    except Exception as exc:
                        log.warning("Gagal seed M1 riil MT5 untuk %s: %s", sym, exc)

            await asyncio.gather(*(fetch_sym(m) for m in FOREX_METAS), return_exceptions=True)

        missing = [m["symbol"] for m in FOREX_METAS if m["symbol"] not in mt5_seeded]
        if missing:
            log.warning("Fallback synthetic seed untuk %d pair Forex yang belum siap di MT5: %s", len(missing), missing)
            self.seed_rings(rings, initial_ticks=initial_ticks, symbols_only=missing)
        log.info("Forex M1 history seeded: %d/%d pair riil MT5 (%d bars target)", len(mt5_seeded), len(FOREX_METAS), num_bars)
        return len(mt5_seeded)

    async def start(self) -> None:
        self._running = True
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2))
        self._task = asyncio.create_task(self._feed_loop())
        log.info("ForexFeed aktif: %d instrumen Forex & Metals siap.", len(self.symbols))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        if self.session:
            await self.session.close()

    async def _check_mt5_bridge(self) -> bool:
        if not self.session:
            return False
        try:
            timeout = aiohttp.ClientTimeout(total=1.5)
            async with self.session.get(f"{MT5_BRIDGE_URL}/health", timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return bool(data.get("connected") and data.get("symbols_count", 0) > 0)
        except Exception:
            pass
        return False

    async def _feed_loop(self) -> None:
        """Tick generation & bridge poll loop. Mengirimkan live tick tiap 500ms."""
        last_pause_log = 0.0
        while self._running:
            try:
                now_sec = time.time()
                now_ms = int(now_sec * 1000)

                # Cek koneksi ke MT5 Bridge secara periodik (setiap 3 detik)
                if now_sec - self._last_mt5_check >= 3.0:
                    self._last_mt5_check = now_sec
                    mt5_ok = await self._check_mt5_bridge()
                    if mt5_ok != self.is_mt5_live:
                        self.is_mt5_live = mt5_ok
                        if mt5_ok:
                            log.info("✓ Terhubung ke MT5 Bridge di %s (Live Realtime Feed)", MT5_BRIDGE_URL)
                        else:
                            log.warning("⏸️ MT5 Bridge offline/kosong. Pembaruan harga Forex DIHENTIKAN SEMENTARA (PAUSED) agar tidak terjadi distorsi harga.")

                bridge_ticks = None
                if self.session:
                    try:
                        timeout = aiohttp.ClientTimeout(total=1.5)
                        async with self.session.get(f"{MT5_BRIDGE_URL}/ticks", timeout=timeout) as resp:
                            if resp.status == 200:
                                bridge_ticks = await resp.json()
                    except Exception:
                        pass

                # Jika MT5 bridge tidak mengembalikan ticks riil, JANGAN gunakan simulasi random! STOP / PAUSE FOREX!
                if not bridge_ticks or not isinstance(bridge_ticks, dict) or len(bridge_ticks) == 0:
                    if now_sec - last_pause_log >= 15.0:
                        last_pause_log = now_sec
                        log.warning("⏸️ MT5 Bridge tidak mengembalikan data tick riil. Forex feed dihentikan (PAUSED) untuk menjaga integritas harga.")
                    self.is_mt5_live = False
                    await asyncio.sleep(1.0)
                    continue

                self.is_mt5_live = True

                for meta in FOREX_METAS:
                    sym = meta["symbol"]
                    if sym not in bridge_ticks:
                        continue
                    t_data = bridge_ticks[sym]
                    cur = self.current_prices[sym]
                    digits = meta["digits"]

                    self.latest_ticks[sym] = t_data
                    new_price = round(float(t_data.get("price") or t_data.get("last") or cur), digits)
                    if t_data.get("day_open") and float(t_data["day_open"]) > 0:
                        self.open_prices_24h[sym] = float(t_data["day_open"])

                    # Pastikan harga tetap rasional positif
                    if new_price <= 0:
                        continue

                    self.current_prices[sym] = new_price
                    quote_sig = (t_data.get("bid"), t_data.get("ask"), t_data.get("last"), t_data.get("time_msc"))
                    prev_sig = self._last_quote.get(sym)
                    now_min = now_ms // 60000
                    quote_changed = prev_sig != quote_sig
                    if quote_changed:
                        self._last_quote[sym] = quote_sig
                        qty = 1.0  # Hitung tick riil hanya saat kuotasi MT5 benar-benar berubah
                        self.volumes_24h[sym] += qty
                        self.ticks_count += 1
                    else:
                        qty = 0.0

                    if quote_changed or self._last_bar_min.get(sym) != now_min:
                        self._last_bar_min[sym] = now_min
                        await self.on_trade(sym, new_price, qty, float(now_ms))

                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.warning("ForexFeed loop tick exception: %s", exc)
                await asyncio.sleep(1)

    def pairs(self) -> list[dict]:
        """Format pair konsisten dengan UI, lengkap dengan Bid, Ask, Spread & Change riil MT5."""
        out = []
        for meta in FOREX_METAS:
            sym = meta["symbol"]
            cur = self.current_prices.get(sym, meta["base_price"])
            t = self.latest_ticks.get(sym, {})
            digits = meta["digits"]
            pip = meta["pip"]

            bid = t.get("bid")
            ask = t.get("ask")
            if bid is None or ask is None:
                bid = cur
                ask = cur
                diff = 0.0
                spr_pips = 0.0
            else:
                bid = round(float(bid), digits)
                ask = round(float(ask), digits)
                diff = round(ask - bid, digits)
                spr_pips = round(diff / pip, 1) if pip > 0 else 0.0

            change = t.get("change")
            if change is None:
                o24 = self.open_prices_24h.get(sym, cur)
                change = round(((cur - o24) / o24 * 100.0), 2) if o24 > 0 else 0.0

            out.append({
                "symbol": sym,
                "base": meta["base"],
                "quote": meta["quote"],
                "name": meta["name"],
                "price": cur,
                "last_close": cur,
                "bid": bid,
                "ask": ask,
                "spread": diff,
                "spread_pips": spr_pips,
                "change": change,
                "digits": digits,
                "pip": pip,
                "category": "forex",
            })
        return out
