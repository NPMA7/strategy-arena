"""Vectorised indicators over a time window. One call per symbol per closed bar.

Everything runs on the tail window (W bars) so cost stays flat regardless of
how long the ring has been filling.
"""

from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

W = 1440  # window dipakai untuk indikator (hingga 24 jam M1 untuk konfirmasi M15/M30/H1)


def _ema(x: np.ndarray, n: int) -> np.ndarray:
    if x.size == 0:
        return np.empty_like(x)
    a = 2.0 / (n + 1.0)
    b = 1.0 - a
    xs = x.tolist()
    val = float(xs[0])
    out = [val]
    append = out.append
    for v in xs[1:]:
        val = v * a + val * b
        append(val)
    return np.asarray(out, dtype=x.dtype)





def _sma(x: np.ndarray, n: int) -> np.ndarray:
    c = np.concatenate(([0.0], np.cumsum(x)))
    out = np.full_like(x, np.nan)
    if x.size >= n:
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def _rolling_max(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    if x.size >= n:
        out[n - 1:] = sliding_window_view(x, n).max(axis=1)
    return out


def _rolling_min(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    if x.size >= n:
        out[n - 1:] = sliding_window_view(x, n).min(axis=1)
    return out


def _true_range(h, l, c) -> np.ndarray:
    prev = np.roll(c, 1)
    prev[0] = c[0]
    return np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))


def _wilder(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    sz = x.size
    if sz > n:
        val = float(x[1:n + 1].mean())
        out[n] = val
        xs = x.tolist()
        nm1 = n - 1.0
        res = []
        append = res.append
        for v in xs[n + 1:]:
            val = (val * nm1 + v) / n
            append(val)
        if res:
            out[n + 1:] = res
    elif sz == n and n > 0:
        out[n - 1] = float(x.mean())
    return out


class Snap:
    """Latest-window snapshot handed to strategies."""
    __slots__ = (
        "n", "o", "h", "l", "c", "v", "i",
        "ema9", "ema21", "ema50", "ema100", "ema200",
        "sma20", "sma50", "sma200",
        "rsi14", "rsi2", "atr14", "atr50",
        "bb_u", "bb_m", "bb_l", "bb_w",
        "hh20", "ll20", "hh55", "ll55", "hh10", "ll10",
        "macd", "macd_sig", "macd_hist",
        "stoch_k", "stoch_d", "adx", "plus_di", "minus_di",
        "vol_sma20", "ts", "symbol", "market_mode", "custom_sl_tp",
    )


def compute(views: dict[str, np.ndarray]) -> Snap:
    n_all = views["c"].size
    n = min(n_all, W)
    off = n_all - n
    o = views["o"][off:].astype(float)
    h = views["h"][off:].astype(float)
    l = views["l"][off:].astype(float)
    c = views["c"][off:].astype(float)
    v = views["v"][off:].astype(float)
    ts = views["ts"][off:]

    s = Snap()
    s.n = n
    s.o, s.h, s.l, s.c, s.v, s.ts = o, h, l, c, v, ts
    s.i = n - 1
    s.custom_sl_tp = None

    s.ema9 = _ema(c, 9)
    s.ema21 = _ema(c, 21)
    s.ema50 = _ema(c, 50)
    s.ema100 = _ema(c, 100)
    s.ema200 = _ema(c, 200)
    s.sma20 = _sma(c, 20)
    s.sma50 = _sma(c, 50)
    s.sma200 = _sma(c, 200)

    d = np.diff(c, prepend=c[0])
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    s.rsi14 = _rsi(up, dn, 14)
    s.rsi2 = _rsi(up, dn, 2)

    tr = _true_range(h, l, c)
    s.atr14 = _wilder(tr, 14)
    s.atr50 = _wilder(tr, 50)

    sd = _rolling_std(c, 20)
    s.bb_m = s.sma20
    s.bb_u = s.sma20 + 2 * sd
    s.bb_l = s.sma20 - 2 * sd
    s.bb_w = np.where(s.bb_m > 0, (s.bb_u - s.bb_l) / s.bb_m, np.nan)

    s.hh20 = _rolling_max(h, 20)
    s.ll20 = _rolling_min(l, 20)
    s.hh55 = _rolling_max(h, 55)
    s.ll55 = _rolling_min(l, 55)
    s.hh10 = _rolling_max(h, 10)
    s.ll10 = _rolling_min(l, 10)

    s.macd = _ema(c, 12) - _ema(c, 26)
    s.macd_sig = _ema(s.macd, 9)
    s.macd_hist = s.macd - s.macd_sig

    lo14 = _rolling_min(l, 14)
    hi14 = _rolling_max(h, 14)
    rng = np.where((hi14 - lo14) > 0, hi14 - lo14, 1e-12)
    s.stoch_k = (c - lo14) / rng * 100.0
    s.stoch_d = _sma(np.nan_to_num(s.stoch_k), 3)

    # ADX kasar (14): pakai TR sederhana, cukup akurat untuk sinyal
    plus_dm = np.where((h - np.roll(h, 1)) > (np.roll(l, 1) - l), np.maximum(h - np.roll(h, 1), 0.0), 0.0)
    minus_dm = np.where((np.roll(l, 1) - l) > (h - np.roll(h, 1)), np.maximum(np.roll(l, 1) - l, 0.0), 0.0)
    atr = s.atr14
    atr_safe = np.where(atr > 0, atr, 1e-12)
    s.plus_di = 100 * _wilder(plus_dm, 14) / atr_safe
    s.minus_di = 100 * _wilder(minus_dm, 14) / atr_safe
    dx = np.abs(s.plus_di - s.minus_di) / np.where((s.plus_di + s.minus_di) > 0, s.plus_di + s.minus_di, 1e-12) * 100
    s.adx = _wilder(np.nan_to_num(dx), 14)

    s.vol_sma20 = _sma(v, 20)
    return s


def _rsi(up: np.ndarray, dn: np.ndarray, n: int) -> np.ndarray:
    au = _wilder(up, n)
    ad = _wilder(dn, n)
    rs = au / np.where(ad > 0, ad, 1e-12)
    rsi = 100 - 100 / (1 + rs)
    return np.nan_to_num(rsi, nan=50.0)


def _rolling_std(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    if x.size >= n:
        out[n - 1:] = sliding_window_view(x, n).std(axis=1)
    return out
