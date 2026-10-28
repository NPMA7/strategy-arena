"""Ring buffer of OHLCV bars per symbol, with fast numpy views for indicators."""

from __future__ import annotations

import numpy as np

CAP = 720  # 12 jam candle 1 menit


class BarRing:
    """Fixed capacity circular buffer. Arrays are contiguous float64."""

    __slots__ = ("ts", "o", "h", "l", "c", "v", "n", "head", "last_tick", "price")

    def __init__(self, cap: int = CAP) -> None:
        self.ts = np.zeros(cap, dtype=np.float64)
        self.o = np.zeros(cap)
        self.h = np.zeros(cap)
        self.l = np.zeros(cap)
        self.c = np.zeros(cap)
        self.v = np.zeros(cap)
        self.n = 0
        self.head = 0
        self.last_tick = 0.0
        self.price = 0.0

    def on_trade(self, ts: float, price: float, qty: float) -> bool:
        """Roll the forming bar with a trade tick. Returns True if a bar just closed."""
        self.last_tick = ts
        self.price = price
        bucket = ts // 60000 * 60000
        closed = False
        if self.n == 0:
            self._push(bucket, price, price, price, price, qty)
            return False
        last_ts = self.ts[(self.head - 1) % len(self.ts)]

        if bucket > last_ts:
            closed = True
            # kalau ada menit yang terlewat tanpa tick, isi datar supaya indeks waktu tetap benar
            while bucket - last_ts > 60000:
                last_ts += 60000
                close = self.c[(self.head - 1) % len(self.ts)]
                self._push(last_ts, close, close, close, close, 0.0)
            self._push(bucket, price, price, price, price, qty)
        else:
            i = (self.head - 1) % len(self.ts)
            if price > self.h[i]:
                self.h[i] = price
            if price < self.l[i]:
                self.l[i] = price
            self.c[i] = price
            self.v[i] += qty
        return closed

    def seed(self, open_t: int, o: float, h: float, l: float, c: float, v: float) -> None:
        self._push(open_t, o, h, l, c, v)

    def _push(self, t, o, h, l, c, v) -> None:
        i = self.head
        self.ts[i] = t
        self.o[i] = o
        self.h[i] = h
        self.l[i] = l
        self.c[i] = c
        self.v[i] = v
        self.head = (i + 1) % len(self.ts)
        if self.n < len(self.ts):
            self.n += 1

    def views(self) -> dict[str, np.ndarray]:
        """Chronological contiguous copies (oldest → newest)."""
        cap = len(self.ts)
        if self.n < cap:
            sl = slice(0, self.n)
            return {"ts": self.ts[sl], "o": self.o[sl], "h": self.h[sl], "l": self.l[sl], "c": self.c[sl], "v": self.v[sl]}
        idx = np.arange(self.head, self.head + cap) % cap
        return {"ts": self.ts[idx], "o": self.o[idx], "h": self.h[idx], "l": self.l[idx], "c": self.c[idx], "v": self.v[idx]}

    @property
    def last_close(self) -> float:
        if self.n == 0:
            return 0.0
        return float(self.c[(self.head - 1) % len(self.c)])
