"""50 strategy untuk Spot dan Futures.

Kontrak sinyal per strategy (dipanggil satu kali per bar tertutup per symbol):

    score(s) -> float in [-1, 1]

  > +0.15  long   ·   < -0.15  short   ·   selain itu diam.

Spot mode: hanya LONG yang dieksekusi, fee 0.05% per sisi.
Futures mode: LONG + SHORT, leverage configurable per strategi, funding rate 8 jam,
              fee maker 0.02% / taker 0.05%.
"""

from __future__ import annotations

from typing import Callable

MAX_POS = 5            # batas concurrent positions per strategi (bisa pegang hingga 5 pair berbeda)
SINGLE_POS_CAP = 0.20  # alokasi maks 20% equity ($2.000 dari $10.000) per posisi
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
    """SuperTrend 10 x 3 ATR sederhana (arah dari posisi close vs ATR band)."""
    i = s.i
    atr = s.atr14[i]
    hl2 = (s.h[i] + s.l[i]) / 2
    if not _ok(atr):
        return 0.0
    up_line = hl2 - 3 * atr
    dn_line = hl2 + 3 * atr
    c0, c1 = s.c[i - 1], s.c[i]
    if c0 <= up_line:
        return 0.0
    if c1 > up_line and c0 <= up_line:
        return 0.7
    if c1 < dn_line and c0 >= dn_line:
        return -0.7
    # sinyal lanjutan: harga jauh di luar band bertahan = momentum
    if c1 > up_line and c1 < s.ema21[i]:
        return 0.3
    if c1 < dn_line and c1 > s.ema21[i]:
        return -0.3
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


def pivot_bounce(s):
    i = s.i
    piv = (s.h[i - 1] + s.l[i - 1] + s.c[i - 1]) / 3
    r1 = 2 * piv - s.l[i - 1]
    s1 = 2 * piv - s.h[i - 1]
    c = s.c[i]
    if c < s1 and s.c[i - 1] >= s1:
        return 0.6
    if c > r1 and s.c[i - 1] <= r1:
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
    if not (0.0015 <= vol <= 0.012):
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
    i = s.i
    if i < 25:
        return 0.0
    px_low_prev = float(s.l[i - 25:i - 5].min())
    px_low_now = float(s.l[i - 20:i + 1].min())
    macd_low_prev = float(s.macd[i - 25:i - 5].min())
    macd_low_now = float(s.macd[i - 20:i + 1].min())
    px_hi_prev = float(s.h[i - 25:i - 5].max())
    px_hi_now = float(s.h[i - 20:i + 1].max())
    macd_hi_prev = float(s.macd[i - 25:i - 5].max())
    macd_hi_now = float(s.macd[i - 20:i + 1].max())
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
    return -1 if s.c[i] < s.o[i] else 1


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
    i = s.i
    if i < 3:
        return 0.0
    # Engulfing sederhana
    o1, c1, o2, c2 = s.o[i - 1], s.c[i - 1], s.o[i], s.c[i]
    if c1 < o1 and c2 > o2 and c2 > o1 and o2 < c1:
        return 0.6
    if c1 > o1 and c2 < o2 and c2 < o1 and o2 > c1:
        return -0.6
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


STRATEGIES: list[tuple[str, str, str, Callable]] = [
    # id, nama, keluarga, fungsi sinyal
    ("ict_momentum", "ICT Momentum", "ICT", order_block),
    ("ict_fvg", "ICT Fair Value Gap", "ICT", fvg_ict),
    ("ict_obs", "ICT Order Block Sweep", "ICT", fractal_break),
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
    ("fib_retrace", "Fib Retracement 38-62", "Fibonaci", fib_retrace),
    ("fib_ext", "Fib Extension Trend", "Fibonaci", lambda s: trend_stack(s) if 0.25 <= ((s.c[s.i] - float(s.l[s.i - 49:s.i + 1].min())) / max(float(s.h[s.i - 49:s.i + 1].max()) - float(s.l[s.i - 49:s.i + 1].min()), 1e-9)) <= 0.5 else 0.0),
    ("vwap_band", "VWAP Deviation", "Statistik", vwap_band),
    ("vwap_trend", "VWAP Trend Follow", "Statistik", lambda s: trend_stack(s) if s.c[s.i] > s.ema50[s.i] else -trend_stack(s) if _ok(s.ema50[s.i]) else 0.0),
    ("vol_breakout", "Volume Breakout", "Breakout", volume_breakout),
    ("vol_target", "Volatility Trend Filter", "Trend", volatility_target),
    ("adx_trend", "ADX Strong Trend", "Trend", adx_trend),
    ("roc_momentum", "ROC Momentum 12", "Momentum", roc_momentum),
    ("hot_momentum", "Impulse Candle", "Momentum", hot_momentum),
    ("momentum_60", "Multi-Horizon Momentum", "Momentum", momentum_weeks),
    ("zscore_rev", "Z-Score Reversion", "Statistik", zscore_reversion),
    ("mean_sd_band", "Mean Deviation Band", "Statistik", lambda s: -zscore_reversion(s) * 0.7),
    ("time_session", "Timezone Session Bias", "Waktu", time_filter),
    ("time_open", "Opening Hour Range", "Waktu", lambda s: trend_stack(s) if int((s.ts[s.i] // 3600000) % 24) in (0, 1, 2, 3) else 0.0),
    ("gap_fill", "Gap Fill Reversal", "Price action", gap_fill),
    ("2b_rev", "2B Reversal", "Price action", price_action_2b),
    ("engulfing", "Bullish/Bearish Engulfing", "Price action", paint_bar),
    ("inside_bar", "Inside Bar Breakout", "Price action", inner_bar),
    ("swing_break", "Swing Volume Break", "Price action", swing_break),
    ("vol_trend_sma", "SMA50/200 Regime", "Trend", vol_trend_sma),
    ("ewma_trend", "EMA200 Trend Bias", "Trend", ewma_trend),
    ("price_ema_dev", "EMA Deviation", "Statistik", lambda s: mean_ema(s, s.ema9, s.ema21)),
    ("price_ema_dev2", "EMA50 Deviation", "Statistik", lambda s: mean_ema(s, s.ema21, s.ema50)),
    ("rotation", "RSI+MACD Rotation", "Momentum", rotation),
    ("value_area", "Value Area Auction", "Volume profile", lambda s: vwap_band(s)),
    ("tr_break", "Range Expansion Fade", "Volatility", tr_break),
    ("trend_pullback", "Trend Pullback EMA9", "Trend", lambda s: 0.6 if (s.c[s.i] > s.ema50[s.i] and s.c[s.i] < s.ema9[s.i] and s.rsi14[s.i] < 50) else (-0.6 if (_ok(s.ema50[s.i]) and s.c[s.i] < s.ema50[s.i] and s.c[s.i] > s.ema9[s.i] and s.rsi14[s.i] > 50) else 0.0)),
    ("mean_ma_cross", "MA Cross Mean", "Trend", lambda s: 0.5 if (_ok(s.sma20[s.i], s.sma50[s.i]) and s.sma20[s.i] > s.sma50[s.i] and s.c[s.i] > s.sma20[s.i]) else (-0.5 if (_ok(s.sma20[s.i], s.sma50[s.i]) and s.sma20[s.i] < s.sma50[s.i] and s.c[s.i] < s.sma20[s.i]) else 0.0)),
    ("rsi2_extreme", "RSI2 Extreme", "Mean reversion", lambda s: 0.7 if s.rsi2[s.i] < 10 else (-0.7 if s.rsi2[s.i] > 90 else 0.0)),
    ("turtle_soup", "Turtle Soup Sweep", "Struktur", lambda s: 0.65 if (s.l[s.i] < s.ll20[s.i - 1] and s.c[s.i] > s.ll20[s.i - 1]) else (-0.65 if (s.h[s.i] > s.hh20[s.i - 1] and s.c[s.i] < s.hh20[s.i - 1]) else 0.0)),
    ("delta_flow", "Candle Imbalance", "Order flow", lambda s: (0.35 if (s.c[s.i] - s.l[s.i]) > 0.65 * max(s.h[s.i] - s.l[s.i], 1e-12) else (-0.35 if (s.h[s.i] - s.c[s.i]) > 0.65 * max(s.h[s.i] - s.l[s.i], 1e-12) else 0.0)) * (1 if s.c[s.i] > s.ema21[s.i] else -1)),
    ("wicks_reject", "Wick Rejection", "Order flow", lambda s: (0.6 if (s.h[s.i] - s.c[s.i]) > 1.8 * abs(s.c[s.i] - s.o[s.i] + 1e-12) and s.h[s.i] > s.ema21[s.i] else (-0.6 if (s.c[s.i] - s.l[s.i]) > 1.8 * abs(s.c[s.i] - s.o[s.i] + 1e-12) and s.l[s.i] < s.ema21[s.i] else 0.0))),
    ("paint_bar", "Paint Bar Pattern", "Price action", paint_bar),
    ("price_action_2b", "2B Reversal", "Price action", price_action_2b),
    ("fractal_break", "Fractal Breakout", "Breakout", fractal_break),
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
    "turtle_soup": 15, "fib_retrace": 8, "fib_ext": 8,
    # Price action & Order flow (hingga 20x)
    "price_action_2b": 15, "engulfing": 15, "inside_bar": 15, "paint_bar": 15,
    "wicks_reject": 15, "delta_flow": 20,
    # Statistical & Time (10-15x)
    "vwap_band": 12, "vwap_trend": 10, "price_ema_dev": 12, "price_ema_dev2": 15,
    "value_area": 10, "time_session": 10, "time_open": 12,
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

# ── Spot vs Futures strategy assignment ──────────────────────────────
# Spot: strategi yang cocok untuk long-only, akumulasi, swing.
# Futures: semua strategi termasuk yang butuh short + leverage awareness.
# Beberapa strategi eksklusif per mode.

SPOT_STRATEGIES = [
    # Trend following — ideal untuk spot hold
    "trend_stack", "golden_50_200", "ema_macd_fast", "ichimoku",
    "vol_trend_sma", "ewma_trend", "adx_trend", "trend_pullback", "mean_ma_cross",
    # Breakout — spot accumulation pada breakout
    "donchian_55", "donchian_20", "keltner", "squeeze", "vol_breakout", "swing_break",
    # Momentum — ride the wave
    "macd_cross", "roc_momentum", "momentum_60", "hot_momentum",
    # Mean reversion — buy the dip
    "bb_rev", "rsi_30_70", "zscore_rev", "mean_sd_band", "rsi2_extreme",
    # Fib / Structure — spot entry points
    "fib_retrace", "fib_ext", "snr_bounce", "turtle_soup",
    # Price action — spot-friendly patterns
    "engulfing", "inside_bar", "paint_bar", "price_action_2b",
    # Statistical / VWAP
    "vwap_band", "vwap_trend", "price_ema_dev", "price_ema_dev2", "value_area",
    # Time-based
    "time_session", "time_open",
]

FUTURES_STRATEGIES = [
    # Semua spot strategies juga valid di futures (dengan leverage)
    *SPOT_STRATEGIES,
    # Plus futures-exclusive strategies:
    # Short-biased / mean reversion agresif
    "stoch_cross", "gap_fill", "rotation",
    # Volatility / scalping — butuh leverage
    "supertrend", "chandelier", "tr_break", "vol_target",
    # ICT / Order flow — institutional style
    "ict_momentum", "ict_fvg", "ict_obs",
    # Fractal / microstructure
    "fractal_break", "wicks_reject", "delta_flow",
    # MACD divergence — better with leverage
    "macd_div",
]

# Deduplicate while preserving order
FUTURES_STRATEGIES = list(dict.fromkeys(FUTURES_STRATEGIES))

# Validate all IDs exist
_all_ids = set(STRATEGY_IDS)
for sid in SPOT_STRATEGIES:
    assert sid in _all_ids, f"Spot strategy {sid} not in STRATEGIES"
for sid in FUTURES_STRATEGIES:
    assert sid in _all_ids, f"Futures strategy {sid} not in STRATEGIES"

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
