"""Binance public data feeds: venue discovery, 24h tickers, and the combined
trade WebSocket. Tidak butuh API key — hanya endpoint publik.

Aliran:
  REST  /api/v3/exchangeInfo      → daftar pair SPOT/TRADING yang aktif
  REST  /api/v3/ticker/24hr       → peringkat volume, dipakai memilih N pair teratas
  WS    wss://stream.binance.com:9443/stream?streams=<sym>@trade/...
        pesan menyusul sebagai {"stream": "btcusdt@trade", "data": {...}}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Awaitable, Callable

import ssl

import aiohttp
import certifi

log = logging.getLogger("arena.binance")

REST = os.getenv("ARENA_BINANCE_REST", "https://data-api.binance.vision")
WS_BASE = os.getenv("ARENA_BINANCE_WS", "wss://data-stream.binance.vision")
PAIR_LIMIT = int(os.getenv("ARENA_PAIRS", "100"))
REFRESH_SEC = 900
MAX_STREAMS_PER_CONN = 220

# SSL context dengan certifi bundle — fix untuk container tanpa system CA
_ssl_ctx = ssl.create_default_context(cafile=certifi.where())

EXCLUDE_BASES = {
    "USDC", "TUSD", "USDP", "FDUSD", "BUSD", "DAI", "EUR", "GBP", "AUD", "TRY", "BRL", "ARS",
    "RUB", "ZAR", "IDR", "UAH", "NGN", "PLN", "RON", "JPY", "BIDR", "AEUR", "XUSD",
}
EXCLUDE_SET = {"WBTC", "WBETH"}


def _is_valid_base(base: str) -> bool:
    """Filter out non-standard tokens: Chinese chars, excessive length, numeric prefixes, etc."""
    if base in EXCLUDE_BASES or base in EXCLUDE_SET:
        return False
    # Reject non-ASCII (Chinese, emoji, etc.)
    if not base.isascii():
        return False
    # Must be uppercase alphanumeric only
    if not base.isalnum() or not base.isupper():
        return False
    # Reject suspiciously long tickers (>10 chars usually meme/spam)
    if len(base) > 10:
        return False
    # Reject tickers starting with digits
    if base[0].isdigit():
        return False
    # Reject known spam/meme patterns
    spam_patterns = ("BULL", "BEAR", "UP", "DOWN", "HALF", "MOON", "BABY", "TEST")
    for pat in spam_patterns:
        if base.endswith(pat) and len(base) > len(pat) + 2:
            return False
    return True


class BinanceFeed:
    def __init__(self, on_trade: Callable[[str, float, float, float], Awaitable[None]]) -> None:
        self.on_trade = on_trade
        self.session: aiohttp.ClientSession | None = None
        self.symbols: list[str] = []
        self.info: dict[str, dict] = {}
        self.quote_volume: dict[str, float] = {}
        self.connected = False
        self.last_msg = 0.0
        self.messages = 0
        self._task: asyncio.Task | None = None
        self._stream_task: asyncio.Task | None = None
        self._refresh_task: asyncio.Task | None = None
        self._stopping = False
        self._events: dict[str, dict] = {}

    async def start(self) -> None:
        connector = aiohttp.TCPConnector(ssl=_ssl_ctx, limit=30)
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60, connect=20),
            headers={"User-Agent": "strategy-arena/1.0"},
            connector=connector,
        )
        # Retry exchangeInfo up to 5 times
        data = None
        for attempt in range(5):
            try:
                async with self.session.get(REST + "/api/v3/exchangeInfo") as r:
                    data = await r.json()
                break
            except Exception as exc:
                log.warning("exchangeInfo attempt %d gagal: %s", attempt + 1, exc)
                await asyncio.sleep(3)
        if data is None:
            raise RuntimeError("gagal fetch exchangeInfo setelah 5 percobaan")
        for s in data.get("symbols", []):
            if s.get("status") != "TRADING" or not s.get("isSpotTradingAllowed"):
                continue
            if s.get("quoteAsset") != "USDT":
                continue
            base = s["baseAsset"]
            if not _is_valid_base(base):
                continue
            self.info[s["symbol"]] = {"base": base, "quote": s["quoteAsset"]}
        log.info("exchangeInfo: %d valid pair USDT spot (filtered from total)", len(self.info))

        await self.refresh_top()
        self._task = asyncio.create_task(self._run_streams(), name="binance-ws")
        self._refresh_task = asyncio.create_task(self._refresh_loop(), name="binance-refresh")

    async def refresh_top(self) -> None:
        tickers = None
        for attempt in range(3):
            try:
                async with self.session.get(REST + "/api/v3/ticker/24hr") as r:
                    tickers = await r.json()
                break
            except Exception as exc:
                log.warning("ticker/24hr attempt %d gagal: %s", attempt + 1, exc)
                await asyncio.sleep(3)
        if tickers is None:
            log.error("gagal fetch ticker/24hr setelah 3 percobaan")
            return
        vol = {}
        last = {}
        for t in tickers:
            sym = t.get("symbol")
            if sym in self.info:
                v = float(t.get("quoteVolume") or 0)
                p = float(t.get("lastPrice") or 0)
                # Skip pairs with zero price or negligible volume
                if p > 0 and v > 1000:
                    vol[sym] = v
                    last[sym] = p
        ranked = sorted(vol, key=vol.get, reverse=True)[:PAIR_LIMIT]
        self.quote_volume = vol
        self._events = {}
        for i, sym in enumerate(ranked):
            self._events[sym] = {
                "symbol": sym, "base": self.info[sym]["base"], "quote": "USDT",
                "rank": i + 1, "quote_volume": vol[sym], "last_close": last.get(sym),
            }
        new_list = list(ranked)  # already sorted by volume desc
        changed = new_list != self.symbols
        self.symbols = new_list
        log.info("top %d pair by 24h volume (changed=%s)", len(self.symbols), changed)
        if changed and self._stream_task and not self._stream_task.done():
            log.info("daftar pair berubah, restart WS stream chunked untuk melacak pair baru...")
            self._stream_task.cancel()

    def get_futures_pairs(self) -> list[dict]:
        """Return subset of spot pairs that are commonly available on Binance USDT-M Futures.
        Filtered automatically from top volume pairs using known futures base assets.
        Hasil di-cache; filter hanya dihitung ulang saat daftar symbol berubah."""
        from .strategies import KNOWN_FUTURES_BASES
        cache_key = len(self.symbols) * 1000003 + hash(tuple(self.symbols))
        if getattr(self, "_fp_key", None) == cache_key:
            return self._fp_cache
        result = []
        for sym in self.symbols:
            ev = self._events.get(sym)
            if not ev:
                continue
            base = ev["base"]
            # Include if base is in known futures set, OR if it's in top 30 by volume
            # (new listings often appear in top volume before being added to known set)
            if base in KNOWN_FUTURES_BASES or ev["rank"] <= 30:
                result.append(ev)
        self._fp_key = cache_key
        self._fp_cache = result
        log.info("futures pairs: %d (filtered from %d spot pairs)", len(result), len(self.symbols))
        return result

    async def _refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(REFRESH_SEC)
            try:
                await self.refresh_top()
            except Exception as exc:  # jaringan bisa putus
                log.warning("refresh ticker gagal: %s", exc)

    async def seed_klines(self, symbols: list[str], rings: dict, limit: int = 250) -> int:
        """Seed BarRings with historical 1m klines concurrently on startup."""
        sem = asyncio.Semaphore(20)
        total_seeded = 0

        async def fetch_and_seed(sym: str):
            nonlocal total_seeded
            url = f"{REST}/api/v3/klines?symbol={sym}&interval=1m&limit={limit}"
            async with sem:
                try:
                    async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                        if r.status != 200:
                            return
                        data = await r.json()
                        if not isinstance(data, list) or not data:
                            return
                        ring = rings.get(sym)
                        if ring is None:
                            from .bars import BarRing
                            ring = rings[sym] = BarRing()
                        for k in data:
                            # k: [open_time, open, high, low, close, volume, ...]
                            open_t = int(k[0])
                            o = float(k[1])
                            h = float(k[2])
                            l = float(k[3])
                            c = float(k[4])
                            v = float(k[5])
                            ring.seed(open_t, o, h, l, c, v)
                        if data:
                            ring.last_tick = float(data[-1][6])
                            ring.price = float(data[-1][4])
                        total_seeded += 1
                except Exception as exc:
                    log.warning("seed_klines %s gagal: %s", sym, exc)

        tasks = [fetch_and_seed(s) for s in symbols]
        await asyncio.gather(*tasks, return_exceptions=True)
        log.info("seed_klines selesai: %d/%d pair siap dengan %d bar", total_seeded, len(symbols), limit)
        return total_seeded

    def pairs(self) -> list[dict]:
        return [self._events[s] for s in self.symbols if s in self._events]

    async def _run_streams(self) -> None:
        while not self._stopping:
            try:
                self._stream_task = asyncio.create_task(self._stream_chunked())
                await self._stream_task
            except asyncio.CancelledError:
                if self._stopping:
                    raise
                log.info("WS stream task di-reconnect untuk pair baru...")
                await asyncio.sleep(1)
            except Exception as exc:
                self.connected = False
                log.warning("WS terputus: %s — sambung ulang 5s", exc)
                await asyncio.sleep(5)

    async def _stream_chunked(self) -> None:
        syms = list(self.symbols)
        chunks = [syms[i:i + MAX_STREAMS_PER_CONN] for i in range(0, len(syms), MAX_STREAMS_PER_CONN)]
        await asyncio.gather(*[self._stream_one(part) for part in chunks])

    async def _stream_one(self, part: list[str]) -> None:
        streams = "/".join(f"{s.lower()}@trade" for s in part)
        url = f"{WS_BASE}/stream?streams={streams}"
        ticker = {}
        for s in part:
            ticker[s] = self.info[s]["base"] + self.info[s]["quote"]
        while True:
            try:
                async with self.session.ws_connect(url, heartbeat=20, max_msg_size=8 * 1024 * 1024) as ws:
                    self.connected = True
                    log.info("WS tersambung: %d stream", len(part))
                    async for msg in ws:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
                            continue
                        try:
                            raw = json.loads(msg.data)
                        except Exception:
                            continue
                        data = raw.get("data") or raw
                        s = (data.get("s") or "").upper()
                        if s not in ticker:
                            continue
                        price = float(data["p"])
                        qty = float(data["q"])
                        ts = float(data["T"])
                        self.messages += 1
                        self.last_msg = time.time()
                        await self.on_trade(s, price, qty, ts)
                        self.trades_hit = getattr(self, "trades_hit", 0) + 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("stream chunk putus (%d): %s", len(part), exc)
            self.connected = False
            await asyncio.sleep(5)
