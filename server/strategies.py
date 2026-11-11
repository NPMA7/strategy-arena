"""89 Universal Multi-Market Quantitative Strategies (Spot, Futures, Forex).

Kontrak sinyal per strategy (dipanggil satu kali per bar tertutup per symbol):

    score(s) -> float in [-1, 1]

  > +0.15  long   ·   < -0.15  short   ·   selain itu diam.

Spot mode: hanya LONG yang dieksekusi, fee 0.05% per sisi.
Futures mode: LONG + SHORT, leverage configurable per strategi (5-20x), funding rate 8 jam,
              fee maker 0.02% / taker 0.05%.
Forex mode: LONG + SHORT, MT5 direct lot sizing & spread broker riil, no funding fee.
"""

from __future__ import annotations

from typing import Callable
from .config import SINGLE_POS_CAP

MAX_POS = 5            # batas concurrent positions per strategi (bisa pegang hingga 5 pair berbeda)
TOTAL_NOTIONAL_CAP = 1.0   # max 100% equity total notional (spot) / margin (futures)
TOTAL_RISK_CAP = 0.20      # max 20% equity total risk exposure
LONG, SHORT = 1, -1

# Default leverage per strategi (futures mode). Bisa 1-125x.
# Strategi konservatif dapat leverage rendah, agresif lebih tinggi.
DEFAULT_LEVERAGE: dict[str, int] = {}  # diisi di bawah setelah STRATEGIES didefinisikan

# Funding rate simulation: rata-rata 0.01% per 8 jam (Binance historical average)
FUNDING_RATE_DEFAULT = 0.0001
FUNDING_INTERVAL_SEC = 8 * 3600  # 8 jam

# Fee structure
SPOT_FEE = 0.0005        # 0.05% taker
FUTURES_MAKER_FEE = 0.0002  # 0.02%
FUTURES_TAKER_FEE = 0.0005  # 0.05% (kita pakai taker sebagai default paper trading)


def _ok(*vals) -> bool:
    for v in vals:
        if v is None or v != v:  # NaN
            return False
    return True


def trend_stack(s):
    e9, e21, e50 = s.ema9[s.i], s.ema21[s.i], s.ema50[s.i]
    c, adx = s.c[s.i], s.adx[s.i]
    if not _ok(e9, e21, e50, adx):
        return 0.0
    if e9 > e21 > e50 and c > e9:
        return min(1.0, 0.35 + adx / 80)
    if e9 < e21 < e50 and c < e9:
        return -min(1.0, 0.35 + adx / 80)
    return 0.0


def ema_cross(s, fast, slow, confirm=None):
    f0, f1 = fast[s.i - 1], fast[s.i]
    s0, s1 = slow[s.i - 1], slow[s.i]
    if not _ok(f0, f1, s0, s1):
        return 0.0
    up = f0 <= s0 and f1 > s1
    dn = f0 >= s0 and f1 < s1
    if confirm is not None and _ok(confirm[s.i]):
        up = up and s.c[s.i] > confirm[s.i]
        dn = dn and s.c[s.i] < confirm[s.i]
    if up:
        return 0.8
    if dn:
        return -0.8
    return 0.0


def breakout(s, up_arr, dn_arr, k_atr=0.0):
    c, prev_c = s.c[s.i], s.c[s.i - 1]
    up, dn = up_arr[s.i - 1], dn_arr[s.i - 1]
    atr = s.atr14[s.i]
    if not _ok(up, dn, prev_c):
        return 0.0
    buffer = k_atr * atr if _ok(atr) else 0.0
    if c > up + buffer:
        return min(1.0, 0.45 + (c - up) / atr * 0.5) if _ok(atr) and atr > 0 else 0.6
    if c < dn - buffer:
        return -min(1.0, 0.45 + (dn - c) / atr * 0.5) if _ok(atr) and atr > 0 else -0.6
    return 0.0


def reversion(s, lo=30, hi=70):
    r0, r1 = s.rsi14[s.i - 1], s.rsi14[s.i]
    if not _ok(r0, r1):
        return 0.0
    if r0 < lo <= r1:
        return 0.8
    if r0 > hi >= r1:
        return -0.8
    return 0.0


def macd_cross(s):
    h0, h1 = s.macd_hist[s.i - 1], s.macd_hist[s.i]
    if not _ok(h0, h1):
        return 0.0
    if h0 <= 0 < h1:
        return 0.7 if s.macd[s.i] > 0 else 0.5
    if h0 >= 0 > h1:
        return -0.7 if s.macd[s.i] < 0 else -0.5
    return 0.0


def rsi_regime(s):
    return reversion(s, 30, 70)


def willr(s):
    """Stochastic %K cross 20/80."""
    k0, k1 = s.stoch_k[s.i - 1], s.stoch_k[s.i]
    d1 = s.stoch_d[s.i]
    if not _ok(k0, k1, d1):
        return 0.0
    if k0 < 20 <= k1 and k1 > d1:
        return 0.75
    if k0 > 80 >= k1 and k1 < d1:
        return -0.75
    return 0.0


def cci(s, n=20):
    pass


def donchian(s):
    return breakout(s, s.hh55, s.ll55)


def keltner(s):
    c = s.c[s.i]
    k_up = s.ema21[s.i] + 2 * s.atr14[s.i]
    k_dn = s.ema21[s.i] - 2 * s.atr14[s.i]
    if not _ok(k_up, k_dn):
        return 0.0
    if c > k_up:
        return 0.7
    if c < k_dn:
        return -0.7
    return 0.0


def bollinger_reversion(s):
    c0, c1 = s.c[s.i - 1], s.c[s.i]
    if not _ok(c0, c1, s.bb_l[s.i], s.bb_l[s.i - 1], s.bb_u[s.i], s.bb_u[s.i - 1]):
        return 0.0
    if c0 < s.bb_l[s.i - 1] and c1 > s.bb_l[s.i]:
        return 0.8
    if c0 > s.bb_u[s.i - 1] and c1 < s.bb_u[s.i]:
        return -0.8
    return 0.0


def squeeze(s):
    i = s.i
    if i < 100 or not _ok(s.bb_u[i], s.bb_l[i]):
        return 0.0
    widths = s.bb_u[i - 99:i + 1] - s.bb_l[i - 99:i + 1]
    avg = float(widths[:-1].mean())
    if avg <= 0 or (s.bb_u[i] - s.bb_l[i]) > avg * 0.75:
        return 0.0
    if s.c[i] > s.bb_u[i] and s.c[i - 1] <= s.bb_u[i - 1]:
        return 0.85
    if s.c[i] < s.bb_l[i] and s.c[i - 1] >= s.bb_l[i - 1]:
        return -0.85
    return 0.0


def volume_breakout(s):
    i = s.i
    if not _ok(s.vol_sma20[i]) or s.vol_sma20[i] <= 0:
        return 0.0
    if s.v[i] < s.vol_sma20[i] * 2.5:
        return 0.0
    return breakout(s, s.hh20, s.ll20)


def vwap_band(s):
    """VWAP jendela 60 candle, mean reversion ke band."""
    i = s.i
    a, b = max(0, i - 59), i + 1
    vv = s.v[a:b]
    tot = float(vv.sum())
    if tot <= 0:
        return 0.0
    vwap = float((s.c[a:b] * vv).sum() / tot)
    sd = float((((s.c[a:b] - vwap) ** 2) * vv).sum() / tot) ** 0.5
    if sd <= 0:
        return 0.0
    z = (s.c[i] - vwap) / sd
    if z < -2:
        return min(0.9, abs(z) / 3)
    if z > 2:
        return -min(0.9, abs(z) / 3)
    return 0.0


def supertrend(s):
    """SuperTrend 14 x 3.0 ATR stateful trailing band."""
    i = s.i
    if i < 20 or not _ok(s.atr14[i]):
        return 0.0
    start = max(1, i - 59)
    final_ub = None
    final_lb = None
    trend = 1
    prev_trend = 1
    for k in range(start, i + 1):
        atr_k = s.atr14[k]
        c_k = s.c[k]
        if not _ok(atr_k, c_k, s.h[k], s.l[k]) or atr_k <= 0:
            continue
        hl2 = 0.5 * (s.h[k] + s.l[k])
        basic_ub = hl2 + 3.0 * atr_k
        basic_lb = hl2 - 3.0 * atr_k
        prev_c = s.c[k - 1]
        if final_ub is None:
            final_ub = basic_ub
            final_lb = basic_lb
            trend = 1 if c_k >= hl2 else -1
            prev_trend = trend
            continue
        prev_trend = trend
        final_ub = basic_ub if (basic_ub < final_ub or prev_c > final_ub) else final_ub
        final_lb = basic_lb if (basic_lb > final_lb or prev_c < final_lb) else final_lb
        if c_k > final_ub:
            trend = 1
        elif c_k < final_lb:
            trend = -1
    if final_ub is None or final_lb is None:
        return 0.0
    if prev_trend == -1 and trend == 1:
        return 0.8
    if prev_trend == 1 and trend == -1:
        return -0.8
    if _ok(s.ema21[i]):
        if trend == 1 and s.c[i] > final_lb and s.c[i] < s.ema21[i]:
            return 0.35
        if trend == -1 and s.c[i] < final_ub and s.c[i] > s.ema21[i]:
            return -0.35
    return 0.0


def ichimoku(s):
    i = s.i
    if i < 55:
        return 0.0
    conv = (float(s.h[i - 8:i + 1].max()) + float(s.l[i - 8:i + 1].min())) / 2
    base = (float(s.h[i - 25:i + 1].max()) + float(s.l[i - 25:i + 1].min())) / 2
    span_a = (conv + base) / 2
    span_b = (float(s.h[i - 51:i + 1].max()) + float(s.l[i - 51:i + 1].min())) / 2
    top, bot = max(span_a, span_b), min(span_a, span_b)
    c = s.c[i]
    if c > top and conv > base:
        return 0.8
    if c < bot and conv < base:
        return -0.8
    return 0.0


def chandelier_exit(s):
    i = s.i
    atr = s.atr14[i]
    if not _ok(atr):
        return 0.0
    long_band = float(s.h[i - 12:i + 1].max()) - 3 * atr
    short_band = float(s.l[i - 12:i + 1].min()) + 3 * atr
    c0, c1 = s.c[i - 1], s.c[i]
    crossed_up = c0 <= long_band < c1
    crossed_dn = c0 >= short_band > c1
    if crossed_up:
        return 0.7
    if crossed_dn:
        return -0.7
    return 0.0


def fvg_ict(s):
    """Fair Value Gap: gap antara high bar-2 dan low bar-0 lalu diisi (retest)."""
    i = s.i
    if i < 3:
        return 0.0
    gap_up = s.l[i - 2] > s.h[i - 4]
    gap_dn = s.h[i - 2] < s.l[i - 4]
    if not (gap_up or gap_dn):
        return 0.0
    c = s.c[i]
    if gap_up and abs(c - (s.l[i - 2] + s.h[i - 4]) / 2) / c < 0.004:
        return 0.65
    if gap_dn and abs(c - (s.h[i - 2] + s.l[i - 4]) / 2) / c < 0.004:
        return -0.65
    return 0.0


def order_block(s):
    """Order block: candle impulsif jauh di luar ATR, lalu harga kembali ke 50%-nya."""
    i = s.i
    if i < 5:
        return 0.0
    atr = s.atr14[i]
    if not _ok(atr) or atr <= 0:
        return 0.0
    body = s.c[i - 1] - s.o[i - 1]
    c = s.c[i]
    if abs(body) < 1.6 * atr:
        return 0.0
    if body > 0:
        mid = (s.o[i - 1] + s.c[i - 1]) / 2
        if mid * 0.998 <= c <= mid * 1.002 and c < s.ema9[i]:
            return 0.7
    else:
        mid = (s.o[i - 1] + s.c[i - 1]) / 2
        if mid * 0.998 <= c <= mid * 1.002 and c > s.ema9[i]:
            return -0.7
    return 0.0


def fib_retrace(s):
    """Retrace ke 38.2–61.8% dari swing 50 bar, searah tren EMA50."""
    i = s.i
    swing_hi = float(s.h[i - 49:i + 1].max())
    swing_lo = float(s.l[i - 49:i + 1].min())
    rng = swing_hi - swing_lo
    if rng <= 0:
        return 0.0
    pos = (s.c[i] - swing_lo) / rng
    e50 = s.ema50[i]
    if not _ok(e50):
        return 0.0
    if 0.35 <= pos <= 0.62 and s.c[i] > e50:
        return 0.65
    if 0.38 <= pos <= 0.65 and s.c[i] < e50:
        return -0.65
    return 0.0


def fib_golden_pocket(s):
    """Entry di Golden Pocket (61.8% - 65% retracement) dari swing 60 bar dengan konfirmasi candlestick & EMA50."""
    i = s.i
    if i < 60:
        return 0.0
    swing_hi = float(s.h[i - 59:i + 1].max())
    swing_lo = float(s.l[i - 59:i + 1].min())
    rng = swing_hi - swing_lo
    if rng <= 0:
        return 0.0
    c = s.c[i]
    e50 = s.ema50[i]
    if not _ok(e50):
        return 0.0
    # Bullish GP: koreksi turun 61.8% - 66% dari swing low ke swing high
    fib_depth_bull = (swing_hi - c) / rng
    if 0.60 <= fib_depth_bull <= 0.68 and c > e50 and c > s.o[i]:
        return 0.75
    # Bearish GP: koreksi naik 61.8% - 66% dari swing high ke swing low
    fib_depth_bear = (c - swing_lo) / rng
    if 0.60 <= fib_depth_bear <= 0.68 and c < e50 and c < s.o[i]:
        return -0.75
    return 0.0


def fib_expansion_1618(s):
    """Breakout ekspansi Fibonacci 1.272–1.618 ekstensi dengan dorongan momentum."""
    i = s.i
    if i < 40:
        return 0.0
    recent_hi = float(s.h[i - 20:i].max())
    recent_lo = float(s.l[i - 20:i].min())
    rng = recent_hi - recent_lo
    if rng <= 0:
        return 0.0
    c = s.c[i]
    # Breakout ke zona ekstensi 1.272
    target_ext_bull = recent_hi + rng * 0.272
    target_ext_bear = recent_lo - rng * 0.272
    if c > target_ext_bull and s.c[i - 1] <= target_ext_bull and c > s.ema21[i]:
        return 0.7
    if c < target_ext_bear and s.c[i - 1] >= target_ext_bear and c < s.ema21[i]:
        return -0.7
    return 0.0


def pivot_bounce(s):
    """Support/Resistance Bounce: memantul naik dari S1 atau ditolak turun dari R1."""
    i = s.i
    piv = (s.h[i - 1] + s.l[i - 1] + s.c[i - 1]) / 3
    r1 = 2 * piv - s.l[i - 1]
    s1 = 2 * piv - s.h[i - 1]
    c = s.c[i]
    if (s.l[i] <= s1 or s.c[i - 1] <= s1) and c > s1 and c > s.o[i]:
        return 0.6
    if (s.h[i] >= r1 or s.c[i - 1] >= r1) and c < r1 and c < s.o[i]:
        return -0.6
    return 0.0


def time_filter(s):
    """Bias sesi: London open cenderung impulsif, NY close cenderung mean-revert."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if 7 <= hour <= 10 or 13 <= hour <= 15:
        return trend_stack(s) * 1.15
    if 20 <= hour <= 22:
        return -trend_stack(s) * 0.9
    return 0.0


def mean_ema(s, fast, slow):
    """Linreg-ish: deviasi close dari rata-rata dua EMA."""
    i = s.i
    f, sl = fast[i], slow[i]
    if not _ok(f, sl):
        return 0.0
    mid = (f + sl) / 2
    if mid <= 0:
        return 0.0
    dev = (s.c[i] - mid) / mid
    if abs(dev) < 0.0015:
        return 0.0
    return max(-0.9, min(0.9, dev * 250))


def adx_trend(s):
    i = s.i
    adx = s.adx[i]
    if not _ok(adx):
        return 0.0
    if adx < 22:
        return 0.0
    if s.plus_di[i] > s.minus_di[i]:
        return min(0.9, adx / 55)
    return -min(0.9, adx / 55)


def roc_momentum(s):
    i = s.i
    if i < 12:
        return 0.0
    roc = s.c[i] / s.c[i - 12] - 1
    if abs(roc) < 0.0025:
        return 0.0
    return max(-0.9, min(0.9, roc * 120))


def hot_momentum(s):
    """Momentum paling agresif: follow candle tubuh > 2 ATR."""
    i = s.i
    atr = s.atr14[i]
    if not _ok(atr) or atr <= 0:
        return 0.0
    body = s.c[i] - s.o[i]
    if body > 2 * atr:
        return 0.9
    if body < -2 * atr:
        return -0.9
    return 0.0


def fractal_break(s):
    i = s.i
    if i < 6:
        return 0.0
    c, l2, h2 = s.c[i], s.l[i - 2], s.h[i - 2]
    left_dn = s.l[i - 4] > l2 < s.l[i]
    left_up = s.h[i - 4] < h2 > s.h[i]
    if left_dn and c > s.h[i - 1]:
        return 0.6
    if left_up and c < s.l[i - 1]:
        return -0.6
    return 0.0


def pairs_ratio(s, alt=None):
    return 0.0


def volatility_target(s):
    """Trading saat volatilitas normal: follow tren hanya kalau ATR/close sehat."""
    i = s.i
    atr, c = s.atr14[i], s.c[i]
    if not _ok(atr, c) or c <= 0:
        return 0.0
    vol = atr / c
    if not (0.0003 <= vol <= 0.012):
        return 0.0
    return trend_stack(s) * 0.8


def gap_fill(s):
    i = s.i
    if i < 2:
        return 0.0
    prev_c = s.c[i - 1]
    open_gap = (s.o[i] - prev_c) / prev_c if prev_c > 0 else 0.0
    if open_gap > 0.006:
        return -0.55
    if open_gap < -0.006:
        return 0.55
    return 0.0


def rotation(s):
    """RSI di zona netral + MACD cross = rotasi momentum jangka pendek."""
    i = s.i
    r = s.rsi14[i]
    if not _ok(r):
        return 0.0
    m = macd_cross(s)
    if 45 <= r <= 65 and m > 0:
        return m
    if 35 <= r <= 55 and m < 0:
        return m
    return 0.0


def macd_divergence(s):
    """Deteksi divergensi MACD vs harga dengan dua jendela terpisah (disjoint)."""
    i = s.i
    if i < 30:
        return 0.0
    px_low_prev = float(s.l[i - 30:i - 14].min())
    px_low_now = float(s.l[i - 14:i + 1].min())
    macd_low_prev = float(s.macd[i - 30:i - 14].min())
    macd_low_now = float(s.macd[i - 14:i + 1].min())
    px_hi_prev = float(s.h[i - 30:i - 14].max())
    px_hi_now = float(s.h[i - 14:i + 1].max())
    macd_hi_prev = float(s.macd[i - 30:i - 14].max())
    macd_hi_now = float(s.macd[i - 14:i + 1].max())
    if px_low_now < px_low_prev and macd_low_now > macd_low_prev and s.c[i] > s.ema9[i]:
        return 0.65
    if px_hi_now > px_hi_prev and macd_hi_now < macd_hi_prev and s.c[i] < s.ema9[i]:
        return -0.65
    return 0.0


def tr_break(s):
    """True Range expansion: lawan impuls ekstrem sesaat."""
    i = s.i
    atr = s.atr14[i]
    if not _ok(atr) or atr <= 0:
        return 0.0
    tr = max(s.h[i] - s.l[i], abs(s.h[i] - s.c[i - 1]), abs(s.l[i] - s.c[i - 1]))
    if tr < 2.4 * atr:
        return 0.0
    if s.c[i] > s.o[i]:
        return -0.8
    if s.c[i] < s.o[i]:
        return 0.8
    return 0.0


def ewma_trend(s):
    """EMA200 sebagai garis bias, EMA9 untuk timing."""
    i = s.i
    e200, e9 = s.ema200[i], s.ema9[i]
    if not _ok(e200, e9):
        return 0.0
    if s.c[i] > e200 and s.c[i] > e9:
        return 0.55
    if s.c[i] < e200 and s.c[i] < e9:
        return -0.55
    return 0.0


def price_action_2b(s):
    """Reversal 2B: dua kali gagal menembus swing dengan wick panjang."""
    i = s.i
    if i < 6:
        return 0.0
    h2 = float(s.h[i - 5:i - 1].max())
    l2 = float(s.l[i - 5:i - 1].min())
    if s.h[i - 1] > h2 and s.h[i] < s.h[i - 1] and s.c[i] < s.c[i - 1]:
        return -0.6
    if s.l[i - 1] < l2 and s.l[i] > s.l[i - 1] and s.c[i] > s.c[i - 1]:
        return 0.6
    return 0.0


def swing_break(s):
    i = s.i
    if i < 10:
        return 0.0
    h = float(s.h[i - 10:i - 1].max())
    l = float(s.l[i - 10:i - 1].min())
    atr = s.atr14[i]
    if not _ok(atr) or atr <= 0:
        return 0.0
    if s.c[i] > h + 0.25 * atr and s.v[i] > s.v[i - 1]:
        return 0.6
    if s.c[i] < l - 0.25 * atr and s.v[i] > s.v[i - 1]:
        return -0.6
    return 0.0


def inner_bar(s):
    i = s.i
    if i < 3:
        return 0.0
    inside = s.h[i - 1] <= s.h[i - 2] and s.l[i - 1] >= s.l[i - 2]
    if not inside:
        return 0.0
    if s.c[i] > s.h[i - 1]:
        return 0.6
    if s.c[i] < s.l[i - 1]:
        return -0.6
    return 0.0


def mean_candle(s):
    i = s.i
    if i < 10:
        return 0.0
    body = s.c[i] - s.o[i]
    rng = s.h[i] - s.l[i]
    if rng <= 0:
        return 0.0
    if abs(body) / rng > 0.75 and body > 0:
        return 0.45
    if abs(body) / rng > 0.75 and body < 0:
        return -0.45
    return 0.0


def vol_trend_sma(s):
    i = s.i
    if not _ok(s.sma50[i], s.sma200[i]):
        return 0.0
    if s.sma50[i] > s.sma200[i] and s.c[i] > s.sma20[i]:
        return 0.5
    if s.sma50[i] < s.sma200[i] and s.c[i] < s.sma20[i]:
        return -0.5
    return 0.0


def zscore_reversion(s):
    i = s.i
    if i < 30:
        return 0.0
    win = s.c[i - 29:i + 1]
    mu, sd = float(win.mean()), float(win.std())
    if sd <= 0:
        return 0.0
    z = (s.c[i] - mu) / sd
    if z <= -2:
        return 0.8
    if z >= 2:
        return -0.8
    return 0.0


def paint_bar(s):
    """3-Bar Key Reversal / Paint-Bar: sweep high/low 2 bar lalu tutup berbalik menembus kedua bar."""
    i = s.i
    if i < 3:
        return 0.0
    h1, h2 = s.h[i - 1], s.h[i - 2]
    l1, l2 = s.l[i - 1], s.l[i - 2]
    c, l_now, h_now = s.c[i], s.l[i], s.h[i]
    if l_now < min(l1, l2) and c > max(h1, h2) and c > s.o[i]:
        return 0.7
    if h_now > max(h1, h2) and c < min(l1, l2) and c < s.o[i]:
        return -0.7
    return 0.0


def engulfing_pattern(s):
    """Bullish/Bearish Engulfing klasik dengan dominasi body & toleransi ATR kecil."""
    i = s.i
    if i < 2:
        return 0.0
    o1, c1, o2, c2 = s.o[i - 1], s.c[i - 1], s.o[i], s.c[i]
    atr = s.atr14[i]
    if not _ok(o1, c1, o2, c2, atr) or atr <= 0:
        return 0.0
    tol = 0.05 * atr
    b1, b2 = abs(c1 - o1), abs(c2 - o2)
    if b1 <= 0 or b2 < 1.05 * b1:
        return 0.0
    if c1 < o1 and c2 > o2 and o2 <= c1 + tol and c2 >= o1 - tol:
        return 0.65
    if c1 > o1 and c2 < o2 and o2 >= c1 - tol and c2 <= o1 + tol:
        return -0.65
    return 0.0


def ict_orderblock_sweep(s):
    """ICT Order Block Sweep: bar sebelumnya menyapu swing low/high lalu dimitigasi sebagai OB."""
    i = s.i
    if i < 20:
        return 0.0
    atr = s.atr14[i]
    c, o, h, l = s.c[i], s.o[i], s.h[i], s.l[i]
    if not _ok(atr, c, o, h, l) or atr <= 0:
        return 0.0
    for k in range(i - 2, max(i - 10, 15), -1):
        ll_prev = float(s.l[k - 15:k].min())
        if s.l[k] < ll_prev and s.c[k] > s.o[k] and s.c[k + 1] > s.h[k]:
            if float(s.l[k + 1:i].min()) >= s.l[k] and l <= s.h[k] and c >= s.l[k] and c > o:
                return 0.78
            break
    for k in range(i - 2, max(i - 10, 15), -1):
        hh_prev = float(s.h[k - 15:k].max())
        if s.h[k] > hh_prev and s.c[k] < s.o[k] and s.c[k + 1] < s.l[k]:
            if float(s.h[k + 1:i].max()) <= s.h[k] and h >= s.l[k] and c <= s.h[k] and c < o:
                return -0.78
            break
    return 0.0


def two_b_close_reversal(s):
    """Sperandeo 2B Reversal: false breakout 20-bar high/low diikuti close konfirmasi ke dalam range."""
    i = s.i
    if i < 22:
        return 0.0
    hh = float(s.h[i - 21:i - 1].max())
    ll = float(s.l[i - 21:i - 1].min())
    c, o = s.c[i], s.o[i]
    if s.h[i - 1] > hh and c < hh and c < s.l[i - 1] and c < o:
        return -0.75
    if s.l[i - 1] < ll and c > ll and c > s.h[i - 1] and c > o:
        return 0.75
    return 0.0


def value_area_profile(s):
    """Volume Profile Auction: POC & 70% Value Area (VAH/VAL) dari distribusi volume 90 bar."""
    import numpy as np
    i = s.i
    if i < 60:
        return 0.0
    a = max(0, i - 89)
    closes = s.c[a:i + 1]
    vols = s.v[a:i + 1]
    lo, hi = float(closes.min()), float(closes.max())
    if hi <= lo:
        return 0.0
    bins = 12
    weights = np.where(vols > 0, vols, 1.0)
    hist, edges = np.histogram(closes, bins=bins, range=(lo, hi), weights=weights)
    tot = float(hist.sum())
    if tot <= 0:
        return 0.0
    poc_idx = int(np.argmax(hist))
    acc = float(hist[poc_idx])
    l_idx = r_idx = poc_idx
    while acc < 0.70 * tot and (l_idx > 0 or r_idx < bins - 1):
        left_v = float(hist[l_idx - 1]) if l_idx > 0 else -1.0
        right_v = float(hist[r_idx + 1]) if r_idx < bins - 1 else -1.0
        if left_v >= right_v:
            l_idx -= 1
            acc += left_v
        else:
            r_idx += 1
            acc += right_v
    val, vah = float(edges[l_idx]), float(edges[r_idx + 1])
    c, o = s.c[i], s.o[i]
    if c < val and c > o:
        return 0.7
    if c > vah and c < o:
        return -0.7
    return 0.0


def mean_sd_band_mad(s):
    """Robust Median + MAD (Median Absolute Deviation) mean-reversion band."""
    import numpy as np
    i = s.i
    if i < 30:
        return 0.0
    win = s.c[i - 29:i + 1]
    med = float(np.median(win))
    mad = float(np.median(np.abs(win - med)))
    scale = 1.4826 * mad
    if scale <= 0:
        return 0.0
    z = (s.c[i] - med) / scale
    if z <= -2.2:
        return 0.72
    if z >= 2.2:
        return -0.72
    return 0.0


def vwap_trend_follow(s):
    """VWAP Trend Follow: searah VWAP 60-bar + EMA21/EMA50 stack."""
    i = s.i
    if i < 50:
        return 0.0
    a = max(0, i - 59)
    vv = s.v[a:i + 1]
    tot = float(vv.sum())
    if tot <= 0 or not _ok(s.ema21[i], s.ema50[i]):
        return 0.0
    vwap = float((s.c[a:i + 1] * vv).sum() / tot)
    c = s.c[i]
    if c > vwap and c > s.ema21[i] > s.ema50[i]:
        return 0.65
    if c < vwap and c < s.ema21[i] < s.ema50[i]:
        return -0.65
    return 0.0


def candle_imbalance(s):
    """Candle Imbalance (Order Flow Delta Proxy) selaras EMA21."""
    i = s.i
    c, h, l, e21 = s.c[i], s.h[i], s.l[i], s.ema21[i]
    if not _ok(c, h, l, e21):
        return 0.0
    rng = max(h - l, 1e-12)
    if (c - l) > 0.65 * rng and c > e21:
        return 0.65
    if (h - c) > 0.65 * rng and c < e21:
        return -0.65
    return 0.0


def wick_rejection(s):
    """Wick Rejection (Hammer & Shooting Star) pada level EMA21."""
    i = s.i
    o, h, l, c, e21 = s.o[i], s.h[i], s.l[i], s.c[i], s.ema21[i]
    if not _ok(o, h, l, c, e21):
        return 0.0
    body = abs(c - o) + 1e-12
    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)
    if lower_wick > 1.8 * body and l < e21 and c >= o:
        return 0.65
    if upper_wick > 1.8 * body and h > e21 and c <= o:
        return -0.65
    return 0.0


def opening_range_breakout(s):
    """Opening Hour Range Breakout (30m opening box pada awal sesi Asia/London/NY)."""
    i = s.i
    if i < 60 or not _ok(s.c[i], s.c[i - 1], s.ts[i]):
        return 0.0
    cur_ts = int(s.ts[i])
    hour = (cur_ts // 3_600_000) % 24
    # Sesi aktif 2-3 jam pasca open utama: Asia 00-02, London 08-10, NY 13-15 UTC
    if 0 <= hour < 3:
        sess_start_hr = 0
    elif 8 <= hour < 10:
        sess_start_hr = 8
    elif 13 <= hour < 15:
        sess_start_hr = 13
    else:
        return 0.0
    day_ms = (cur_ts // 86_400_000) * 86_400_000
    box_start = day_ms + sess_start_hr * 3_600_000
    box_end = box_start + 30 * 60_000
    if cur_ts < box_end:
        return 0.0
    or_high = None
    or_low = None
    for k in range(max(0, i - 180), i):
        tk = int(s.ts[k])
        if box_start <= tk < box_end:
            or_high = s.h[k] if or_high is None else max(or_high, s.h[k])
            or_low = s.l[k] if or_low is None else min(or_low, s.l[k])
    if or_high is None or or_low is None or or_high <= or_low:
        return 0.0
    if s.c[i] > or_high and s.c[i - 1] <= or_high and s.c[i] > s.o[i]:
        return 0.75
    if s.c[i] < or_low and s.c[i - 1] >= or_low and s.c[i] < s.o[i]:
        return -0.75
    return 0.0


def momentum_weeks(s):
    """Momentum 60 candle bertingkat (gaya time-series momentum)."""
    i = s.i
    if i < 60:
        return 0.0
    r1 = s.c[i] / s.c[i - 20] - 1
    r2 = s.c[i - 20] / s.c[i - 40] - 1
    r3 = s.c[i - 40] / s.c[i - 60] - 1
    if r1 > 0 and r2 > 0 and r3 > 0 and r1 > r2:
        return 0.75
    if r1 < 0 and r2 < 0 and r3 < 0 and r1 < r2:
        return -0.75
    return 0.0


# ── Extended Quantitative Strategies (Universal Multi-Market, 33 Models) ─
def lob_alpha(s):
    """London Open Breakout: Breakout sesi London dengan konfirmasi volume & EMA."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if hour not in (7, 8, 9):
        return 0.0
    c, hh, ll, atr = s.c[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1], s.atr14[s.i]
    if not _ok(c, hh, ll, atr) or atr <= 0:
        return 0.0
    if c > hh and c > s.ema9[s.i]:
        return min(1.0, 0.5 + (c - hh) / atr)
    if c < ll and c < s.ema9[s.i]:
        return -min(1.0, 0.5 + (ll - c) / atr)
    return 0.0


def tokyo_fader(s):
    """Asian Range Mean-Reversion: Fading rentang sempit sesi Tokyo."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if hour >= 7:
        return 0.0
    c, bu, bl, rsi = s.c[s.i], s.bb_u[s.i], s.bb_l[s.i], s.rsi14[s.i]
    if not _ok(c, bu, bl, rsi):
        return 0.0
    if c < bl and rsi < 28:
        return 0.8
    if c > bu and rsi > 72:
        return -0.8
    return 0.0


def frankfurt_probe(s):
    """Frankfurt Liquidity Probe: Menjebak likuiditas awal jam 06:00 UTC."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if hour != 6:
        return 0.0
    c, l, h, ll, hh = s.c[s.i], s.l[s.i], s.h[s.i], s.ll10[s.i - 1], s.hh10[s.i - 1]
    if not _ok(c, l, h, ll, hh):
        return 0.0
    if l < ll and c > s.bb_m[s.i]:
        return 0.75
    if h > hh and c < s.bb_m[s.i]:
        return -0.75
    return 0.0


def ny_reversal(s):
    """New York Institutional Fixing Reversal: Jam 15:00 - 17:00 UTC."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if hour not in (15, 16, 17):
        return 0.0
    c, bu, bl, atr, rsi = s.c[s.i], s.bb_u[s.i], s.bb_l[s.i], s.atr14[s.i], s.rsi14[s.i]
    if not _ok(c, bu, bl, atr, rsi):
        return 0.0
    if c > bu + 0.3 * atr and rsi > 72:
        return -0.8
    if c < bl - 0.3 * atr and rsi < 28:
        return 0.8
    return 0.0


def sunday_gap(s):
    """Sunday / Session Gap Fill: Fade lonjakan harga pembukaan terhadap penutupan sebelumnya."""
    c0, o1 = s.c[s.i - 1], s.o[s.i]
    atr = s.atr14[s.i]
    if not _ok(c0, o1, atr) or atr <= 0:
        return 0.0
    diff = o1 - c0
    if diff > 0.8 * atr:
        return -0.85
    if diff < -0.8 * atr:
        return 0.85
    return 0.0


def aud_nzd_arb(s):
    """Cointegration / Mean-Distance Arb: Deviasi statistik ATR Z-Score dari EMA50."""
    c, e50, atr = s.c[s.i], s.ema50[s.i], s.atr14[s.i]
    if not _ok(c, e50, atr) or atr <= 0:
        return 0.0
    z = (c - e50) / atr
    if z < -2.0:
        return 0.85
    if z > 2.0:
        return -0.85
    return 0.0


def triangular_synth(s):
    """Cross-Rate Triangular Arbitrage Synth: Inefisiensi harga mikro SMA20 + MACD + Stoch."""
    c, sma, hist, stoch = s.c[s.i], s.sma20[s.i], s.macd_hist[s.i], s.stoch_k[s.i]
    if not _ok(c, sma, hist, stoch):
        return 0.0
    if c > sma and hist > 0 and stoch < 35:
        return 0.75
    if c < sma and hist < 0 and stoch > 65:
        return -0.75
    return 0.0


def oil_cad_divergence(s):
    """Macro Divergence Pullback: Pullback melawan tren EMA21/50 pada kondisi RSI moderat."""
    c, e21, e50, rsi = s.c[s.i], s.ema21[s.i], s.ema50[s.i], s.rsi14[s.i]
    if not _ok(c, e21, e50, rsi):
        return 0.0
    if e21 > e50 and c < e21 and rsi < 45:
        return 0.75
    if e21 < e50 and c > e21 and rsi > 55:
        return -0.75
    return 0.0


def gold_safehaven_relay(s):
    """Momentum Breakout Relay: Donchian 20 breakout dengan konfirmasi DI+/DI- & ADX > 22."""
    c, hh, ll, pdi, mdi, adx = s.c[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1], s.plus_di[s.i], s.minus_di[s.i], s.adx[s.i]
    if not _ok(c, hh, ll, pdi, mdi, adx):
        return 0.0
    if c > hh and pdi > mdi and adx > 22:
        return 0.85
    if c < ll and mdi > pdi and adx > 22:
        return -0.85
    return 0.0


def dragon_momentum(s):
    """The Dragon Momentum Rider: High-beta breakout Donchian 20 + EMA9."""
    c, hh, ll, e9, atr = s.c[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1], s.ema9[s.i], s.atr14[s.i]
    if not _ok(c, hh, ll, e9, atr):
        return 0.0
    if c > hh and c > e9:
        return 0.85
    if c < ll and c < e9:
        return -0.85
    return 0.0


def bb_squeeze(s):
    """Bollinger Bandwidth Volatility Explosion."""
    w0, w1 = s.bb_w[s.i - 1], s.bb_w[s.i]
    c, bu, bl = s.c[s.i], s.bb_u[s.i], s.bb_l[s.i]
    if not _ok(w0, w1, c, bu, bl) or w0 <= 0:
        return 0.0
    if w1 > w0 * 1.15 and c > bu:
        return 0.8
    if w1 > w0 * 1.15 and c < bl:
        return -0.8
    return 0.0


def atr_expansion(s):
    """ATR Expansion Channel Breakout."""
    h, l, c, o, atr = s.h[s.i], s.l[s.i], s.c[s.i], s.o[s.i], s.atr14[s.i]
    if not _ok(h, l, c, o, atr) or atr <= 0:
        return 0.0
    if (h - l) > 1.5 * atr and c > o:
        return 0.8
    if (h - l) > 1.5 * atr and c < o:
        return -0.8
    return 0.0


def gold_flash_spike(s):
    """Flash-Spike Mean Reversion: Fade lonjakan > 1.8x ATR pada RSI ekstrem."""
    h, l, c, atr, rsi = s.h[s.i], s.l[s.i], s.c[s.i], s.atr14[s.i], s.rsi14[s.i]
    if not _ok(h, l, c, atr, rsi) or atr <= 0:
        return 0.0
    if (h - l) > 1.8 * atr and c < (h + l) / 2 and rsi > 68:
        return -0.85
    if (h - l) > 1.8 * atr and c > (h + l) / 2 and rsi < 32:
        return 0.85
    return 0.0


def ema_ribbon(s):
    """Multi-Timeframe EMA Ribbon Alignment."""
    e9, e21, e50, e200, c = s.ema9[s.i], s.ema21[s.i], s.ema50[s.i], s.ema200[s.i], s.c[s.i]
    if not _ok(e9, e21, e50, e200, c):
        return 0.0
    if e9 > e21 > e50 > e200 and c > e9:
        return 0.85
    if e9 < e21 < e50 < e200 and c < e9:
        return -0.85
    return 0.0


def supertrend_trailing(s):
    """SuperTrend Dynamic Trailing System (ATR14 x 2.0 fast trailing + EMA21 filter)."""
    i = s.i
    if i < 20 or not _ok(s.atr14[i], s.ema21[i]):
        return 0.0
    start = max(1, i - 39)
    final_ub = None
    final_lb = None
    trend = 1
    prev_trend = 1
    for k in range(start, i + 1):
        atr_k, c_k = s.atr14[k], s.c[k]
        if not _ok(atr_k, c_k, s.h[k], s.l[k]) or atr_k <= 0:
            continue
        hl2 = 0.5 * (s.h[k] + s.l[k])
        b_ub = hl2 + 2.0 * atr_k
        b_lb = hl2 - 2.0 * atr_k
        pc = s.c[k - 1]
        if final_ub is None:
            final_ub, final_lb = b_ub, b_lb
            trend = 1 if c_k >= hl2 else -1
            prev_trend = trend
            continue
        prev_trend = trend
        final_ub = b_ub if (b_ub < final_ub or pc > final_ub) else final_ub
        final_lb = b_lb if (b_lb > final_lb or pc < final_lb) else final_lb
        if c_k > final_ub:
            trend = 1
        elif c_k < final_lb:
            trend = -1
    if prev_trend == -1 and trend == 1 and s.c[i] > s.ema21[i]:
        return 0.82
    if prev_trend == 1 and trend == -1 and s.c[i] < s.ema21[i]:
        return -0.82
    return 0.0


def ichimoku_quantum(s):
    """Ichimoku Kumo Cloud Quantum Breakout."""
    h10, l10 = s.hh10[s.i], s.ll10[s.i]
    h20, l20 = s.hh20[s.i], s.ll20[s.i]
    c, s50 = s.c[s.i], s.sma50[s.i]
    if not _ok(h10, l10, h20, l20, c, s50):
        return 0.0
    tenkan = (h10 + l10) / 2
    kijun = (h20 + l20) / 2
    if tenkan > kijun and c > s50:
        return 0.8
    if tenkan < kijun and c < s50:
        return -0.8
    return 0.0


def heikin_ashi_smooth(s):
    """Heikin-Ashi Smoothed Trend Continuum (kalkulasi HA Open/Close riil)."""
    i = s.i
    if i < 15 or not _ok(s.adx[i]) or s.adx[i] <= 20:
        return 0.0
    ha_o = 0.5 * (s.o[i - 10] + s.c[i - 10])
    ha_c = 0.25 * (s.o[i - 10] + s.h[i - 10] + s.l[i - 10] + s.c[i - 10])
    prev_bull = False
    for k in range(i - 9, i):
        if not _ok(s.o[k], s.h[k], s.l[k], s.c[k]):
            return 0.0
        ha_o = 0.5 * (ha_o + ha_c)
        ha_c = 0.25 * (s.o[k] + s.h[k] + s.l[k] + s.c[k])
        prev_bull = ha_c > ha_o
    cur_ha_o = 0.5 * (ha_o + ha_c)
    cur_ha_c = 0.25 * (s.o[i] + s.h[i] + s.l[i] + s.c[i])
    no_lower_wick = abs(min(cur_ha_o, cur_ha_c) - min(s.l[i], cur_ha_o, cur_ha_c)) < 0.15 * max(s.h[i] - s.l[i], 1e-12)
    no_upper_wick = abs(max(s.h[i], cur_ha_o, cur_ha_c) - max(cur_ha_o, cur_ha_c)) < 0.15 * max(s.h[i] - s.l[i], 1e-12)
    if cur_ha_c > cur_ha_o and prev_bull and (no_lower_wick or cur_ha_c > ha_c):
        return 0.78
    if cur_ha_c < cur_ha_o and not prev_bull and (no_upper_wick or cur_ha_c < ha_c):
        return -0.78
    return 0.0


def hedging_grid(s):
    """Dynamic Hedging Grid (Range-Optimized)."""
    c, sma, atr, adx = s.c[s.i], s.sma20[s.i], s.atr14[s.i], s.adx[s.i]
    if not _ok(c, sma, atr, adx) or adx >= 20:
        return 0.0
    if c < sma - 1.2 * atr:
        return 0.7
    if c > sma + 1.2 * atr:
        return -0.7
    return 0.0


def camarilla_fader(s):
    """Camarilla Pivot Points Multi-Confluence (H3/H4/L3/L4 dari blok 60-bar sebelumnya)."""
    i = s.i
    if i < 62 or not _ok(s.c[i], s.h[i], s.l[i], s.o[i]):
        return 0.0
    prev_h = float(s.h[i - 61:i - 1].max())
    prev_l = float(s.l[i - 61:i - 1].min())
    prev_c = float(s.c[i - 2])
    rng = prev_h - prev_l
    if rng <= 0:
        return 0.0
    h3 = prev_c + rng * 1.1 / 4.0
    h4 = prev_c + rng * 1.1 / 2.0
    l3 = prev_c - rng * 1.1 / 4.0
    l4 = prev_c - rng * 1.1 / 2.0
    c, o, h, l = s.c[i], s.o[i], s.h[i], s.l[i]
    if l <= l3 and c > l3 and c > o and c > l4:
        return 0.75
    if h >= h3 and c < h3 and c < o and c < h4:
        return -0.75
    return 0.0


def orderflow_sweep(s):
    """Support/Resistance Order Flow Imbalance."""
    c, o, l, h, ll, hh, e9 = s.c[s.i], s.o[s.i], s.l[s.i], s.h[s.i], s.ll20[s.i - 1], s.hh20[s.i - 1], s.ema9[s.i]
    if not _ok(c, o, l, h, ll, hh, e9):
        return 0.0
    if l < ll and c > o and c > e9:
        return 0.8
    if h > hh and c < o and c < e9:
        return -0.8
    return 0.0


def carry_yield_momentum(s):
    """Synthetic Carry-Trade Yield Momentum."""
    c, e50, e200, rsi = s.c[s.i], s.ema50[s.i], s.ema200[s.i], s.rsi14[s.i]
    if not _ok(c, e50, e200, rsi):
        return 0.0
    if c > e200 and e50 > e200 and rsi > 52:
        return 0.75
    if c < e200 and e50 < e200 and rsi < 48:
        return -0.75
    return 0.0


def economic_straddle(s):
    """Economic Event Straddle & Volatility Rider."""
    h, l, c, o, atr = s.h[s.i], s.l[s.i], s.c[s.i], s.o[s.i], s.atr14[s.i]
    rng = h - l
    if not _ok(h, l, c, o, atr) or atr <= 0 or rng <= 0:
        return 0.0
    if rng > 1.8 * atr and c > o + 0.5 * rng:
        return 0.85
    if rng > 1.8 * atr and c < o - 0.5 * rng:
        return -0.85
    return 0.0


def smc_orderblock(s):
    """Institutional Order Block Mitigation (SMC)."""
    if s.i < 15:
        return 0.0
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    for k in range(s.i - 2, max(s.i - 12, 1), -1):
        if s.c[k] < s.o[k] and (s.c[k + 1] - s.c[k]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if float(s.l[k + 1:s.i].min()) < ob_low:
                continue
            if l <= ob_high and c >= ob_low and c > o:
                return 0.80
    for k in range(s.i - 2, max(s.i - 12, 1), -1):
        if s.c[k] > s.o[k] and (s.c[k] - s.c[k + 1]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if float(s.h[k + 1:s.i].max()) > ob_high:
                continue
            if h >= ob_low and c <= ob_high and c < o:
                return -0.80
    return 0.0


def ict_fair_value_gap(s):
    """ICT Fair Value Gap (FVG) Imbalance 3-Candle Mitigation."""
    i = s.i
    if i < 6:
        return 0.0
    c, o, h, l, atr = s.c[i], s.o[i], s.h[i], s.l[i], s.atr14[i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    for k in range(i - 1, max(i - 12, 2), -1):
        # Bullish 3-candle FVG: low[k] > high[k-2]
        gap_low, gap_high = s.h[k - 2], s.l[k]
        if gap_high - gap_low >= 0.2 * atr:
            # Pastikan gap belum terisi penuh sebelumnya
            filled = (k + 1 < i) and (float(s.l[k + 1:i].min()) <= gap_low)
            if not filled and l <= gap_high and c >= gap_low and c > o:
                return 0.80
        # Bearish 3-candle FVG: high[k] < low[k-2]
        bgap_low, bgap_high = s.h[k], s.l[k - 2]
        if bgap_high - bgap_low >= 0.2 * atr:
            filled = (k + 1 < i) and (float(s.h[k + 1:i].max()) >= bgap_high)
            if not filled and h >= bgap_low and c <= bgap_high and c < o:
                return -0.80
    return 0.0


def smc_liquidity_sweep(s):
    """SMC Liquidity Sweep & Market Structure Shift (MSS)."""
    c, o, h, l, hh, ll = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1]
    if not _ok(c, o, h, l, hh, ll):
        return 0.0
    rng = max(h - l, 1e-9)
    if l < ll and c > ll and (min(o, c) - l) / rng >= 0.45:
        return 0.85
    if h > hh and c < hh and (h - max(o, c)) / rng >= 0.45:
        return -0.85
    return 0.0


def ict_optimal_trade_entry(s):
    """ICT Optimal Trade Entry (OTE 62% - 79% Retracement)."""
    c, o, hh, ll, e21, e50 = s.c[s.i], s.o[s.i], s.hh20[s.i], s.ll20[s.i], s.ema21[s.i], s.ema50[s.i]
    if not _ok(c, o, hh, ll, e21, e50):
        return 0.0
    rng = hh - ll
    if rng <= 0:
        return 0.0
    if e21 > e50 and c > o:
        depth = (hh - c) / rng
        if 0.58 <= depth <= 0.80:
            return 0.78
    if e21 < e50 and c < o:
        depth = (c - ll) / rng
        if 0.58 <= depth <= 0.80:
            return -0.78
    return 0.0


def momentum_candle_burst(s):
    """Momentum Candle (Marubozu / Full-Body Range Expansion)."""
    c, o, h, l, atr, e9 = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i], s.ema9[s.i]
    if not _ok(c, o, h, l, atr, e9) or atr <= 0:
        return 0.0
    rng = h - l
    body = abs(c - o)
    if rng > 1.5 * atr and body >= 0.75 * rng:
        if c > o and c > e9:
            return 0.85
        if c < o and c < e9:
            return -0.85
    return 0.0


def xauusd_mc_fibo(s):
    """M15 Momentum Candle + M30/H1 alignment + Fibonacci [0.236..0.786] retest zones.

    Strict specs:
    - Forex mode: XAUUSD only. Spot/Futures: all pairs.
    - Completed M15/M30/H1 bars only (no mid-candle repainting).
    - Asia (00-07 UTC) & New York (12-21 UTC) sessions only.
    - Anchors: wick/body extreme for 1.0 (SL) & 0.0, TP = -0.27.
    - Fires ONLY when price genuinely retests inside [0.236, 0.786] without invalidation.
    """
    if s.i < 180 or not _ok(s.c[s.i], s.ts[s.i]):
        return 0.0

    symbol = getattr(s, "symbol", None)
    if getattr(s, "market_mode", "forex") == "forex" and symbol != "XAUUSD":
        return 0.0

    import numpy as np

    n = s.i + 1
    ts_a = s.ts[:n].astype(np.int64)
    o_a, h_a, l_a, c_a = s.o[:n], s.h[:n], s.l[:n], s.c[:n]

    # UTC session filter: Asia 00:00-06:59 UTC, New York 12:00-20:59 UTC
    hour = int((int(ts_a[-1]) // 3_600_000) % 24)
    if not (0 <= hour < 7 or 12 <= hour < 21):
        return 0.0

    def aggregate_closed(minutes: int):
        bucket = ts_a // (minutes * 60_000)
        cur_bucket = int(bucket[-1])
        cur_done = (((int(ts_a[-1]) // 60_000) + 1) % minutes) == 0
        min_bars = max(3, minutes // 3)
        groups = []
        for key in np.unique(bucket):
            k_int = int(key)
            if k_int == cur_bucket and not cur_done:
                continue
            ix = np.flatnonzero(bucket == key)
            if ix.size < min_bars:
                continue
            groups.append((
                k_int,
                int(ts_a[ix[-1]]),
                float(o_a[ix[0]]),
                float(h_a[ix].max()),
                float(l_a[ix].min()),
                float(c_a[ix[-1]]),
            ))
        return groups

    m15 = aggregate_closed(15)
    m30 = aggregate_closed(30)
    h1 = aggregate_closed(60)
    if len(m15) < 16 or len(m30) < 6 or len(h1) < 4:
        return 0.0

    def direction(bars):
        closes = np.array([x[5] for x in bars], dtype=float)
        fast = float(closes[-min(5, len(closes)):].mean())
        slow = float(closes[-min(20, len(closes)):].mean())
        if slow <= 0 or abs(fast - slow) / slow < 0.00008:
            return 0
        _, _, bo, bh, bl, bc = bars[-1]
        body_ratio = abs(bc - bo) / max(bh - bl, 1e-12)
        if body_ratio < 0.35:
            return 0
        if bc > bo and fast > slow:
            return 1
        if bc < bo and fast < slow:
            return -1
        return 0

    h1_dir, m30_dir = direction(h1), direction(m30)
    if not h1_dir or h1_dir != m30_dir:
        return 0.0

    px_now = float(c_a[-1])
    m1_m15_bucket = ts_a // (15 * 60_000)

    for idx_mc in range(len(m15) - 1, max(14, len(m15) - 4) - 1, -1):
        key_mc, _, o_mc, h_mc, l_mc, c_mc = m15[idx_mc]
        atr_ranges = np.array([x[3] - x[4] for x in m15[idx_mc - 14:idx_mc]], dtype=float)
        atr14 = float(atr_ranges.mean()) if atr_ranges.size else 0.0
        rng = h_mc - l_mc
        body = abs(c_mc - o_mc)
        if rng <= 0 or atr14 <= 0 or body / rng < 0.65 or rng < 1.5 * atr14:
            continue
        if (h1_dir > 0 and c_mc <= o_mc) or (h1_dir < 0 and c_mc >= o_mc):
            continue

        if h1_dir > 0:
            origin = l_mc if l_mc < o_mc else o_mc
            terminal = h_mc if h_mc > c_mc else c_mc
            delta = abs(terminal - origin)
            if delta <= 0:
                continue
            fibo_236 = terminal - 0.236 * delta
            fibo_786 = terminal - 0.786 * delta
            tp_neg_027 = terminal + 0.27 * delta
            after_ix = np.flatnonzero(m1_m15_bucket[:-1] > key_mc)
            if after_ix.size > 0:
                if float(l_a[after_ix].min()) <= origin or float(h_a[after_ix].max()) >= tp_neg_027:
                    continue
            if fibo_786 <= px_now <= fibo_236 and px_now > origin:
                s.custom_sl_tp = (origin, tp_neg_027)
                return 0.9
        else:
            origin = h_mc if h_mc > o_mc else o_mc
            terminal = l_mc if l_mc < c_mc else c_mc
            delta = abs(terminal - origin)
            if delta <= 0:
                continue
            fibo_236 = terminal + 0.236 * delta
            fibo_786 = terminal + 0.786 * delta
            tp_neg_027 = terminal - 0.27 * delta
            after_ix = np.flatnonzero(m1_m15_bucket[:-1] > key_mc)
            if after_ix.size > 0:
                if float(h_a[after_ix].max()) >= origin or float(l_a[after_ix].min()) <= tp_neg_027:
                    continue
            if fibo_236 <= px_now <= fibo_786 and px_now < origin:
                s.custom_sl_tp = (origin, tp_neg_027)
                return -0.9

    return 0.0


def three_line_strike(s):
    """Three Line Strike Price Action Reversal."""
    if s.i < 4:
        return 0.0
    c0, o0 = s.c[s.i], s.o[s.i]
    c1, o1 = s.c[s.i - 1], s.o[s.i - 1]
    c2, o2 = s.c[s.i - 2], s.o[s.i - 2]
    c3, o3 = s.c[s.i - 3], s.o[s.i - 3]
    atr = s.atr14[s.i]
    if not _ok(c0, o0, c1, o1, c2, o2, c3, o3, atr):
        return 0.0
    tol = max(0.0, 0.08 * atr)
    if c3 < o3 and c2 < o2 and c1 < o1 and c1 < c2 < c3:
        if c0 > o0 and c0 > o3 and o0 <= c1 + tol:
            return 0.85
    if c3 > o3 and c2 > o2 and c1 > o1 and c1 > c2 > c3:
        if c0 < o0 and c0 < o3 and o0 >= c1 - tol:
            return -0.85
    return 0.0


def pinbar_liquidity_reject(s):
    """Pin Bar Rejection of Dynamic S/R (EMA21/50)."""
    c, o, h, l, e21 = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.ema21[s.i]
    if not _ok(c, o, h, l, e21):
        return 0.0
    rng = max(h - l, 1e-9)
    body = abs(c - o)
    if (min(o, c) - l) / rng >= 0.60 and body / rng <= 0.32:
        if l < e21 and c >= e21 * 0.999:
            return 0.80
    if (h - max(o, c)) / rng >= 0.60 and body / rng <= 0.32:
        if h > e21 and c <= e21 * 1.001:
            return -0.80
    return 0.0


def london_ny_overlap(s):
    """London - New York Session Overlap Scalper (12:00 - 17:59 UTC)."""
    c, o, e9, e21, adx = s.c[s.i], s.o[s.i], s.ema9[s.i], s.ema21[s.i], s.adx[s.i]
    if not _ok(c, o, e9, e21, adx):
        return 0.0
    hr = int((s.ts[s.i] // 3600000) % 24)
    if 12 <= hr <= 17:
        if c > e9 > e21 and adx > 20 and c > o:
            return 0.75
        if c < e9 < e21 and adx > 20 and c < o:
            return -0.75
    return 0.0


def supply_demand_zone(s):
    """Institutional Supply & Demand Imbalance Retest (scan 2..10 bar terakhir)."""
    if s.i < 12:
        return 0.0
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    for k in range(s.i - 2, max(s.i - 10, 1), -1):
        base_h, base_l = s.h[k], s.l[k]
        if (base_h - base_l) >= 0.9 * atr:
            continue
        impulse = s.c[k + 1] - s.o[k + 1]
        # Demand Zone: base sempit + rally impulsif + belum jebol ke bawah base_l
        if impulse > 1.0 * atr:
            invalid = (k + 2 <= s.i - 1) and (float(s.l[k + 2:s.i].min()) < base_l)
            if not invalid and l <= base_h and c >= base_l and c > o:
                return 0.80
        # Supply Zone: base sempit + drop impulsif + belum jebol ke atas base_h
        if -impulse > 1.0 * atr:
            invalid = (k + 2 <= s.i - 1) and (float(s.h[k + 2:s.i].max()) > base_h)
            if not invalid and h >= base_l and c <= base_h and c < o:
                return -0.80
    return 0.0


def volume_spread_analysis(s):
    """Volume Spread Analysis (VSA): Wide spread + Volume Spike + Absorption Close."""
    i = s.i
    c, o, h, l, atr, v, v_sma = s.c[i], s.o[i], s.h[i], s.l[i], s.atr14[i], s.v[i], s.vol_sma20[i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    rng = h - l
    vol_ok = True if (not _ok(v_sma) or v_sma <= 0) else (v > 1.15 * v_sma)
    if rng > 1.5 * atr and vol_ok:
        if (c - l) / rng >= 0.55 and c > o:
            return 0.80
        if (h - c) / rng >= 0.55 and c < o:
            return -0.80
    return 0.0


STRATEGIES: list[tuple[str, str, str, Callable]] = [
    # id, nama, keluarga, fungsi sinyal
    ("ict_momentum", "ICT Momentum", "ICT", order_block),
    ("ict_fvg", "ICT Fair Value Gap", "ICT", fvg_ict),
    ("ict_obs", "ICT Order Block Sweep", "ICT", ict_orderblock_sweep),
    ("snr_bounce", "Support Resistance Bounce", "Price action", pivot_bounce),
    ("trend_stack", "EMA Stack 9/21/50", "Trend", trend_stack),
    ("donchian_55", "Donchian Turtle 55", "Breakout", donchian),
    ("donchian_20", "Donchian Breakout 20", "Breakout", lambda s: breakout(s, s.hh20, s.ll20)),
    ("keltner", "Keltner Channel Break", "Volatility", keltner),
    ("bb_rev", "Bollinger Fade", "Mean reversion", bollinger_reversion),
    ("squeeze", "Squeeze Release", "Volatility", squeeze),
    ("rsi_30_70", "RSI Mean Reversion", "Mean reversion", rsi_regime),
    ("stoch_cross", "Stochastic 20/80", "Oscillator", willr),
    ("macd_cross", "MACD Trend", "Momentum", macd_cross),
    ("macd_div", "MACD Divergence", "Momentum", macd_divergence),
    ("ema_macd_fast", "EMA21/50 Golden", "Trend", lambda s: ema_cross(s, s.ema21, s.ema50)),
    ("golden_50_200", "Golden Cross 50/200", "Trend", lambda s: ema_cross(s, s.sma50, s.sma200)),
    ("ichimoku", "Ichimoku Kumo", "Trend", ichimoku),
    ("supertrend", "SuperTrend ATR", "Volatility", supertrend),
    ("chandelier", "Chandelier Exit", "Trailing", chandelier_exit),
    ("fib_retrace", "Fib Retracement 38-62", "Fibonacci", fib_retrace),
    ("fib_ext", "Fib Extension Trend", "Fibonacci", lambda s: trend_stack(s) if 0.25 <= ((s.c[s.i] - float(s.l[s.i - 49:s.i + 1].min())) / max(float(s.h[s.i - 49:s.i + 1].max()) - float(s.l[s.i - 49:s.i + 1].min()), 1e-9)) <= 0.5 else 0.0),
    ("fib_golden_pocket", "Fib Golden Pocket 61.8", "Fibonacci", fib_golden_pocket),
    ("fib_expansion_1618", "Fib Extension 1.618", "Fibonacci", fib_expansion_1618),
    ("vwap_band", "VWAP Deviation", "Statistik", vwap_band),
    ("vwap_trend", "VWAP Trend Follow", "Statistik", vwap_trend_follow),
    ("vol_breakout", "Volume Breakout", "Breakout", volume_breakout),
    ("vol_target", "Volatility Trend Filter", "Trend", volatility_target),
    ("adx_trend", "ADX Strong Trend", "Trend", adx_trend),
    ("roc_momentum", "ROC Momentum 12", "Momentum", roc_momentum),
    ("hot_momentum", "Impulse Candle", "Momentum", hot_momentum),
    ("momentum_60", "Multi-Horizon Momentum", "Momentum", momentum_weeks),
    ("zscore_rev", "Z-Score Reversion", "Statistik", zscore_reversion),
    ("mean_sd_band", "Mean Deviation Band", "Statistik", mean_sd_band_mad),
    ("time_session", "Timezone Session Bias", "Waktu", time_filter),
    ("time_open", "Opening Hour Range", "Waktu", opening_range_breakout),
    ("gap_fill", "Gap Fill Reversal", "Price action", gap_fill),
    ("2b_rev", "2B Close Reversal", "Price action", two_b_close_reversal),
    ("engulfing", "Bullish/Bearish Engulfing", "Price action", engulfing_pattern),
    ("inside_bar", "Inside Bar Breakout", "Price action", inner_bar),
    ("swing_break", "Swing Volume Break", "Price action", swing_break),
    ("vol_trend_sma", "SMA50/200 Regime", "Trend", vol_trend_sma),
    ("ewma_trend", "EMA200 Trend Bias", "Trend", ewma_trend),
    ("price_ema_dev", "EMA Deviation", "Statistik", lambda s: mean_ema(s, s.ema9, s.ema21)),
    ("price_ema_dev2", "EMA50 Deviation", "Statistik", lambda s: mean_ema(s, s.ema21, s.ema50)),
    ("rotation", "RSI+MACD Rotation", "Momentum", rotation),
    ("value_area", "Value Area Auction", "Volume profile", value_area_profile),
    ("tr_break", "Range Expansion Fade", "Volatility", tr_break),
    ("trend_pullback", "Trend Pullback EMA9", "Trend", lambda s: 0.6 if (s.c[s.i] > s.ema50[s.i] and s.c[s.i] < s.ema9[s.i] and s.rsi14[s.i] < 50) else (-0.6 if (_ok(s.ema50[s.i]) and s.c[s.i] < s.ema50[s.i] and s.c[s.i] > s.ema9[s.i] and s.rsi14[s.i] > 50) else 0.0)),
    ("mean_ma_cross", "MA Cross Mean", "Trend", lambda s: 0.5 if (_ok(s.sma20[s.i], s.sma50[s.i]) and s.sma20[s.i] > s.sma50[s.i] and s.c[s.i] > s.sma20[s.i]) else (-0.5 if (_ok(s.sma20[s.i], s.sma50[s.i]) and s.sma20[s.i] < s.sma50[s.i] and s.c[s.i] < s.sma20[s.i]) else 0.0)),
    ("rsi2_extreme", "RSI2 Extreme", "Mean reversion", lambda s: 0.7 if s.rsi2[s.i] < 10 else (-0.7 if s.rsi2[s.i] > 90 else 0.0)),
    ("turtle_soup", "Turtle Soup Sweep", "Struktur", lambda s: 0.65 if (s.l[s.i] < s.ll20[s.i - 1] and s.c[s.i] > s.ll20[s.i - 1]) else (-0.65 if (s.h[s.i] > s.hh20[s.i - 1] and s.c[s.i] < s.hh20[s.i - 1]) else 0.0)),
    ("delta_flow", "Candle Imbalance", "Order flow", candle_imbalance),
    ("wicks_reject", "Wick Rejection", "Order flow", wick_rejection),
    ("paint_bar", "Paint Bar Pattern", "Price action", paint_bar),
    ("price_action_2b", "2B Reversal", "Price action", price_action_2b),
    ("fractal_break", "Fractal Breakout", "Breakout", fractal_break),
    # ── 33 Extended Universal Quantitative Models ──
    ("lob_alpha", "London Open Breakout", "Breakout", lob_alpha),
    ("tokyo_fader", "Asian Range Fader", "Mean reversion", tokyo_fader),
    ("frankfurt_probe", "Frankfurt Liquidity Probe", "Order flow", frankfurt_probe),
    ("ny_reversal", "New York Fixing Reversal", "Mean reversion", ny_reversal),
    ("sunday_gap", "Sunday Gap Fill Engine", "Statistik", sunday_gap),
    ("aud_nzd_arb", "Aussie-Kiwi Cointegration", "Statistik", aud_nzd_arb),
    ("triangular_synth", "Triangular Arbitrage Synth", "Statistik", triangular_synth),
    ("oil_cad_divergence", "Petro-CAD Divergence", "Trend", oil_cad_divergence),
    ("gold_safehaven_relay", "Safe-Haven Gold Relay", "Trend", gold_safehaven_relay),
    ("dragon_momentum", "The Dragon Momentum Rider", "Momentum", dragon_momentum),
    ("bb_squeeze", "BB Squeeze Volatility", "Volatility", bb_squeeze),
    ("atr_expansion", "ATR Expansion Breakout", "Breakout", atr_expansion),
    ("gold_flash_spike", "Gold Flash-Spike Reversal", "Oscillator", gold_flash_spike),
    ("ema_ribbon", "Multi-TF EMA Ribbon", "Trend", ema_ribbon),
    ("supertrend_trailing", "SuperTrend Dynamic Trailing", "Trailing", supertrend_trailing),
    ("ichimoku_quantum", "Ichimoku Kumo Quantum", "Trend", ichimoku_quantum),
    ("heikin_ashi_smooth", "Heikin-Ashi Trend Continuum", "Trend", heikin_ashi_smooth),
    ("hedging_grid", "Dynamic Hedging Grid", "Struktur", hedging_grid),
    ("camarilla_fader", "Camarilla Multi-Confluence", "Struktur", camarilla_fader),
    ("orderflow_sweep", "Order Flow Liquidity Sweep", "Order flow", orderflow_sweep),
    ("carry_yield_momentum", "Synthetic Carry-Trade Yield", "Trend", carry_yield_momentum),
    ("economic_straddle", "Economic Straddle Breakout", "Breakout", economic_straddle),
    ("smc_orderblock", "SMC Order Block Mitigation", "ICT", smc_orderblock),
    ("ict_fair_value_gap", "ICT Fair Value Gap (FVG)", "ICT", ict_fair_value_gap),
    ("smc_liquidity_sweep", "SMC Liquidity Sweep & BOS", "Struktur", smc_liquidity_sweep),
    ("ict_optimal_trade_entry", "ICT Optimal Trade Entry", "ICT", ict_optimal_trade_entry),
    ("momentum_candle_burst", "Momentum Candle Expansion", "Momentum", momentum_candle_burst),
    ("xauusd_mc_fibo", "XAUUSD MC-FIBO Retest", "Fibonacci", xauusd_mc_fibo),
    ("three_line_strike", "Three Line Strike Pattern", "Price action", three_line_strike),
    ("pinbar_liquidity_reject", "Pin Bar Liquidity Rejection", "Price action", pinbar_liquidity_reject),
    ("london_ny_overlap", "London-NY Overlap Scalper", "Breakout", london_ny_overlap),
    ("supply_demand_zone", "Supply & Demand Zone", "Struktur", supply_demand_zone),
    ("volume_spread_analysis", "Volume Spread Analysis (VSA)", "Order flow", volume_spread_analysis),
]

DEFAULT_SL = {"atr": 2.0}
THRESHOLD = 0.15

assert len(STRATEGIES) == len({s[0] for s in STRATEGIES}), "id strategi duplikat"
assert len(STRATEGIES) >= 50, f"butuh minimal 50 strategi, ada {len(STRATEGIES)}"

STRATEGY_IDS = [s[0] for s in STRATEGIES]
STRATEGY_META = {s[0]: {"name": s[1], "family": s[2]} for s in STRATEGIES}
SIGNAL_FN = {s[0]: s[3] for s in STRATEGIES}

# Leverage default per strategi (futures mode). Range 5-20x (institusional / quant prop standards).
# Scalp / Extreme / Mean reversion: 15-20x · Breakout / Momentum: 10-15x · Trend / Swing: 5-10x.
_leverage_map = {
    # Trend — 5-10x
    "trend_stack": 10, "golden_50_200": 5, "ema_macd_fast": 8, "ichimoku": 8,
    "vol_trend_sma": 6, "ewma_trend": 8, "adx_trend": 10, "trend_pullback": 10,
    "mean_ma_cross": 8,
    # Breakout & Volatility — 10-15x
    "donchian_55": 10, "donchian_20": 10, "keltner": 12, "squeeze": 15,
    "vol_breakout": 12, "swing_break": 10, "fractal_break": 12,
    "supertrend": 10, "chandelier": 10, "tr_break": 15, "vol_target": 8,
    # Momentum — 10-15x
    "macd_cross": 10, "macd_div": 12, "roc_momentum": 15, "hot_momentum": 15,
    "momentum_60": 12, "rotation": 12,
    # Mean reversion — scalp & reversion (hingga 20x)
    "bb_rev": 15, "rsi_30_70": 15, "stoch_cross": 15, "zscore_rev": 20,
    "mean_sd_band": 15, "rsi2_extreme": 20, "gap_fill": 15,
    # ICT / Structure — 10-15x
    "ict_momentum": 15, "ict_fvg": 12, "ict_obs": 15, "snr_bounce": 10,
    "turtle_soup": 15, "fib_retrace": 8, "fib_ext": 8, "fib_golden_pocket": 10, "fib_expansion_1618": 12,
    # Price action & Order flow (hingga 20x)
    "price_action_2b": 15, "engulfing": 15, "inside_bar": 15, "paint_bar": 15,
    "wicks_reject": 15, "delta_flow": 20,
    # Statistical & Time (10-15x)
    "vwap_band": 12, "vwap_trend": 10, "price_ema_dev": 12, "price_ema_dev2": 15,
    "value_area": 10, "time_session": 10, "time_open": 12,
    # Extended Universal Quant Suite (5-20x dalam mode Futures)
    "lob_alpha": 12, "tokyo_fader": 15, "frankfurt_probe": 15, "ny_reversal": 15,
    "sunday_gap": 15, "aud_nzd_arb": 15, "triangular_synth": 15, "oil_cad_divergence": 8,
    "gold_safehaven_relay": 8, "dragon_momentum": 15, "bb_squeeze": 15, "atr_expansion": 12,
    "gold_flash_spike": 15, "ema_ribbon": 8, "supertrend_trailing": 10, "ichimoku_quantum": 8,
    "heikin_ashi_smooth": 8, "hedging_grid": 10, "camarilla_fader": 12, "orderflow_sweep": 15,
    "carry_yield_momentum": 6, "economic_straddle": 15,
    "smc_orderblock": 15, "ict_fair_value_gap": 12, "smc_liquidity_sweep": 15,
    "ict_optimal_trade_entry": 12, "momentum_candle_burst": 15, "xauusd_mc_fibo": 10, "three_line_strike": 15,
    "pinbar_liquidity_reject": 15, "london_ny_overlap": 12, "supply_demand_zone": 12,
    "volume_spread_analysis": 15,
}
DEFAULT_LEVERAGE.update(_leverage_map)
# Fallback: strategi tanpa mapping dapat 10x
for sid in STRATEGY_IDS:
    if sid not in DEFAULT_LEVERAGE:
        DEFAULT_LEVERAGE[sid] = 10


def get_strategy_rr(sid: str) -> float:
    """Return Risk-to-Reward (R:R) ratio untuk perhitungan Take Profit (TP).
    Mean reversion: 1.5R (keluar cepat saat harga kembali ke rata-rata).
    Trend & Breakout: 2.2R (biarkan pemenang berlari mengikuti tren).
    Momentum & Order flow: 2.0R.
    Lainnya: 1.8R."""
    fam = STRATEGY_META.get(sid, {}).get("family", "")
    if fam in ("Trend", "Breakout"):
        return 2.2
    if fam in ("Momentum", "Order flow"):
        return 2.0
    if fam in ("Mean reversion", "Statistik", "Oscillator"):
        return 1.5
    return 1.8

# ── Universal Multi-Market Strategy Suite (89 Models) ────────────────
# Semua 89 model kuantitatif bersifat UNIVERSAL: dapat beroperasi di Spot, Futures, maupun Forex.
# - Spot: 89 strategi (Long-only, 1x equity, fee 0.05%).
# - Futures: 89 strategi (Long + Short, configurable leverage 5-20x, funding rate).
# - Forex: 89 strategi (Long + Short, MT5 Direct lot sizing, spread broker riil, no funding fee).

UNIVERSAL_STRATEGIES = list(STRATEGY_IDS)

SPOT_STRATEGIES = list(UNIVERSAL_STRATEGIES)
FUTURES_STRATEGIES = list(UNIVERSAL_STRATEGIES)
FOREX_STRATEGIES = list(UNIVERSAL_STRATEGIES)

# Validate all IDs exist
_all_ids = set(STRATEGY_IDS)
for sid in SPOT_STRATEGIES:
    assert sid in _all_ids, f"Spot strategy {sid} not in STRATEGIES"
for sid in FUTURES_STRATEGIES:
    assert sid in _all_ids, f"Futures strategy {sid} not in STRATEGIES"
for sid in FOREX_STRATEGIES:
    assert sid in _all_ids, f"Forex strategy {sid} not in STRATEGIES"

# ── Forex pair selection (28 Pairs sesuai watchlist broker) ─────────
FOREX_PAIRS = [
    "XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDCAD", "AUDJPY",
    "AUDUSD", "EURGBP", "EURAUD", "EURJPY", "EURNZD", "GBPJPY", "GBPAUD",
    "GBPCAD", "GBPNZD", "NZDUSD", "NZDCAD", "XTIUSD", "USDCHF", "EURCHF",
    "GBPCHF", "CADJPY", "CHFJPY", "NZDJPY", "AUDNZD", "CADCHF", "AUDCHF",
]

# ── Futures pair selection ────────────────────────────────────────────
# Futures API (fapi.binance.com) sering diblokir oleh ISP.
# Solusi: ambil dari spot pairs, filter yang umum ada di futures market.
# Pair futures cenderung lebih liquid dan terkonsentrasi di top volume.
# Daftar ini di-filter otomatis saat runtime berdasarkan:
#   1. Top N spot pairs by volume
#   2. Exclude stablecoins, tokenized stocks, BRL/TRY/etc pairs
#   3. Hanya pair yang base asset-nya dikenal di futures market
# Fungsi filter ada di binance.py:get_futures_pairs()

# Known futures base assets (updated periodically from Binance USDT-M futures)
# Ini hanya fallback filter — pair tetap diambil otomatis dari volume ranking
KNOWN_FUTURES_BASES = {
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "TRX", "LINK",
    "DOT", "MATIC", "LTC", "UNI", "ATOM", "ETC", "FIL", "APT", "NEAR", "OP",
    "ARB", "SUI", "TIA", "SEI", "INJ", "FTM", "ALGO", "SAND", "MANA", "AXS",
    "GALA", "APE", "DYDX", "GMX", "LDO", "MKR", "AAVE", "COMP", "SNX", "CRV",
    "RUNE", "FET", "RENDER", "IMX", "STX", "THETA", "GRT", "ENS", "PENDLE",
    "WLD", "PEPE", "SHIB", "WIF", "BONK", "FLOKI", "TON", "NOT", "TRUMP",
    "HYPE", "PENGU", "KAITO", "IP", "LAYER", "FORM", "BIO", "SIGN", "PARTI",
    "ZRO", "EIGEN", "SCR", "HMSTR", "CATI", "NEIRO", "TURBO", "POPCAT", "MEW",
    "BOME", "W", "PYTH", "JUP", "STRK", "PIXEL", "PORTAL", "AEVO", "ENA",
    "DRIFT", "ONDO", "ALT", "AI16Z", "VIRTUAL", "PNUT", "ACT", "HIPSTR",
    "MORPHO", "USUAL", "MOVE", "ME", "PENGU", "VANA", "BIO", "TRUMP", "MELANIA",
    "ANIME", "TST", "KOMA", "LPT", "QNT", "ICP", "VET", "HBAR", "EGLD", "FLOW",
    "MINA", "KAS", "CFX", "ZIL", "CELO", "ONE", "ROSE", "ZEC", "DASH", "XMR",
    "EOS", "IOTA", "NEO", "QTUM", "ZRX", "BAT", "MANA", "ENJ", "CHZ", "HOT",
    "ANKR", "SKL", "CTSI", "OGN", "BAKE", "REEF", "CELR", "DENT", "WIN",
}
