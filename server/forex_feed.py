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

MT5_BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://mt5-bridge:5000")

FOREX_METAS: list[dict] = [
    {"symbol": "XAUUSD", "base": "XAU", "quote": "USD", "name": "Spot Gold / US Dollar", "digits": 2, "base_price": 4048.45, "pip": 0.1, "vol": 0.50},
    {"symbol": "EURUSD", "base": "EUR", "quote": "USD", "name": "Euro / US Dollar", "digits": 5, "base_price": 1.11317, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "GBPUSD", "base": "GBP", "quote": "USD", "name": "British Pound / US Dollar", "digits": 5, "base_price": 1.32963, "pip": 0.0001, "vol": 0.00010},
    {"symbol": "USDJPY", "base": "USD", "quote": "JPY", "name": "US Dollar / Japanese Yen", "digits": 3, "base_price": 158.060, "pip": 0.01, "vol": 0.015},
    {"symbol": "USDCAD", "base": "USD", "quote": "CAD", "name": "US Dollar / Canadian Dollar", "digits": 5, "base_price": 1.40579, "pip": 0.0001, "vol": 0.010},
    {"symbol": "AUDCAD", "base": "AUD", "quote": "CAD", "name": "Aussie / Canadian Dollar", "digits": 5, "base_price": 0.98874, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "AUDJPY", "base": "AUD", "quote": "JPY", "name": "Aussie / Japanese Yen", "digits": 3, "base_price": 111.175, "pip": 0.01, "vol": 0.015},
    {"symbol": "AUDUSD", "base": "AUD", "quote": "USD", "name": "Aussie / US Dollar", "digits": 5, "base_price": 0.70340, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "EURGBP", "base": "EUR", "quote": "GBP", "name": "Euro / British Pound", "digits": 5, "base_price": 0.83729, "pip": 0.0001, "vol": 0.00006},
    {"symbol": "EURAUD", "base": "EUR", "quote": "AUD", "name": "Euro / Aussie", "digits": 5, "base_price": 1.58271, "pip": 0.0001, "vol": 0.00012},
    {"symbol": "EURJPY", "base": "EUR", "quote": "JPY", "name": "Euro / Japanese Yen", "digits": 3, "base_price": 175.976, "pip": 0.01, "vol": 0.015},
    {"symbol": "EURNZD", "base": "EUR", "quote": "NZD", "name": "Euro / Kiwi", "digits": 5, "base_price": 1.98163, "pip": 0.0001, "vol": 0.00015},
    {"symbol": "GBPJPY", "base": "GBP", "quote": "JPY", "name": "British Pound / Japanese Yen", "digits": 3, "base_price": 210.158, "pip": 0.01, "vol": 0.020},
    {"symbol": "GBPAUD", "base": "GBP", "quote": "AUD", "name": "British Pound / Aussie", "digits": 5, "base_price": 1.89029, "pip": 0.0001, "vol": 0.00015},
    {"symbol": "GBPCAD", "base": "GBP", "quote": "CAD", "name": "British Pound / Canadian Dollar", "digits": 5, "base_price": 1.86909, "pip": 0.0001, "vol": 0.00012},
    {"symbol": "GBPNZD", "base": "GBP", "quote": "NZD", "name": "British Pound / Kiwi", "digits": 5, "base_price": 2.36661, "pip": 0.0001, "vol": 0.00020},
    {"symbol": "NZDUSD", "base": "NZD", "quote": "USD", "name": "Kiwi / US Dollar", "digits": 5, "base_price": 0.56180, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "NZDCAD", "base": "NZD", "quote": "CAD", "name": "Kiwi / Canadian Dollar", "digits": 5, "base_price": 0.78968, "pip": 0.0001, "vol": 0.00010},
    {"symbol": "XTIUSD", "base": "XTI", "quote": "USD", "name": "WTI Crude Oil / US Dollar", "digits": 3, "base_price": 105.690, "pip": 0.01, "vol": 0.05},
    {"symbol": "USDCHF", "base": "USD", "quote": "CHF", "name": "US Dollar / Swiss Franc", "digits": 5, "base_price": 0.83011, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "EURCHF", "base": "EUR", "quote": "CHF", "name": "Euro / Swiss Franc", "digits": 5, "base_price": 0.92439, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "GBPCHF", "base": "GBP", "quote": "CHF", "name": "British Pound / Swiss Franc", "digits": 5, "base_price": 1.10372, "pip": 0.0001, "vol": 0.00010},
    {"symbol": "CADJPY", "base": "CAD", "quote": "JPY", "name": "Canadian Dollar / Japanese Yen", "digits": 3, "base_price": 112.525, "pip": 0.01, "vol": 0.012},
    {"symbol": "CHFJPY", "base": "CHF", "quote": "JPY", "name": "Swiss Franc / Japanese Yen", "digits": 3, "base_price": 190.424, "pip": 0.01, "vol": 0.018},
    {"symbol": "NZDJPY", "base": "NZD", "quote": "JPY", "name": "Kiwi / Japanese Yen", "digits": 3, "base_price": 88.812, "pip": 0.01, "vol": 0.012},
    {"symbol": "AUDNZD", "base": "AUD", "quote": "NZD", "name": "Aussie / Kiwi", "digits": 5, "base_price": 1.25169, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "CADCHF", "base": "CAD", "quote": "CHF", "name": "Canadian Dollar / Swiss Franc", "digits": 5, "base_price": 0.59120, "pip": 0.0001, "vol": 0.00008},
    {"symbol": "AUDCHF", "base": "AUD", "quote": "CHF", "name": "Aussie / Swiss Franc", "digits": 5, "base_price": 0.58410, "pip": 0.0001, "vol": 0.00008},
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
        self.connected = True
        self.is_mt5_live = False
        self.ticks_count = 0
        self._last_mt5_check = 0.0
        self._running = False
        self._task: asyncio.Task | None = None
        self.session: aiohttp.ClientSession | None = None

    def seed_rings(self, rings: dict) -> None:
        """Seed 240 bars (4 jam candle M1) untuk setiap pair Forex agar indikator langsung aktif."""
        from .bars import BarRing
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - (240 * 60 * 1000)

        for meta in FOREX_METAS:
            sym = meta["symbol"]
            ring = rings.get(sym)
            if ring is None:
                ring = rings[sym] = BarRing()

            base = meta["base_price"]
            vol = meta["vol"]
            p = base * (1.0 + random.uniform(-0.004, 0.004))
            self.open_prices_24h[sym] = p

            for b in range(240):
                b_ts = start_ms + (b * 60 * 1000)
                drift = random.gauss(0, vol * 0.8)
                o = p
                c = round(o + drift, meta["digits"])
                h = round(max(o, c) + abs(random.gauss(0, vol * 0.5)), meta["digits"])
                l = round(min(o, c) - abs(random.gauss(0, vol * 0.5)), meta["digits"])
                v = round(random.uniform(50, 450), 2)
                ring.seed(b_ts, o, h, l, c, v)
                p = c

            self.current_prices[sym] = p
            ring.price = p
            ring.last_tick = now_ms

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
                    return True
        except Exception:
            pass
        return False

    async def _feed_loop(self) -> None:
        """Tick generation & bridge poll loop. Mengirimkan live tick tiap 500ms."""
        while self._running:
            try:
                now_sec = time.time()
                now_ms = int(now_sec * 1000)

                # Cek koneksi ke MT5 Bridge secara periodik (setiap 10 detik)
                if now_sec - self._last_mt5_check >= 10.0:
                    self._last_mt5_check = now_sec
                    mt5_ok = await self._check_mt5_bridge()
                    if mt5_ok != self.is_mt5_live:
                        self.is_mt5_live = mt5_ok
                        if mt5_ok:
                            log.info("✓ Terhubung ke MT5 Bridge di %s (Live Realtime Feed)", MT5_BRIDGE_URL)
                        else:
                            log.info("MT5 Bridge offline, menjalankan autonomous Forex Feed simulation.")

                bridge_ticks = None
                if self.is_mt5_live and self.session:
                    try:
                        timeout = aiohttp.ClientTimeout(total=1.5)
                        async with self.session.get(f"{MT5_BRIDGE_URL}/ticks", timeout=timeout) as resp:
                            if resp.status == 200:
                                bridge_ticks = await resp.json()
                    except Exception:
                        pass

                for meta in FOREX_METAS:
                    sym = meta["symbol"]
                    cur = self.current_prices[sym]
                    digits = meta["digits"]

                    if bridge_ticks and sym in bridge_ticks:
                        t_data = bridge_ticks[sym]
                        self.latest_ticks[sym] = t_data
                        new_price = round(float(t_data.get("price") or t_data.get("last") or cur), digits)
                        if t_data.get("day_open") and float(t_data["day_open"]) > 0:
                            self.open_prices_24h[sym] = float(t_data["day_open"])
                    else:
                        # Model Ornstein-Uhlenbeck: variasi mikro dengan tendensi stabil
                        vol = meta["vol"]
                        anchor = meta["base_price"]
                        reversion = 0.02 * (anchor - cur)
                        shock = random.gauss(0, vol)
                        new_price = round(cur + reversion + shock, digits)

                    # Pastikan harga tetap rasional positif
                    if new_price <= 0:
                        new_price = cur

                    self.current_prices[sym] = new_price
                    qty = round(random.uniform(0.1, 5.0), 2)
                    self.volumes_24h[sym] += qty
                    self.ticks_count += 1

                    # Panggil callback on_trade
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
                spr_pts = round(pip * random.uniform(0.8, 1.8), digits)
                bid = round(cur - spr_pts / 2.0, digits)
                ask = round(cur + spr_pts / 2.0, digits)
            else:
                bid = round(float(bid), digits)
                ask = round(float(ask), digits)

            # Selisih persis mengikuti selisih harga Bid dan Ask
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
