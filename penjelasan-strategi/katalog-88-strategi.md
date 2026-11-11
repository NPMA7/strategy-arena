# Katalog & Bedah Logika 88 Strategi Trading - Strategy Arena

Dokumen ini memuat dokumentasi teknis, logika matematis, formula entry/exit, serta **analisis audit potensi kelemahan/kesalahan logika (Bug & Risk Audit)** dari seluruh 88 strategi kuantitatif yang aktif di Strategy Arena (Forex MT5, Binance Futures, & Binance Spot).

Dokumen ini disusun untuk memudahkan review menyeluruh, audit logika oleh trader/developer, serta sebagai bahan referensi komprehensif bagi agent AI (Claude Opus 3.5, GPT, Astra) untuk optimalisasi lebih lanjut.

---

## 1. Master Tabel 88 Strategi

| No | ID Strategi | Nama Strategi | Kategori | Default Lev | R:R Target | Logika Inti |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `ict_momentum` | **ICT Momentum** | ICT | 15x | 1:1.8 | Order block: candle impulsif jauh di luar ATR, lalu harga kembali ke 50%-nya. |
| 2 | `ict_fvg` | **ICT Fair Value Gap** | ICT | 12x | 1:1.8 | Fair Value Gap: gap antara high bar-2 dan low bar-0 lalu diisi (retest). |
| 3 | `ict_obs` | **ICT Order Block Sweep** | ICT | 15x | 1:1.8 | Algoritma teknikal rule-based |
| 4 | `snr_bounce` | **Support Resistance Bounce** | Price action | 10x | 1:1.8 | Algoritma teknikal rule-based |
| 5 | `trend_stack` | **EMA Stack 9/21/50** | Trend | 10x | 1:2.2 | Algoritma teknikal rule-based |
| 6 | `donchian_55` | **Donchian Turtle 55** | Breakout | 10x | 1:2.2 | Algoritma teknikal rule-based |
| 7 | `donchian_20` | **Donchian Breakout 20** | Breakout | 10x | 1:2.2 | Algoritma teknikal rule-based |
| 8 | `keltner` | **Keltner Channel Break** | Volatility | 12x | 1:1.8 | Algoritma teknikal rule-based |
| 9 | `bb_rev` | **Bollinger Fade** | Mean reversion | 15x | 1:1.5 | Algoritma teknikal rule-based |
| 10 | `squeeze` | **Squeeze Release** | Volatility | 15x | 1:1.8 | Algoritma teknikal rule-based |
| 11 | `rsi_30_70` | **RSI Mean Reversion** | Mean reversion | 15x | 1:1.5 | Algoritma teknikal rule-based |
| 12 | `stoch_cross` | **Stochastic 20/80** | Oscillator | 15x | 1:1.5 | Stochastic %K cross 20/80. |
| 13 | `macd_cross` | **MACD Trend** | Momentum | 10x | 1:2.0 | Algoritma teknikal rule-based |
| 14 | `macd_div` | **MACD Divergence** | Momentum | 12x | 1:2.0 | Algoritma teknikal rule-based |
| 15 | `ema_macd_fast` | **EMA21/50 Golden** | Trend | 8x | 1:2.2 | Algoritma teknikal rule-based |
| 16 | `golden_50_200` | **Golden Cross 50/200** | Trend | 5x | 1:2.2 | Algoritma teknikal rule-based |
| 17 | `ichimoku` | **Ichimoku Kumo** | Trend | 8x | 1:2.2 | Algoritma teknikal rule-based |
| 18 | `supertrend` | **SuperTrend ATR** | Volatility | 10x | 1:1.8 | SuperTrend 10 x 3 ATR sederhana (arah dari posisi close vs ATR band). |
| 19 | `chandelier` | **Chandelier Exit** | Trailing | 10x | 1:1.8 | Algoritma teknikal rule-based |
| 20 | `fib_retrace` | **Fib Retracement 38-62** | Fibonacci | 8x | 1:1.8 | Retrace ke 38.2–61.8% dari swing 50 bar, searah tren EMA50. |
| 21 | `fib_ext` | **Fib Extension Trend** | Fibonacci | 8x | 1:1.8 | Algoritma teknikal rule-based |
| 22 | `fib_golden_pocket` | **Fib Golden Pocket 61.8** | Fibonacci | 10x | 1:1.8 | Entry di Golden Pocket (61.8% - 65% retracement) dari swing 60 bar dengan konfirmasi candlestick & EMA50. |
| 23 | `fib_expansion_1618` | **Fib Extension 1.618** | Fibonacci | 12x | 1:1.8 | Breakout ekspansi Fibonacci 1.272–1.618 ekstensi dengan dorongan momentum. |
| 24 | `vwap_band` | **VWAP Deviation** | Statistik | 12x | 1:1.5 | VWAP jendela 60 candle, mean reversion ke band. |
| 25 | `vwap_trend` | **VWAP Trend Follow** | Statistik | 10x | 1:1.5 | Algoritma teknikal rule-based |
| 26 | `vol_breakout` | **Volume Breakout** | Breakout | 12x | 1:2.2 | Algoritma teknikal rule-based |
| 27 | `vol_target` | **Volatility Trend Filter** | Trend | 8x | 1:2.2 | Trading saat volatilitas normal: follow tren hanya kalau ATR/close sehat. |
| 28 | `adx_trend` | **ADX Strong Trend** | Trend | 10x | 1:2.2 | Algoritma teknikal rule-based |
| 29 | `roc_momentum` | **ROC Momentum 12** | Momentum | 15x | 1:2.0 | Algoritma teknikal rule-based |
| 30 | `hot_momentum` | **Impulse Candle** | Momentum | 15x | 1:2.0 | Momentum paling agresif: follow candle tubuh > 2 ATR. |
| 31 | `momentum_60` | **Multi-Horizon Momentum** | Momentum | 12x | 1:2.0 | Momentum 60 candle bertingkat (gaya time-series momentum). |
| 32 | `zscore_rev` | **Z-Score Reversion** | Statistik | 20x | 1:1.5 | Algoritma teknikal rule-based |
| 33 | `mean_sd_band` | **Mean Deviation Band** | Statistik | 15x | 1:1.5 | Algoritma teknikal rule-based |
| 34 | `time_session` | **Timezone Session Bias** | Waktu | 10x | 1:1.8 | Bias sesi: London open cenderung impulsif, NY close cenderung mean-revert. |
| 35 | `time_open` | **Opening Hour Range** | Waktu | 12x | 1:1.8 | Algoritma teknikal rule-based |
| 36 | `gap_fill` | **Gap Fill Reversal** | Price action | 15x | 1:1.8 | Algoritma teknikal rule-based |
| 37 | `2b_rev` | **2B Reversal** | Price action | 10x | 1:1.8 | Reversal 2B: dua kali gagal menembus swing dengan wick panjang. |
| 38 | `engulfing` | **Bullish/Bearish Engulfing** | Price action | 15x | 1:1.8 | Algoritma teknikal rule-based |
| 39 | `inside_bar` | **Inside Bar Breakout** | Price action | 15x | 1:1.8 | Algoritma teknikal rule-based |
| 40 | `swing_break` | **Swing Volume Break** | Price action | 10x | 1:1.8 | Algoritma teknikal rule-based |
| 41 | `vol_trend_sma` | **SMA50/200 Regime** | Trend | 6x | 1:2.2 | Algoritma teknikal rule-based |
| 42 | `ewma_trend` | **EMA200 Trend Bias** | Trend | 8x | 1:2.2 | EMA200 sebagai garis bias, EMA9 untuk timing. |
| 43 | `price_ema_dev` | **EMA Deviation** | Statistik | 12x | 1:1.5 | Algoritma teknikal rule-based |
| 44 | `price_ema_dev2` | **EMA50 Deviation** | Statistik | 15x | 1:1.5 | Algoritma teknikal rule-based |
| 45 | `rotation` | **RSI+MACD Rotation** | Momentum | 12x | 1:2.0 | RSI di zona netral + MACD cross = rotasi momentum jangka pendek. |
| 46 | `value_area` | **Value Area Auction** | Volume profile | 10x | 1:1.8 | Algoritma teknikal rule-based |
| 47 | `tr_break` | **Range Expansion Fade** | Volatility | 15x | 1:1.8 | True Range expansion: lawan impuls ekstrem sesaat. |
| 48 | `trend_pullback` | **Trend Pullback EMA9** | Trend | 10x | 1:2.2 | Algoritma teknikal rule-based |
| 49 | `mean_ma_cross` | **MA Cross Mean** | Trend | 8x | 1:2.2 | Algoritma teknikal rule-based |
| 50 | `rsi2_extreme` | **RSI2 Extreme** | Mean reversion | 20x | 1:1.5 | Algoritma teknikal rule-based |
| 51 | `turtle_soup` | **Turtle Soup Sweep** | Struktur | 15x | 1:1.8 | Algoritma teknikal rule-based |
| 52 | `delta_flow` | **Candle Imbalance** | Order flow | 20x | 1:2.0 | Algoritma teknikal rule-based |
| 53 | `wicks_reject` | **Wick Rejection** | Order flow | 15x | 1:2.0 | Algoritma teknikal rule-based |
| 54 | `paint_bar` | **Paint Bar Pattern** | Price action | 15x | 1:1.8 | Algoritma teknikal rule-based |
| 55 | `price_action_2b` | **2B Reversal** | Price action | 15x | 1:1.8 | Reversal 2B: dua kali gagal menembus swing dengan wick panjang. |
| 56 | `fractal_break` | **Fractal Breakout** | Breakout | 12x | 1:2.2 | Algoritma teknikal rule-based |
| 57 | `fx_lob_alpha` | **London Open Breakout** | Breakout | 1x | 1:2.2 | London Open Breakout: Breakout sesi London dengan konfirmasi volume & EMA. |
| 58 | `fx_tokyo_fader` | **Asian Range Fader** | Mean reversion | 1x | 1:1.5 | Asian Range Mean-Reversion: Fading rentang sempit sesi Tokyo. |
| 59 | `fx_frankfurt_probe` | **Frankfurt Liquidity Probe** | Order flow | 1x | 1:2.0 | Frankfurt Liquidity Probe: Menjebak likuiditas awal jam 06:00 UTC. |
| 60 | `fx_ny_reversal` | **New York Fixing Reversal** | Mean reversion | 1x | 1:1.5 | New York Institutional Fixing Reversal: Jam 15:00 - 17:00 UTC. |
| 61 | `fx_sunday_gap` | **Sunday Gap Fill Engine** | Statistik | 1x | 1:1.5 | Sunday Gap Fill: Fade lonjakan harga pembukaan terhadap penutupan. |
| 62 | `fx_aud_nzd_arb` | **Aussie-Kiwi Cointegration** | Statistik | 1x | 1:1.5 | Aussie-Kiwi Cointegration Arb: Deviasi statistik Z-Score. |
| 63 | `fx_triangular_synth` | **Triangular Arbitrage Synth** | Statistik | 1x | 1:1.5 | Cross-Rate Triangular Arbitrage Synth: Inefisiensi harga mikro. |
| 64 | `fx_oil_cad_divergence` | **Petro-CAD Divergence** | Trend | 1x | 1:2.2 | Commodity-Petro Currency Divergence. |
| 65 | `fx_gold_safehaven_relay` | **Safe-Haven Gold Relay** | Trend | 1x | 1:2.2 | Safe-Haven Risk Divergence Relay (Gold/Metals). |
| 66 | `fx_dragon_momentum` | **The Dragon Momentum Rider** | Momentum | 1x | 1:2.0 | The Dragon Momentum Rider (GBPJPY): Volatilitas tinggi. |
| 67 | `fx_bb_squeeze` | **BB Squeeze Volatility** | Volatility | 1x | 1:1.8 | Bollinger Bandwidth Volatility Explosion. |
| 68 | `fx_atr_expansion` | **ATR Expansion Breakout** | Breakout | 1x | 1:2.2 | ATR Expansion Channel Breakout. |
| 69 | `fx_gold_flash_spike` | **Gold Flash-Spike Reversal** | Oscillator | 1x | 1:1.5 | Gold Flash-Spike Mean Reversion. |
| 70 | `fx_ema_ribbon` | **Multi-TF EMA Ribbon** | Trend | 1x | 1:2.2 | Multi-Timeframe EMA Ribbon Alignment. |
| 71 | `fx_supertrend_trailing` | **SuperTrend Dynamic Trailing** | Trailing | 1x | 1:1.8 | SuperTrend Dynamic Trailing System. |
| 72 | `fx_ichimoku_quantum` | **Ichimoku Kumo Quantum** | Trend | 1x | 1:2.2 | Ichimoku Kumo Cloud Quantum Breakout. |
| 73 | `fx_heikin_ashi_smooth` | **Heikin-Ashi Trend Continuum** | Trend | 1x | 1:2.2 | Heikin-Ashi Smoothed Trend Continuum. |
| 74 | `fx_hedging_grid` | **Dynamic Hedging Grid** | Struktur | 1x | 1:1.8 | Dynamic Hedging Grid (Range-Optimized). |
| 75 | `fx_camarilla_fader` | **Camarilla Multi-Confluence** | Struktur | 1x | 1:1.8 | Camarilla Pivot Points Multi-Confluence. |
| 76 | `fx_orderflow_sweep` | **Order Flow Liquidity Sweep** | Order flow | 1x | 1:2.0 | Support/Resistance Order Flow Imbalance. |
| 77 | `fx_carry_yield_momentum` | **Synthetic Carry-Trade Yield** | Trend | 1x | 1:2.2 | Synthetic Carry-Trade Yield Momentum. |
| 78 | `fx_economic_straddle` | **Economic Straddle Breakout** | Breakout | 1x | 1:2.2 | Economic Event Straddle & Volatility Rider. |
| 79 | `fx_smc_orderblock` | **SMC Order Block Mitigation** | ICT | 1x | 1:1.8 | Institutional Order Block Mitigation (SMC). |
| 80 | `fx_ict_fair_value_gap` | **ICT Fair Value Gap (FVG)** | ICT | 1x | 1:1.8 | ICT Fair Value Gap (FVG) Imbalance Retest. |
| 81 | `fx_smc_liquidity_sweep` | **SMC Liquidity Sweep & BOS** | Struktur | 1x | 1:1.8 | SMC Liquidity Sweep & Market Structure Shift (MSS). |
| 82 | `fx_ict_optimal_trade_entry` | **ICT Optimal Trade Entry** | ICT | 1x | 1:1.8 | ICT Optimal Trade Entry (OTE 62% - 79% Retracement). |
| 83 | `fx_momentum_candle_burst` | **Momentum Candle Expansion** | Momentum | 1x | 1:2.0 | Momentum Candle (Marubozu / Full-Body Range Expansion). |
| 84 | `fx_three_line_strike` | **Three Line Strike Pattern** | Price action | 1x | 1:1.8 | Three Line Strike Price Action Reversal. |
| 85 | `fx_pinbar_liquidity_reject` | **Pin Bar Liquidity Rejection** | Price action | 1x | 1:1.8 | Pin Bar Rejection of Dynamic S/R (EMA21/50). |
| 86 | `fx_london_ny_overlap` | **London-NY Overlap Scalper** | Breakout | 1x | 1:2.2 | London - New York Session Overlap Scalper (13:00 - 17:00 UTC). |
| 87 | `fx_supply_demand_zone` | **Supply & Demand Zone** | Struktur | 1x | 1:1.8 | Institutional Supply & Demand Imbalance Retest. |
| 88 | `fx_volume_spread_analysis` | **Volume Spread Analysis (VSA)** | Order flow | 1x | 1:2.0 | Volume Spread Analysis (VSA) Stopping Volume & Absorption. |

---

## 2. Bedah Logika Teknis, Parameter & Audit Setiap Strategi

### #1. ICT Momentum (`ict_momentum`)

* **ID Sistem**: `ict_momentum`
* **Kategori / Family**: `ICT`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Order block: candle impulsif jauh di luar ATR, lalu harga kembali ke 50%-nya.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Filter Volatilitas**: Menggunakan ATR sebagai denominator. *Catatan*: Pastikan `atr > 0` untuk menghindari potensi *ZeroDivisionError* pada instrumen flat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #2. ICT Fair Value Gap (`ict_fvg`)

* **ID Sistem**: `ict_fvg`
* **Kategori / Family**: `ICT`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Fair Value Gap: gap antara high bar-2 dan low bar-0 lalu diisi (retest).

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #3. ICT Order Block Sweep (`ict_obs`)

* **ID Sistem**: `ict_obs`
* **Kategori / Family**: `ICT`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #4. Support Resistance Bounce (`snr_bounce`)

* **ID Sistem**: `snr_bounce`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #5. EMA Stack 9/21/50 (`trend_stack`)

* **ID Sistem**: `trend_stack`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #6. Donchian Turtle 55 (`donchian_55`)

* **ID Sistem**: `donchian_55`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
def donchian(s):
    return breakout(s, s.hh55, s.ll55)
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #7. Donchian Breakout 20 (`donchian_20`)

* **ID Sistem**: `donchian_20`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("donchian_20", "Donchian Breakout 20", "Breakout", lambda s: breakout(s, s.hh20, s.ll20)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #8. Keltner Channel Break (`keltner`)

* **ID Sistem**: `keltner`
* **Kategori / Family**: `Volatility`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #9. Bollinger Fade (`bb_rev`)

* **ID Sistem**: `bb_rev`
* **Kategori / Family**: `Mean reversion`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
def bollinger_reversion(s):
    c0, c1 = s.c[s.i - 1], s.c[s.i]
    if not _ok(c0, c1, s.bb_l[s.i], s.bb_l[s.i - 1], s.bb_u[s.i], s.bb_u[s.i - 1]):
        return 0.0
    if c0 < s.bb_l[s.i - 1] and c1 > s.bb_l[s.i]:
        return 0.8
    if c0 > s.bb_u[s.i - 1] and c1 < s.bb_u[s.i]:
        return -0.8
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #10. Squeeze Release (`squeeze`)

* **ID Sistem**: `squeeze`
* **Kategori / Family**: `Volatility`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #11. RSI Mean Reversion (`rsi_30_70`)

* **ID Sistem**: `rsi_30_70`
* **Kategori / Family**: `Mean reversion`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
def rsi_regime(s):
    return reversion(s, 30, 70)
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #12. Stochastic 20/80 (`stoch_cross`)

* **ID Sistem**: `stoch_cross`
* **Kategori / Family**: `Oscillator`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Stochastic %K cross 20/80.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #13. MACD Trend (`macd_cross`)

* **ID Sistem**: `macd_cross`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
def macd_cross(s):
    h0, h1 = s.macd_hist[s.i - 1], s.macd_hist[s.i]
    if not _ok(h0, h1):
        return 0.0
    if h0 <= 0 < h1:
        return 0.7 if s.macd[s.i] > 0 else 0.5
    if h0 >= 0 > h1:
        return -0.7 if s.macd[s.i] < 0 else -0.5
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **MACD**: Menggunakan histogram/signal cross. *Catatan*: Memiliki jeda (*lagging*) inheren; rentan terkena whipsaw saat pasar berkonsolidasi di rentang sempit.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #14. MACD Divergence (`macd_div`)

* **ID Sistem**: `macd_div`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **MACD**: Menggunakan histogram/signal cross. *Catatan*: Memiliki jeda (*lagging*) inheren; rentan terkena whipsaw saat pasar berkonsolidasi di rentang sempit.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #15. EMA21/50 Golden (`ema_macd_fast`)

* **ID Sistem**: `ema_macd_fast`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `8x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("ema_macd_fast", "EMA21/50 Golden", "Trend", lambda s: ema_cross(s, s.ema21, s.ema50)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **MACD**: Menggunakan histogram/signal cross. *Catatan*: Memiliki jeda (*lagging*) inheren; rentan terkena whipsaw saat pasar berkonsolidasi di rentang sempit.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #16. Golden Cross 50/200 (`golden_50_200`)

* **ID Sistem**: `golden_50_200`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `5x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("golden_50_200", "Golden Cross 50/200", "Trend", lambda s: ema_cross(s, s.sma50, s.sma200)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #17. Ichimoku Kumo (`ichimoku`)

* **ID Sistem**: `ichimoku`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `8x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #18. SuperTrend ATR (`supertrend`)

* **ID Sistem**: `supertrend`
* **Kategori / Family**: `Volatility`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > SuperTrend 10 x 3 ATR sederhana (arah dari posisi close vs ATR band).

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #19. Chandelier Exit (`chandelier`)

* **ID Sistem**: `chandelier`
* **Kategori / Family**: `Trailing`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #20. Fib Retracement 38-62 (`fib_retrace`)

* **ID Sistem**: `fib_retrace`
* **Kategori / Family**: `Fibonacci`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `8x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Retrace ke 38.2–61.8% dari swing 50 bar, searah tren EMA50.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #21. Fib Extension Trend (`fib_ext`)

* **ID Sistem**: `fib_ext`
* **Kategori / Family**: `Fibonacci`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `8x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("fib_ext", "Fib Extension Trend", "Fibonacci", lambda s: trend_stack(s) if 0.25 <= ((s.c[s.i] - float(s.l[s.i - 49:s.i + 1].min())) / max(float(s.h[s.i - 49:s.i + 1].max()) - float(s.l[s.i - 49:s.i + 1].min()), 1e-9)) <= 0.5 else 0.0),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #22. Fib Golden Pocket 61.8 (`fib_golden_pocket`)

* **ID Sistem**: `fib_golden_pocket`
* **Kategori / Family**: `Fibonacci`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Entry di Golden Pocket (61.8% - 65% retracement) dari swing 60 bar dengan konfirmasi candlestick & EMA50.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #23. Fib Extension 1.618 (`fib_expansion_1618`)

* **ID Sistem**: `fib_expansion_1618`
* **Kategori / Family**: `Fibonacci`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Breakout ekspansi Fibonacci 1.272–1.618 ekstensi dengan dorongan momentum.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #24. VWAP Deviation (`vwap_band`)

* **ID Sistem**: `vwap_band`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > VWAP jendela 60 candle, mean reversion ke band.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #25. VWAP Trend Follow (`vwap_trend`)

* **ID Sistem**: `vwap_trend`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("vwap_trend", "VWAP Trend Follow", "Statistik", lambda s: trend_stack(s) if s.c[s.i] > s.ema50[s.i] else -trend_stack(s) if _ok(s.ema50[s.i]) else 0.0),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #26. Volume Breakout (`vol_breakout`)

* **ID Sistem**: `vol_breakout`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
def volume_breakout(s):
    i = s.i
    if not _ok(s.vol_sma20[i]) or s.vol_sma20[i] <= 0:
        return 0.0
    if s.v[i] < s.vol_sma20[i] * 2.5:
        return 0.0
    return breakout(s, s.hh20, s.ll20)
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #27. Volatility Trend Filter (`vol_target`)

* **ID Sistem**: `vol_target`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `8x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Trading saat volatilitas normal: follow tren hanya kalau ATR/close sehat.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #28. ADX Strong Trend (`adx_trend`)

* **ID Sistem**: `adx_trend`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #29. ROC Momentum 12 (`roc_momentum`)

* **ID Sistem**: `roc_momentum`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
def roc_momentum(s):
    i = s.i
    if i < 12:
        return 0.0
    roc = s.c[i] / s.c[i - 12] - 1
    if abs(roc) < 0.0025:
        return 0.0
    return max(-0.9, min(0.9, roc * 120))
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #30. Impulse Candle (`hot_momentum`)

* **ID Sistem**: `hot_momentum`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Momentum paling agresif: follow candle tubuh > 2 ATR.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #31. Multi-Horizon Momentum (`momentum_60`)

* **ID Sistem**: `momentum_60`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Momentum 60 candle bertingkat (gaya time-series momentum).

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #32. Z-Score Reversion (`zscore_rev`)

* **ID Sistem**: `zscore_rev`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `20x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #33. Mean Deviation Band (`mean_sd_band`)

* **ID Sistem**: `mean_sd_band`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("mean_sd_band", "Mean Deviation Band", "Statistik", lambda s: -zscore_reversion(s) * 0.7),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #34. Timezone Session Bias (`time_session`)

* **ID Sistem**: `time_session`
* **Kategori / Family**: `Waktu`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Bias sesi: London open cenderung impulsif, NY close cenderung mean-revert.

**Potongan Kode Algoritma (Python)**:
```python
def time_filter(s):
    """Bias sesi: London open cenderung impulsif, NY close cenderung mean-revert."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if 7 <= hour <= 10 or 13 <= hour <= 15:
        return trend_stack(s) * 1.15
    if 20 <= hour <= 22:
        return -trend_stack(s) * 0.9
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #35. Opening Hour Range (`time_open`)

* **ID Sistem**: `time_open`
* **Kategori / Family**: `Waktu`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("time_open", "Opening Hour Range", "Waktu", lambda s: trend_stack(s) if int((s.ts[s.i] // 3600000) % 24) in (0, 1, 2, 3) else 0.0),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #36. Gap Fill Reversal (`gap_fill`)

* **ID Sistem**: `gap_fill`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #37. 2B Reversal (`2b_rev`)

* **ID Sistem**: `2b_rev`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Reversal 2B: dua kali gagal menembus swing dengan wick panjang.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Counter-Trend (Fade)**: Melawan pergerakan harga ekstrem. *Catatan*: Perlu disiplin ketat pada Stop Loss karena jika terjadi *news flash crash*, posisi counter-trend dapat mengalami drawdown cepat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #38. Bullish/Bearish Engulfing (`engulfing`)

* **ID Sistem**: `engulfing`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #39. Inside Bar Breakout (`inside_bar`)

* **ID Sistem**: `inside_bar`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #40. Swing Volume Break (`swing_break`)

* **ID Sistem**: `swing_break`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #41. SMA50/200 Regime (`vol_trend_sma`)

* **ID Sistem**: `vol_trend_sma`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `6x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
def vol_trend_sma(s):
    i = s.i
    if not _ok(s.sma50[i], s.sma200[i]):
        return 0.0
    if s.sma50[i] > s.sma200[i] and s.c[i] > s.sma20[i]:
        return 0.5
    if s.sma50[i] < s.sma200[i] and s.c[i] < s.sma20[i]:
        return -0.5
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #42. EMA200 Trend Bias (`ewma_trend`)

* **ID Sistem**: `ewma_trend`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `8x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > EMA200 sebagai garis bias, EMA9 untuk timing.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #43. EMA Deviation (`price_ema_dev`)

* **ID Sistem**: `price_ema_dev`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("price_ema_dev", "EMA Deviation", "Statistik", lambda s: mean_ema(s, s.ema9, s.ema21)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #44. EMA50 Deviation (`price_ema_dev2`)

* **ID Sistem**: `price_ema_dev2`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("price_ema_dev2", "EMA50 Deviation", "Statistik", lambda s: mean_ema(s, s.ema21, s.ema50)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #45. RSI+MACD Rotation (`rotation`)

* **ID Sistem**: `rotation`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > RSI di zona netral + MACD cross = rotasi momentum jangka pendek.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **MACD**: Menggunakan histogram/signal cross. *Catatan*: Memiliki jeda (*lagging*) inheren; rentan terkena whipsaw saat pasar berkonsolidasi di rentang sempit.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #46. Value Area Auction (`value_area`)

* **ID Sistem**: `value_area`
* **Kategori / Family**: `Volume profile`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("value_area", "Value Area Auction", "Volume profile", lambda s: vwap_band(s)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #47. Range Expansion Fade (`tr_break`)

* **ID Sistem**: `tr_break`
* **Kategori / Family**: `Volatility`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > True Range expansion: lawan impuls ekstrem sesaat.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Filter Volatilitas**: Menggunakan ATR sebagai denominator. *Catatan*: Pastikan `atr > 0` untuk menghindari potensi *ZeroDivisionError* pada instrumen flat.
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #48. Trend Pullback EMA9 (`trend_pullback`)

* **ID Sistem**: `trend_pullback`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `10x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("trend_pullback", "Trend Pullback EMA9", "Trend", lambda s: 0.6 if (s.c[s.i] > s.ema50[s.i] and s.c[s.i] < s.ema9[s.i] and s.rsi14[s.i] < 50) else (-0.6 if (_ok(s.ema50[s.i]) and s.c[s.i] < s.ema50[s.i] and s.c[s.i] > s.ema9[s.i] and s.rsi14[s.i] > 50) else 0.0)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #49. MA Cross Mean (`mean_ma_cross`)

* **ID Sistem**: `mean_ma_cross`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `8x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("mean_ma_cross", "MA Cross Mean", "Trend", lambda s: 0.5 if (_ok(s.sma20[s.i], s.sma50[s.i]) and s.sma20[s.i] > s.sma50[s.i] and s.c[s.i] > s.sma20[s.i]) else (-0.5 if (_ok(s.sma20[s.i], s.sma50[s.i]) and s.sma20[s.i] < s.sma50[s.i] and s.c[s.i] < s.sma20[s.i]) else 0.0)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #50. RSI2 Extreme (`rsi2_extreme`)

* **ID Sistem**: `rsi2_extreme`
* **Kategori / Family**: `Mean reversion`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `20x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("rsi2_extreme", "RSI2 Extreme", "Mean reversion", lambda s: 0.7 if s.rsi2[s.i] < 10 else (-0.7 if s.rsi2[s.i] > 90 else 0.0)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #51. Turtle Soup Sweep (`turtle_soup`)

* **ID Sistem**: `turtle_soup`
* **Kategori / Family**: `Struktur`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("turtle_soup", "Turtle Soup Sweep", "Struktur", lambda s: 0.65 if (s.l[s.i] < s.ll20[s.i - 1] and s.c[s.i] > s.ll20[s.i - 1]) else (-0.65 if (s.h[s.i] > s.hh20[s.i - 1] and s.c[s.i] < s.hh20[s.i - 1]) else 0.0)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #52. Candle Imbalance (`delta_flow`)

* **ID Sistem**: `delta_flow`
* **Kategori / Family**: `Order flow`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `20x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("delta_flow", "Candle Imbalance", "Order flow", lambda s: (0.35 if (s.c[s.i] - s.l[s.i]) > 0.65 * max(s.h[s.i] - s.l[s.i], 1e-12) else (-0.35 if (s.h[s.i] - s.c[s.i]) > 0.65 * max(s.h[s.i] - s.l[s.i], 1e-12) else 0.0)) * (1 if s.c[s.i] > s.ema21[s.i] else -1)),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #53. Wick Rejection (`wicks_reject`)

* **ID Sistem**: `wicks_reject`
* **Kategori / Family**: `Order flow`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
("wicks_reject", "Wick Rejection", "Order flow", lambda s: (0.6 if (s.h[s.i] - s.c[s.i]) > 1.8 * abs(s.c[s.i] - s.o[s.i] + 1e-12) and s.h[s.i] > s.ema21[s.i] else (-0.6 if (s.c[s.i] - s.l[s.i]) > 1.8 * abs(s.c[s.i] - s.o[s.i] + 1e-12) and s.l[s.i] < s.ema21[s.i] else 0.0))),
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #54. Paint Bar Pattern (`paint_bar`)

* **ID Sistem**: `paint_bar`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #55. 2B Reversal (`price_action_2b`)

* **ID Sistem**: `price_action_2b`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `15x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Reversal 2B: dua kali gagal menembus swing dengan wick panjang.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Counter-Trend (Fade)**: Melawan pergerakan harga ekstrem. *Catatan*: Perlu disiplin ketat pada Stop Loss karena jika terjadi *news flash crash*, posisi counter-trend dapat mengalami drawdown cepat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #56. Fractal Breakout (`fractal_break`)

* **ID Sistem**: `fractal_break`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `12x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: Eksekusi momentum / mean-reversion teknikal berbasis indikator real-time.

**Potongan Kode Algoritma (Python)**:
```python
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #57. London Open Breakout (`fx_lob_alpha`)

* **ID Sistem**: `fx_lob_alpha`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > London Open Breakout: Breakout sesi London dengan konfirmasi volume & EMA.

**Potongan Kode Algoritma (Python)**:
```python
def fx_lob_alpha(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #58. Asian Range Fader (`fx_tokyo_fader`)

* **ID Sistem**: `fx_tokyo_fader`
* **Kategori / Family**: `Mean reversion`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Asian Range Mean-Reversion: Fading rentang sempit sesi Tokyo.

**Potongan Kode Algoritma (Python)**:
```python
def fx_tokyo_fader(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Counter-Trend (Fade)**: Melawan pergerakan harga ekstrem. *Catatan*: Perlu disiplin ketat pada Stop Loss karena jika terjadi *news flash crash*, posisi counter-trend dapat mengalami drawdown cepat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #59. Frankfurt Liquidity Probe (`fx_frankfurt_probe`)

* **ID Sistem**: `fx_frankfurt_probe`
* **Kategori / Family**: `Order flow`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Frankfurt Liquidity Probe: Menjebak likuiditas awal jam 06:00 UTC.

**Potongan Kode Algoritma (Python)**:
```python
def fx_frankfurt_probe(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #60. New York Fixing Reversal (`fx_ny_reversal`)

* **ID Sistem**: `fx_ny_reversal`
* **Kategori / Family**: `Mean reversion`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > New York Institutional Fixing Reversal: Jam 15:00 - 17:00 UTC.

**Potongan Kode Algoritma (Python)**:
```python
def fx_ny_reversal(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Counter-Trend (Fade)**: Melawan pergerakan harga ekstrem. *Catatan*: Perlu disiplin ketat pada Stop Loss karena jika terjadi *news flash crash*, posisi counter-trend dapat mengalami drawdown cepat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #61. Sunday Gap Fill Engine (`fx_sunday_gap`)

* **ID Sistem**: `fx_sunday_gap`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Sunday Gap Fill: Fade lonjakan harga pembukaan terhadap penutupan.

**Potongan Kode Algoritma (Python)**:
```python
def fx_sunday_gap(s):
    """Sunday Gap Fill: Fade lonjakan harga pembukaan terhadap penutupan."""
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Counter-Trend (Fade)**: Melawan pergerakan harga ekstrem. *Catatan*: Perlu disiplin ketat pada Stop Loss karena jika terjadi *news flash crash*, posisi counter-trend dapat mengalami drawdown cepat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #62. Aussie-Kiwi Cointegration (`fx_aud_nzd_arb`)

* **ID Sistem**: `fx_aud_nzd_arb`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Aussie-Kiwi Cointegration Arb: Deviasi statistik Z-Score.

**Potongan Kode Algoritma (Python)**:
```python
def fx_aud_nzd_arb(s):
    """Aussie-Kiwi Cointegration Arb: Deviasi statistik Z-Score."""
    c, e50, atr = s.c[s.i], s.ema50[s.i], s.atr14[s.i]
    if not _ok(c, e50, atr) or atr <= 0:
        return 0.0
    z = (c - e50) / atr
    if z < -2.0:
        return 0.85
    if z > 2.0:
        return -0.85
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #63. Triangular Arbitrage Synth (`fx_triangular_synth`)

* **ID Sistem**: `fx_triangular_synth`
* **Kategori / Family**: `Statistik`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Cross-Rate Triangular Arbitrage Synth: Inefisiensi harga mikro.

**Potongan Kode Algoritma (Python)**:
```python
def fx_triangular_synth(s):
    """Cross-Rate Triangular Arbitrage Synth: Inefisiensi harga mikro."""
    c, sma, hist, stoch = s.c[s.i], s.sma20[s.i], s.macd_hist[s.i], s.stoch_k[s.i]
    if not _ok(c, sma, hist, stoch):
        return 0.0
    if c > sma and hist > 0 and stoch < 35:
        return 0.75
    if c < sma and hist < 0 and stoch > 65:
        return -0.75
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **MACD**: Menggunakan histogram/signal cross. *Catatan*: Memiliki jeda (*lagging*) inheren; rentan terkena whipsaw saat pasar berkonsolidasi di rentang sempit.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #64. Petro-CAD Divergence (`fx_oil_cad_divergence`)

* **ID Sistem**: `fx_oil_cad_divergence`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Commodity-Petro Currency Divergence.

**Potongan Kode Algoritma (Python)**:
```python
def fx_oil_cad_divergence(s):
    """Commodity-Petro Currency Divergence."""
    c, e21, e50, rsi = s.c[s.i], s.ema21[s.i], s.ema50[s.i], s.rsi14[s.i]
    if not _ok(c, e21, e50, rsi):
        return 0.0
    if e21 > e50 and c < e21 and rsi < 45:
        return 0.75
    if e21 < e50 and c > e21 and rsi > 55:
        return -0.75
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #65. Safe-Haven Gold Relay (`fx_gold_safehaven_relay`)

* **ID Sistem**: `fx_gold_safehaven_relay`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Safe-Haven Risk Divergence Relay (Gold/Metals).

**Potongan Kode Algoritma (Python)**:
```python
def fx_gold_safehaven_relay(s):
    """Safe-Haven Risk Divergence Relay (Gold/Metals)."""
    c, hh, ll, pdi, mdi, adx = s.c[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1], s.plus_di[s.i], s.minus_di[s.i], s.adx[s.i]
    if not _ok(c, hh, ll, pdi, mdi, adx):
        return 0.0
    if c > hh and pdi > mdi and adx > 22:
        return 0.85
    if c < ll and mdi > pdi and adx > 22:
        return -0.85
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #66. The Dragon Momentum Rider (`fx_dragon_momentum`)

* **ID Sistem**: `fx_dragon_momentum`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > The Dragon Momentum Rider (GBPJPY): Volatilitas tinggi.

**Potongan Kode Algoritma (Python)**:
```python
def fx_dragon_momentum(s):
    """The Dragon Momentum Rider (GBPJPY): Volatilitas tinggi."""
    c, hh, ll, e9, atr = s.c[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1], s.ema9[s.i], s.atr14[s.i]
    if not _ok(c, hh, ll, e9, atr):
        return 0.0
    if c > hh and c > e9:
        return 0.85
    if c < ll and c < e9:
        return -0.85
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #67. BB Squeeze Volatility (`fx_bb_squeeze`)

* **ID Sistem**: `fx_bb_squeeze`
* **Kategori / Family**: `Volatility`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Bollinger Bandwidth Volatility Explosion.

**Potongan Kode Algoritma (Python)**:
```python
def fx_bb_squeeze(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #68. ATR Expansion Breakout (`fx_atr_expansion`)

* **ID Sistem**: `fx_atr_expansion`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > ATR Expansion Channel Breakout.

**Potongan Kode Algoritma (Python)**:
```python
def fx_atr_expansion(s):
    """ATR Expansion Channel Breakout."""
    h, l, c, o, atr = s.h[s.i], s.l[s.i], s.c[s.i], s.o[s.i], s.atr14[s.i]
    if not _ok(h, l, c, o, atr) or atr <= 0:
        return 0.0
    if (h - l) > 1.5 * atr and c > o:
        return 0.8
    if (h - l) > 1.5 * atr and c < o:
        return -0.8
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #69. Gold Flash-Spike Reversal (`fx_gold_flash_spike`)

* **ID Sistem**: `fx_gold_flash_spike`
* **Kategori / Family**: `Oscillator`
* **Rasio Risk-to-Reward**: `1 : 1.5`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Gold Flash-Spike Mean Reversion.

**Potongan Kode Algoritma (Python)**:
```python
def fx_gold_flash_spike(s):
    """Gold Flash-Spike Mean Reversion."""
    h, l, c, atr, rsi = s.h[s.i], s.l[s.i], s.c[s.i], s.atr14[s.i], s.rsi14[s.i]
    if not _ok(h, l, c, atr, rsi) or atr <= 0:
        return 0.0
    if (h - l) > 1.8 * atr and c < (h + l) / 2 and rsi > 68:
        return -0.85
    if (h - l) > 1.8 * atr and c > (h + l) / 2 and rsi < 32:
        return 0.85
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #70. Multi-TF EMA Ribbon (`fx_ema_ribbon`)

* **ID Sistem**: `fx_ema_ribbon`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Multi-Timeframe EMA Ribbon Alignment.

**Potongan Kode Algoritma (Python)**:
```python
def fx_ema_ribbon(s):
    """Multi-Timeframe EMA Ribbon Alignment."""
    e9, e21, e50, e200, c = s.ema9[s.i], s.ema21[s.i], s.ema50[s.i], s.ema200[s.i], s.c[s.i]
    if not _ok(e9, e21, e50, e200, c):
        return 0.0
    if e9 > e21 > e50 > e200 and c > e9:
        return 0.85
    if e9 < e21 < e50 < e200 and c < e9:
        return -0.85
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #71. SuperTrend Dynamic Trailing (`fx_supertrend_trailing`)

* **ID Sistem**: `fx_supertrend_trailing`
* **Kategori / Family**: `Trailing`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > SuperTrend Dynamic Trailing System.

**Potongan Kode Algoritma (Python)**:
```python
def fx_supertrend_trailing(s):
    """SuperTrend Dynamic Trailing System."""
    c0, c1 = s.c[s.i - 1], s.c[s.i]
    sma, atr = s.sma20[s.i], s.atr14[s.i]
    if not _ok(c0, c1, sma, atr):
        return 0.0
    up = sma + 1.2 * atr
    dn = sma - 1.2 * atr
    if c0 <= up and c1 > up:
        return 0.8
    if c0 >= dn and c1 < dn:
        return -0.8
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #72. Ichimoku Kumo Quantum (`fx_ichimoku_quantum`)

* **ID Sistem**: `fx_ichimoku_quantum`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Ichimoku Kumo Cloud Quantum Breakout.

**Potongan Kode Algoritma (Python)**:
```python
def fx_ichimoku_quantum(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #73. Heikin-Ashi Trend Continuum (`fx_heikin_ashi_smooth`)

* **ID Sistem**: `fx_heikin_ashi_smooth`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Heikin-Ashi Smoothed Trend Continuum.

**Potongan Kode Algoritma (Python)**:
```python
def fx_heikin_ashi_smooth(s):
    """Heikin-Ashi Smoothed Trend Continuum."""
    c, o, adx = s.c[s.i], s.o[s.i], s.adx[s.i]
    c1, o1 = s.c[s.i - 1], s.o[s.i - 1]
    if not _ok(c, o, c1, o1, adx):
        return 0.0
    if c > o and c1 > o1 and adx > 22:
        return 0.75
    if c < o and c1 < o1 and adx > 22:
        return -0.75
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #74. Dynamic Hedging Grid (`fx_hedging_grid`)

* **ID Sistem**: `fx_hedging_grid`
* **Kategori / Family**: `Struktur`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Dynamic Hedging Grid (Range-Optimized).

**Potongan Kode Algoritma (Python)**:
```python
def fx_hedging_grid(s):
    """Dynamic Hedging Grid (Range-Optimized)."""
    c, sma, atr, adx = s.c[s.i], s.sma20[s.i], s.atr14[s.i], s.adx[s.i]
    if not _ok(c, sma, atr, adx) or adx >= 20:
        return 0.0
    if c < sma - 1.2 * atr:
        return 0.7
    if c > sma + 1.2 * atr:
        return -0.7
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #75. Camarilla Multi-Confluence (`fx_camarilla_fader`)

* **ID Sistem**: `fx_camarilla_fader`
* **Kategori / Family**: `Struktur`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Camarilla Pivot Points Multi-Confluence.

**Potongan Kode Algoritma (Python)**:
```python
def fx_camarilla_fader(s):
    """Camarilla Pivot Points Multi-Confluence."""
    c, h, l, ll, hh = s.c[s.i], s.h[s.i], s.l[s.i], s.ll20[s.i - 1], s.hh20[s.i - 1]
    rng = h - l
    if not _ok(c, h, l, ll, hh) or rng <= 0:
        return 0.0
    if c < ll and (c - l) > 0.6 * rng:
        return 0.75
    if c > hh and (h - c) > 0.6 * rng:
        return -0.75
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Counter-Trend (Fade)**: Melawan pergerakan harga ekstrem. *Catatan*: Perlu disiplin ketat pada Stop Loss karena jika terjadi *news flash crash*, posisi counter-trend dapat mengalami drawdown cepat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #76. Order Flow Liquidity Sweep (`fx_orderflow_sweep`)

* **ID Sistem**: `fx_orderflow_sweep`
* **Kategori / Family**: `Order flow`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Support/Resistance Order Flow Imbalance.

**Potongan Kode Algoritma (Python)**:
```python
def fx_orderflow_sweep(s):
    """Support/Resistance Order Flow Imbalance."""
    c, o, l, h, ll, hh, e9 = s.c[s.i], s.o[s.i], s.l[s.i], s.h[s.i], s.ll20[s.i - 1], s.hh20[s.i - 1], s.ema9[s.i]
    if not _ok(c, o, l, h, ll, hh, e9):
        return 0.0
    if l < ll and c > o and c > e9:
        return 0.8
    if h > hh and c < o and c < e9:
        return -0.8
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #77. Synthetic Carry-Trade Yield (`fx_carry_yield_momentum`)

* **ID Sistem**: `fx_carry_yield_momentum`
* **Kategori / Family**: `Trend`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Synthetic Carry-Trade Yield Momentum.

**Potongan Kode Algoritma (Python)**:
```python
def fx_carry_yield_momentum(s):
    """Synthetic Carry-Trade Yield Momentum."""
    c, e50, e200, rsi = s.c[s.i], s.ema50[s.i], s.ema200[s.i], s.rsi14[s.i]
    if not _ok(c, e50, e200, rsi):
        return 0.0
    if c > e200 and e50 > e200 and rsi > 52:
        return 0.75
    if c < e200 and e50 < e200 and rsi < 48:
        return -0.75
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Osilator RSI**: Mengandalkan kondisi overbought/oversold. *Catatan*: Pada pasar trending searah yang sangat kuat (*one-way rally/dump*), RSI bisa bertahan lama di area ekstrem sehingga rawan memicu false reversal terus-menerus.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #78. Economic Straddle Breakout (`fx_economic_straddle`)

* **ID Sistem**: `fx_economic_straddle`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Economic Event Straddle & Volatility Rider.

**Potongan Kode Algoritma (Python)**:
```python
def fx_economic_straddle(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #79. SMC Order Block Mitigation (`fx_smc_orderblock`)

* **ID Sistem**: `fx_smc_orderblock`
* **Kategori / Family**: `ICT`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Institutional Order Block Mitigation (SMC).

**Potongan Kode Algoritma (Python)**:
```python
def fx_smc_orderblock(s):
    """Institutional Order Block Mitigation (SMC)."""
    if s.i < 15:
        return 0.0
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    # Bullish OB: last down candle before displacement wave up, retested by current candle
    for k in range(s.i - 2, max(s.i - 10, 1), -1):
        if s.c[k] < s.o[k] and (s.c[k + 1] - s.c[k]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if l <= ob_high and c >= ob_low and c > o:
                return 0.80
            break
    # Bearish OB: last up candle before displacement wave down, retested by current candle
    for k in range(s.i - 2, max(s.i - 10, 1), -1):
        if s.c[k] > s.o[k] and (s.c[k] - s.c[k + 1]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if h >= ob_low and c <= ob_high and c < o:
                return -0.80
            break
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Breakout Engine**: Mengikuti penembusan level High/Low. *Catatan*: Sangat rentan terhadap *Fakeout / Liquidity Hunt* jika tidak dilengkapi filter penutupan candle (*candle close confirmation*).
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #80. ICT Fair Value Gap (FVG) (`fx_ict_fair_value_gap`)

* **ID Sistem**: `fx_ict_fair_value_gap`
* **Kategori / Family**: `ICT`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > ICT Fair Value Gap (FVG) Imbalance Retest.

**Potongan Kode Algoritma (Python)**:
```python
def fx_ict_fair_value_gap(s):
    """ICT Fair Value Gap (FVG) Imbalance Retest."""
    if s.i < 5:
        return 0.0
    c, o, h, l = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i]
    h2, l2, h0, l0 = s.h[s.i - 2], s.l[s.i - 2], s.h[s.i], s.l[s.i]
    if not _ok(c, o, h, l, h2, l2):
        return 0.0
    # Bullish FVG created at bar i-1 (low[i-1] > high[i-3] or low[i] > high[i-2])
    gap_low, gap_high = s.h[s.i - 2], s.l[s.i - 1]
    if gap_high > gap_low:
        # Price dips into FVG and closes bullish
        if l <= gap_high and c >= gap_low and c > o:
            return 0.80
    # Bearish FVG (high[i-1] < low[i-3] or high[i-1] < low[i-2])
    bgap_high, bgap_low = s.l[s.i - 2], s.h[s.i - 1]
    if bgap_high > bgap_low:
        if h >= bgap_low and c <= bgap_high and c < o:
            return -0.80
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #81. SMC Liquidity Sweep & BOS (`fx_smc_liquidity_sweep`)

* **ID Sistem**: `fx_smc_liquidity_sweep`
* **Kategori / Family**: `Struktur`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > SMC Liquidity Sweep & Market Structure Shift (MSS).

**Potongan Kode Algoritma (Python)**:
```python
def fx_smc_liquidity_sweep(s):
    """SMC Liquidity Sweep & Market Structure Shift (MSS)."""
    c, o, h, l, hh, ll = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1]
    if not _ok(c, o, h, l, hh, ll):
        return 0.0
    rng = max(h - l, 1e-9)
    # Sellside Liquidity Sweep: price sweeps below 20-bar low, but closes back above with lower wick >= 50%
    if l < ll and c > ll and (min(o, c) - l) / rng >= 0.45:
        return 0.85
    # Buyside Liquidity Sweep: price sweeps above 20-bar high, but closes back below with upper wick >= 50%
    if h > hh and c < hh and (h - max(o, c)) / rng >= 0.45:
        return -0.85
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #82. ICT Optimal Trade Entry (`fx_ict_optimal_trade_entry`)

* **ID Sistem**: `fx_ict_optimal_trade_entry`
* **Kategori / Family**: `ICT`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > ICT Optimal Trade Entry (OTE 62% - 79% Retracement).

**Potongan Kode Algoritma (Python)**:
```python
def fx_ict_optimal_trade_entry(s):
    """ICT Optimal Trade Entry (OTE 62% - 79% Retracement)."""
    c, o, hh, ll, e21, e50 = s.c[s.i], s.o[s.i], s.hh20[s.i], s.ll20[s.i], s.ema21[s.i], s.ema50[s.i]
    if not _ok(c, o, hh, ll, e21, e50):
        return 0.0
    rng = hh - ll
    if rng <= 0:
        return 0.0
    # Uptrend OTE: pullback into 61.8% - 78.6% discount zone
    if e21 > e50 and c > o:
        depth = (hh - c) / rng
        if 0.58 <= depth <= 0.80:
            return 0.78
    # Downtrend OTE: rally into 61.8% - 78.6% premium zone
    if e21 < e50 and c < o:
        depth = (c - ll) / rng
        if 0.58 <= depth <= 0.80:
            return -0.78
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #83. Momentum Candle Expansion (`fx_momentum_candle_burst`)

* **ID Sistem**: `fx_momentum_candle_burst`
* **Kategori / Family**: `Momentum`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Momentum Candle (Marubozu / Full-Body Range Expansion).

**Potongan Kode Algoritma (Python)**:
```python
def fx_momentum_candle_burst(s):
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
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Filter Volatilitas**: Menggunakan ATR sebagai denominator. *Catatan*: Pastikan `atr > 0` untuk menghindari potensi *ZeroDivisionError* pada instrumen flat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #84. Three Line Strike Pattern (`fx_three_line_strike`)

* **ID Sistem**: `fx_three_line_strike`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Three Line Strike Price Action Reversal.

**Potongan Kode Algoritma (Python)**:
```python
def fx_three_line_strike(s):
    """Three Line Strike Price Action Reversal."""
    if s.i < 4:
        return 0.0
    c0, o0 = s.c[s.i], s.o[s.i]
    c1, o1 = s.c[s.i - 1], s.o[s.i - 1]
    c2, o2 = s.c[s.i - 2], s.o[s.i - 2]
    c3, o3 = s.c[s.i - 3], s.o[s.i - 3]
    if not _ok(c0, o0, c1, o1, c2, o2, c3, o3):
        return 0.0
    # Bullish Strike: 3 consecutive bear bars wiped out by 1 powerful bull candle
    if c3 < o3 and c2 < o2 and c1 < o1 and c1 < c2 < c3:
        if c0 > o0 and c0 > o3 and o0 <= c1:
            return 0.85
    # Bearish Strike: 3 consecutive bull bars wiped out by 1 powerful bear candle
    if c3 > o3 and c2 > o2 and c1 > o1 and c1 > c2 > c3:
        if c0 < o0 and c0 < o3 and o0 >= c1:
            return -0.85
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Counter-Trend (Fade)**: Melawan pergerakan harga ekstrem. *Catatan*: Perlu disiplin ketat pada Stop Loss karena jika terjadi *news flash crash*, posisi counter-trend dapat mengalami drawdown cepat.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #85. Pin Bar Liquidity Rejection (`fx_pinbar_liquidity_reject`)

* **ID Sistem**: `fx_pinbar_liquidity_reject`
* **Kategori / Family**: `Price action`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Pin Bar Rejection of Dynamic S/R (EMA21/50).

**Potongan Kode Algoritma (Python)**:
```python
def fx_pinbar_liquidity_reject(s):
    """Pin Bar Rejection of Dynamic S/R (EMA21/50)."""
    c, o, h, l, e21 = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.ema21[s.i]
    if not _ok(c, o, h, l, e21):
        return 0.0
    rng = max(h - l, 1e-9)
    body = abs(c - o)
    # Bullish Hammer/Pin: lower wick >= 60% of candle range, body <= 30%
    if (min(o, c) - l) / rng >= 0.60 and body / rng <= 0.32:
        if l < e21 and c >= e21 * 0.999:
            return 0.80
    # Bearish Shooting Star/Pin: upper wick >= 60% of candle range, body <= 30%
    if (h - max(o, c)) / rng >= 0.60 and body / rng <= 0.32:
        if h > e21 and c <= e21 * 1.001:
            return -0.80
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #86. London-NY Overlap Scalper (`fx_london_ny_overlap`)

* **ID Sistem**: `fx_london_ny_overlap`
* **Kategori / Family**: `Breakout`
* **Rasio Risk-to-Reward**: `1 : 2.2`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > London - New York Session Overlap Scalper (13:00 - 17:00 UTC).

**Potongan Kode Algoritma (Python)**:
```python
def fx_london_ny_overlap(s):
    """London - New York Session Overlap Scalper (13:00 - 17:00 UTC)."""
    c, o, e9, e21, adx = s.c[s.i], s.o[s.i], s.ema9[s.i], s.ema21[s.i], s.adx[s.i]
    if not _ok(c, o, e9, e21, adx):
        return 0.0
    hr = int((s.ts[s.i] // 3600000) % 24)
    # Peak overlap hours
    if 12 <= hr <= 17:
        if c > e9 > e21 and adx > 20 and c > o:
            return 0.75
        if c < e9 < e21 and adx > 20 and c < o:
            return -0.75
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #87. Supply & Demand Zone (`fx_supply_demand_zone`)

* **ID Sistem**: `fx_supply_demand_zone`
* **Kategori / Family**: `Struktur`
* **Rasio Risk-to-Reward**: `1 : 1.8`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Institutional Supply & Demand Imbalance Retest.

**Potongan Kode Algoritma (Python)**:
```python
def fx_supply_demand_zone(s):
    """Institutional Supply & Demand Imbalance Retest."""
    if s.i < 5:
        return 0.0
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    # Demand Zone (Rally-Base-Rally): base at i-2, rally at i-1, retest at i
    base_h, base_l = s.h[s.i - 2], s.l[s.i - 2]
    rally = s.c[s.i - 1] - s.o[s.i - 1]
    if rally > 1.0 * atr and (base_h - base_l) < 0.8 * atr:
        if l <= base_h and c >= base_l and c > o:
            return 0.80
    # Supply Zone (Drop-Base-Drop): base at i-2, drop at i-1, retest at i
    drop = s.o[s.i - 1] - s.c[s.i - 1]
    if drop > 1.0 * atr and (base_h - base_l) < 0.8 * atr:
        if h >= base_l and c <= base_h and c < o:
            return -0.80
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

### #88. Volume Spread Analysis (VSA) (`fx_volume_spread_analysis`)

* **ID Sistem**: `fx_volume_spread_analysis`
* **Kategori / Family**: `Order flow`
* **Rasio Risk-to-Reward**: `1 : 2.0`
* **Default Leverage (Futures)**: `1x` (Di Forex: `1x MT5 Direct`)
* **Deskripsi Konsep**: 
  > Volume Spread Analysis (VSA) Stopping Volume & Absorption.

**Potongan Kode Algoritma (Python)**:
```python
def fx_volume_spread_analysis(s):
    """Volume Spread Analysis (VSA) Stopping Volume & Absorption."""
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    rng = h - l
    if rng > 1.5 * atr:
        # Ultra-wide spread down bar closing in the upper half -> Absorption of selling
        if (c - l) / rng >= 0.55 and c > o:
            return 0.80
        # Ultra-wide spread up bar closing in the lower half -> Buying climax / Absorption of buying
        if (h - c) / rng >= 0.55 and c < o:
            return -0.80
    return 0.0
```

**Catatan Analisis & Potensi Titik Lemah (Audit Checklist)**:
- **Volume Confirmation**: Memeriksa lonjakan volume di atas rata-rata. *Catatan*: Di pasar Forex MT5, volume adalah *tick volume*, bukan *real trade volume* seperti di Binance.
- **Rekomendasi Optimalisasi**: Terapkan filter sesi likuiditas tinggi (London & NY) serta pastikan trailing stop aktif saat floating profit mencapai $\ge 1.0\times$ ATR.

---

