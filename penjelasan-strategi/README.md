# Indeks Dokumentasi & Audit Teknis Strategi - Strategy Arena

Folder ini berisi blueprint arsitektur, spesifikasi algoritmik, formula matematis, serta **Audit Kode & Temuan Bug** untuk seluruh strategi trading di Strategy Arena & Copy-Trade Engine.

Seluruh berkas diformat dengan standar quant trading agar siap digunakan langsung oleh developer maupun agent AI (**Claude Opus 3.5**, **GPT**, **Astra**) untuk pengecekan logika dan pengembangan lanjutan.

---

## 🌟 Dokumen Blueprint Strategi Baru (MC-FIBO)

* 📙 [**Momentum Candle Fibonacci Retest (`xauusd-momentum-candle-fibonacci.md`)**](./xauusd-momentum-candle-fibonacci.md)
  * *Blueprint desain target untuk `XAUUSD`, Eksekusi `M15`, Filter High-Probability `M30` & `H1`, Sesi Asia & NY, Penarikan Fibonacci Fleksibel (Wick vs Body). Versi awal kode sudah masuk sebagai `#84 fx_xauusd_mc_fibo` — lihat temuan bug kritis pada file auditnya.*

---

## 📘 Rangkuman Temuan Audit Kritis (89 Strategi Terdaftar)

Berdasarkan inspeksi langsung terhadap kode `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py`, berikut temuan penting yang perlu segera dibenahi:

1. **Strategi dengan Bug Kode Kritis (Harus Diperbaiki)**:
   * **`supertrend` (#18)**: Memiliki *Dead/Unreachable Code* pada baris 213 yang memblokir sinyal BUY agar tidak pernah tereksekusi, ditambah band tidak stateful.
   * **`vwap_trend` (#25)**: Bug *Double Negation* (`-trend_stack` saat `c < ema50`) yang membuat bot **ENTRY BUY di tengah tren turun** dan sama sekali tidak memakai VWAP.
   * **`wicks_reject` (#53)**: Sinyal terbalik 100%! Sumbu atas (*Shooting Star*) justru menghasilkan BUY (`+0.6`), sedangkan sumbu bawah (*Hammer*) menghasilkan SELL (`-0.6`).
   * **`delta_flow` (#52)**: Perkalian tanda `(-0.35) * (-1)` di bawah EMA21 mengakibatkan candle bearish besar memicu posisi BUY.
   * **`tr_break` (#47)**: Docstring menyebut lawan impuls (*Fade*), tetapi kode malah mengikuti warna candle (*Follow*).
   * **`fx_ict_fair_value_gap` (#80)**: Salah indeks bar FVG (membandingkan `i-2` dengan `i-1` bukan `i-3` dengan `i-1`), menyebabkannya selalu `0.00%` (0 transaksi).
   * **`fx_xauusd_mc_fibo` (#84)**: Masih me-return `0.75` langsung saat *impuls* tanpa menunggu harga retest ke Fibo `[0.236..0.786]`, mengevaluasi bar `M15` sebelum close (`ix.size >= 7` -> fire 1x/menit), dan window `H1` terbatas 5 bar (`W=320`).
   * **`macd_div` (#14)**: Window pembanding `[i-25:i-5]` dan `[i-20:i+1]` tumpang tindih 15 bar.
   * **`snr_bounce` (#4)**: Memicu BUY tepat saat candle menjebol ke bawah `S1`, bukan saat memantul naik.
2. **Strategi Duplikat Kembar (Menghasilkan PnL Identik)**:
   * `ict_obs` (#3) == `fractal_break` (#56)
   * `2b_rev` (#37) == `price_action_2b` (#55)
   * `engulfing` (#38) == `paint_bar` (#54) *(ditambah syarat ketat `<`/`>` yang macet di 0.00%)*
   * `value_area` (#46) == `vwap_band` (#24)
   * `mean_sd_band` (#33) == kebalikan `-0.7x` dari `zscore_rev` (#32)
3. **Kendala Data & Engine**:
   * **Volume Forex Acak (`forex_feed.py`)**: Volume bar Forex memakai `random.uniform`, membuat `vol_breakout` (syarat $\ge 2.5\times$ rata-rata volume) nyaris mustahil terpicu di Forex.
   * **Minimum SL Floor 0.35% (`engine.py`)**: Memaksa Stop Loss minimal $\sim 143$ pips pada XAUUSD meskipun sinyal berasal dari bar 1-menit (`M1`).

---

## 📋 Daftar Lengkap Dokumentasi Individu (89 Berkas Markdown)

Klik tautan berkas di bawah untuk membaca bedah detail masing-masing strategi satu per satu:

| No | ID Strategi | Nama Strategi | Kategori | R:R | Lev | Status Audit | Berkas Spesifikasi |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| #1 | `ict_momentum` | **ICT Momentum** | ICT | 1:1.8 | 15x | ⚠️ Catatan Kondisi / Filter | [`01-ict-momentum.md`](./daftar-88-strategi/01-ict-momentum.md) |
| #2 | `ict_fvg` | **ICT Fair Value Gap** | ICT | 1:1.8 | 12x | ⚠️ Catatan Kondisi / Filter | [`02-ict-fvg.md`](./daftar-88-strategi/02-ict-fvg.md) |
| #3 | `ict_obs` | **ICT Order Block Sweep** | ICT | 1:1.8 | 15x | 🚨 Bug / Duplikat / Misnomer | [`03-ict-obs.md`](./daftar-88-strategi/03-ict-obs.md) |
| #4 | `snr_bounce` | **Support Resistance Bounce** | Price action | 1:1.8 | 10x | 🚨 Bug / Duplikat / Misnomer | [`04-snr-bounce.md`](./daftar-88-strategi/04-snr-bounce.md) |
| #5 | `trend_stack` | **EMA Stack 9/21/50** | Trend | 1:2.2 | 10x | ⚠️ Catatan Kondisi / Filter | [`05-trend-stack.md`](./daftar-88-strategi/05-trend-stack.md) |
| #6 | `donchian_55` | **Donchian Turtle 55** | Breakout | 1:2.2 | 10x | ⚠️ Catatan Kondisi / Filter | [`06-donchian-55.md`](./daftar-88-strategi/06-donchian-55.md) |
| #7 | `donchian_20` | **Donchian Breakout 20** | Breakout | 1:2.2 | 10x | ⚠️ Catatan Kondisi / Filter | [`07-donchian-20.md`](./daftar-88-strategi/07-donchian-20.md) |
| #8 | `keltner` | **Keltner Channel Break** | Volatility | 1:1.8 | 12x | ⚠️ Catatan Kondisi / Filter | [`08-keltner.md`](./daftar-88-strategi/08-keltner.md) |
| #9 | `bb_rev` | **Bollinger Fade** | Mean reversion | 1:1.5 | 15x | 🚨 Bug / Duplikat / Misnomer | [`09-bb-rev.md`](./daftar-88-strategi/09-bb-rev.md) |
| #10 | `squeeze` | **Squeeze Release** | Volatility | 1:1.8 | 15x | ⚠️ Catatan Kondisi / Filter | [`10-squeeze.md`](./daftar-88-strategi/10-squeeze.md) |
| #11 | `rsi_30_70` | **RSI Mean Reversion** | Mean reversion | 1:1.5 | 15x | 🚨 Bug / Duplikat / Misnomer | [`11-rsi-30-70.md`](./daftar-88-strategi/11-rsi-30-70.md) |
| #12 | `stoch_cross` | **Stochastic 20/80** | Oscillator | 1:1.5 | 15x | ⚠️ Catatan Kondisi / Filter | [`12-stoch-cross.md`](./daftar-88-strategi/12-stoch-cross.md) |
| #13 | `macd_cross` | **MACD Trend** | Momentum | 1:2.0 | 10x | ⚠️ Catatan Kondisi / Filter | [`13-macd-cross.md`](./daftar-88-strategi/13-macd-cross.md) |
| #14 | `macd_div` | **MACD Divergence** | Momentum | 1:2.0 | 12x | 🚨 Bug / Duplikat / Misnomer | [`14-macd-div.md`](./daftar-88-strategi/14-macd-div.md) |
| #15 | `ema_macd_fast` | **EMA21/50 Golden** | Trend | 1:2.2 | 8x | 🚨 Bug / Duplikat / Misnomer | [`15-ema-macd-fast.md`](./daftar-88-strategi/15-ema-macd-fast.md) |
| #16 | `golden_50_200` | **Golden Cross 50/200** | Trend | 1:2.2 | 5x | ⚠️ Catatan Kondisi / Filter | [`16-golden-50-200.md`](./daftar-88-strategi/16-golden-50-200.md) |
| #17 | `ichimoku` | **Ichimoku Kumo** | Trend | 1:2.2 | 8x | 🚨 Bug / Duplikat / Misnomer | [`17-ichimoku.md`](./daftar-88-strategi/17-ichimoku.md) |
| #18 | `supertrend` | **SuperTrend ATR** | Volatility | 1:1.8 | 10x | 🚨 Bug / Duplikat / Misnomer | [`18-supertrend.md`](./daftar-88-strategi/18-supertrend.md) |
| #19 | `chandelier` | **Chandelier Exit** | Trailing | 1:1.8 | 10x | ⚠️ Catatan Kondisi / Filter | [`19-chandelier.md`](./daftar-88-strategi/19-chandelier.md) |
| #20 | `fib_retrace` | **Fib Retracement 38-62** | Fibonacci | 1:1.8 | 8x | ⚠️ Catatan Kondisi / Filter | [`20-fib-retrace.md`](./daftar-88-strategi/20-fib-retrace.md) |
| #21 | `fib_ext` | **Fib Extension Trend** | Fibonacci | 1:1.8 | 8x | 🚨 Bug / Duplikat / Misnomer | [`21-fib-ext.md`](./daftar-88-strategi/21-fib-ext.md) |
| #22 | `fib_golden_pocket` | **Fib Golden Pocket 61.8** | Fibonacci | 1:1.8 | 10x | ⚠️ Catatan Kondisi / Filter | [`22-fib-golden-pocket.md`](./daftar-88-strategi/22-fib-golden-pocket.md) |
| #23 | `fib_expansion_1618` | **Fib Extension 1.618** | Fibonacci | 1:1.8 | 12x | ⚠️ Catatan Kondisi / Filter | [`23-fib-expansion-1618.md`](./daftar-88-strategi/23-fib-expansion-1618.md) |
| #24 | `vwap_band` | **VWAP Deviation** | Statistik | 1:1.5 | 12x | ⚠️ Catatan Kondisi / Filter | [`24-vwap-band.md`](./daftar-88-strategi/24-vwap-band.md) |
| #25 | `vwap_trend` | **VWAP Trend Follow** | Statistik | 1:1.5 | 10x | 🚨 Bug / Duplikat / Misnomer | [`25-vwap-trend.md`](./daftar-88-strategi/25-vwap-trend.md) |
| #26 | `vol_breakout` | **Volume Breakout** | Breakout | 1:2.2 | 12x | 🚨 Bug / Duplikat / Misnomer | [`26-vol-breakout.md`](./daftar-88-strategi/26-vol-breakout.md) |
| #27 | `vol_target` | **Volatility Trend Filter** | Trend | 1:2.2 | 8x | 🚨 Bug / Duplikat / Misnomer | [`27-vol-target.md`](./daftar-88-strategi/27-vol-target.md) |
| #28 | `adx_trend` | **ADX Strong Trend** | Trend | 1:2.2 | 10x | ⚠️ Catatan Kondisi / Filter | [`28-adx-trend.md`](./daftar-88-strategi/28-adx-trend.md) |
| #29 | `roc_momentum` | **ROC Momentum 12** | Momentum | 1:2.0 | 15x | ⚠️ Catatan Kondisi / Filter | [`29-roc-momentum.md`](./daftar-88-strategi/29-roc-momentum.md) |
| #30 | `hot_momentum` | **Impulse Candle** | Momentum | 1:2.0 | 15x | ⚠️ Catatan Kondisi / Filter | [`30-hot-momentum.md`](./daftar-88-strategi/30-hot-momentum.md) |
| #31 | `momentum_60` | **Multi-Horizon Momentum** | Momentum | 1:2.0 | 12x | ⚠️ Catatan Kondisi / Filter | [`31-momentum-60.md`](./daftar-88-strategi/31-momentum-60.md) |
| #32 | `zscore_rev` | **Z-Score Reversion** | Statistik | 1:1.5 | 20x | ⚠️ Catatan Kondisi / Filter | [`32-zscore-rev.md`](./daftar-88-strategi/32-zscore-rev.md) |
| #33 | `mean_sd_band` | **Mean Deviation Band** | Statistik | 1:1.5 | 15x | 🚨 Bug / Duplikat / Misnomer | [`33-mean-sd-band.md`](./daftar-88-strategi/33-mean-sd-band.md) |
| #34 | `time_session` | **Timezone Session Bias** | Waktu | 1:1.8 | 10x | ⚠️ Catatan Kondisi / Filter | [`34-time-session.md`](./daftar-88-strategi/34-time-session.md) |
| #35 | `time_open` | **Opening Hour Range** | Waktu | 1:1.8 | 12x | 🚨 Bug / Duplikat / Misnomer | [`35-time-open.md`](./daftar-88-strategi/35-time-open.md) |
| #36 | `gap_fill` | **Gap Fill Reversal** | Price action | 1:1.8 | 15x | ⚠️ Catatan Kondisi / Filter | [`36-gap-fill.md`](./daftar-88-strategi/36-gap-fill.md) |
| #37 | `2b_rev` | **2B Reversal** | Price action | 1:1.8 | 10x | 🚨 Bug / Duplikat / Misnomer | [`37-2b-rev.md`](./daftar-88-strategi/37-2b-rev.md) |
| #38 | `engulfing` | **Bullish/Bearish Engulfing** | Price action | 1:1.8 | 15x | 🚨 Bug / Duplikat / Misnomer | [`38-engulfing.md`](./daftar-88-strategi/38-engulfing.md) |
| #39 | `inside_bar` | **Inside Bar Breakout** | Price action | 1:1.8 | 15x | ⚠️ Catatan Kondisi / Filter | [`39-inside-bar.md`](./daftar-88-strategi/39-inside-bar.md) |
| #40 | `swing_break` | **Swing Volume Break** | Price action | 1:1.8 | 10x | ⚠️ Catatan Kondisi / Filter | [`40-swing-break.md`](./daftar-88-strategi/40-swing-break.md) |
| #41 | `vol_trend_sma` | **SMA50/200 Regime** | Trend | 1:2.2 | 6x | 🚨 Bug / Duplikat / Misnomer | [`41-vol-trend-sma.md`](./daftar-88-strategi/41-vol-trend-sma.md) |
| #42 | `ewma_trend` | **EMA200 Trend Bias** | Trend | 1:2.2 | 8x | ⚠️ Catatan Kondisi / Filter | [`42-ewma-trend.md`](./daftar-88-strategi/42-ewma-trend.md) |
| #43 | `price_ema_dev` | **EMA Deviation** | Statistik | 1:1.5 | 12x | ⚠️ Catatan Kondisi / Filter | [`43-price-ema-dev.md`](./daftar-88-strategi/43-price-ema-dev.md) |
| #44 | `price_ema_dev2` | **EMA50 Deviation** | Statistik | 1:1.5 | 15x | ⚠️ Catatan Kondisi / Filter | [`44-price-ema-dev2.md`](./daftar-88-strategi/44-price-ema-dev2.md) |
| #45 | `rotation` | **RSI+MACD Rotation** | Momentum | 1:2.0 | 12x | ⚠️ Catatan Kondisi / Filter | [`45-rotation.md`](./daftar-88-strategi/45-rotation.md) |
| #46 | `value_area` | **Value Area Auction** | Volume profile | 1:1.8 | 10x | 🚨 Bug / Duplikat / Misnomer | [`46-value-area.md`](./daftar-88-strategi/46-value-area.md) |
| #47 | `tr_break` | **Range Expansion Fade** | Volatility | 1:1.8 | 15x | 🚨 Bug / Duplikat / Misnomer | [`47-tr-break.md`](./daftar-88-strategi/47-tr-break.md) |
| #48 | `trend_pullback` | **Trend Pullback EMA9** | Trend | 1:2.2 | 10x | ⚠️ Catatan Kondisi / Filter | [`48-trend-pullback.md`](./daftar-88-strategi/48-trend-pullback.md) |
| #49 | `mean_ma_cross` | **MA Cross Mean** | Trend | 1:2.2 | 8x | 🚨 Bug / Duplikat / Misnomer | [`49-mean-ma-cross.md`](./daftar-88-strategi/49-mean-ma-cross.md) |
| #50 | `rsi2_extreme` | **RSI2 Extreme** | Mean reversion | 1:1.5 | 20x | ⚠️ Catatan Kondisi / Filter | [`50-rsi2-extreme.md`](./daftar-88-strategi/50-rsi2-extreme.md) |
| #51 | `turtle_soup` | **Turtle Soup Sweep** | Struktur | 1:1.8 | 15x | ⚠️ Catatan Kondisi / Filter | [`51-turtle-soup.md`](./daftar-88-strategi/51-turtle-soup.md) |
| #52 | `delta_flow` | **Candle Imbalance** | Order flow | 1:2.0 | 20x | 🚨 Bug / Duplikat / Misnomer | [`52-delta-flow.md`](./daftar-88-strategi/52-delta-flow.md) |
| #53 | `wicks_reject` | **Wick Rejection** | Order flow | 1:2.0 | 15x | 🚨 Bug / Duplikat / Misnomer | [`53-wicks-reject.md`](./daftar-88-strategi/53-wicks-reject.md) |
| #54 | `paint_bar` | **Paint Bar Pattern** | Price action | 1:1.8 | 15x | 🚨 Bug / Duplikat / Misnomer | [`54-paint-bar.md`](./daftar-88-strategi/54-paint-bar.md) |
| #55 | `price_action_2b` | **2B Reversal** | Price action | 1:1.8 | 15x | 🚨 Bug / Duplikat / Misnomer | [`55-price-action-2b.md`](./daftar-88-strategi/55-price-action-2b.md) |
| #56 | `fractal_break` | **Fractal Breakout** | Breakout | 1:2.2 | 12x | 🚨 Bug / Duplikat / Misnomer | [`56-fractal-break.md`](./daftar-88-strategi/56-fractal-break.md) |
| #57 | `fx_lob_alpha` | **London Open Breakout** | Breakout | 1:2.2 | 1x | ✅ Logika Bersih | [`57-fx-lob-alpha.md`](./daftar-88-strategi/57-fx-lob-alpha.md) |
| #58 | `fx_tokyo_fader` | **Asian Range Fader** | Mean reversion | 1:1.5 | 1x | ✅ Logika Bersih | [`58-fx-tokyo-fader.md`](./daftar-88-strategi/58-fx-tokyo-fader.md) |
| #59 | `fx_frankfurt_probe` | **Frankfurt Liquidity Probe** | Order flow | 1:2.0 | 1x | ⚠️ Catatan Kondisi / Filter | [`59-fx-frankfurt-probe.md`](./daftar-88-strategi/59-fx-frankfurt-probe.md) |
| #60 | `fx_ny_reversal` | **New York Fixing Reversal** | Mean reversion | 1:1.5 | 1x | ✅ Logika Bersih | [`60-fx-ny-reversal.md`](./daftar-88-strategi/60-fx-ny-reversal.md) |
| #61 | `fx_sunday_gap` | **Sunday Gap Fill Engine** | Statistik | 1:1.5 | 1x | ⚠️ Catatan Kondisi / Filter | [`61-fx-sunday-gap.md`](./daftar-88-strategi/61-fx-sunday-gap.md) |
| #62 | `fx_aud_nzd_arb` | **Aussie-Kiwi Cointegration** | Statistik | 1:1.5 | 1x | 🚨 Bug / Duplikat / Misnomer | [`62-fx-aud-nzd-arb.md`](./daftar-88-strategi/62-fx-aud-nzd-arb.md) |
| #63 | `fx_triangular_synth` | **Triangular Arbitrage Synth** | Statistik | 1:1.5 | 1x | 🚨 Bug / Duplikat / Misnomer | [`63-fx-triangular-synth.md`](./daftar-88-strategi/63-fx-triangular-synth.md) |
| #64 | `fx_oil_cad_divergence` | **Petro-CAD Divergence** | Trend | 1:2.2 | 1x | 🚨 Bug / Duplikat / Misnomer | [`64-fx-oil-cad-divergence.md`](./daftar-88-strategi/64-fx-oil-cad-divergence.md) |
| #65 | `fx_gold_safehaven_relay` | **Safe-Haven Gold Relay** | Trend | 1:2.2 | 1x | 🚨 Bug / Duplikat / Misnomer | [`65-fx-gold-safehaven-relay.md`](./daftar-88-strategi/65-fx-gold-safehaven-relay.md) |
| #66 | `fx_dragon_momentum` | **The Dragon Momentum Rider** | Momentum | 1:2.0 | 1x | ✅ Logika Bersih | [`66-fx-dragon-momentum.md`](./daftar-88-strategi/66-fx-dragon-momentum.md) |
| #67 | `fx_bb_squeeze` | **BB Squeeze Volatility** | Volatility | 1:1.8 | 1x | ✅ Logika Bersih | [`67-fx-bb-squeeze.md`](./daftar-88-strategi/67-fx-bb-squeeze.md) |
| #68 | `fx_atr_expansion` | **ATR Expansion Breakout** | Breakout | 1:2.2 | 1x | ⚠️ Catatan Kondisi / Filter | [`68-fx-atr-expansion.md`](./daftar-88-strategi/68-fx-atr-expansion.md) |
| #69 | `fx_gold_flash_spike` | **Gold Flash-Spike Reversal** | Oscillator | 1:1.5 | 1x | ⚠️ Catatan Kondisi / Filter | [`69-fx-gold-flash-spike.md`](./daftar-88-strategi/69-fx-gold-flash-spike.md) |
| #70 | `fx_ema_ribbon` | **Multi-TF EMA Ribbon** | Trend | 1:2.2 | 1x | ⚠️ Catatan Kondisi / Filter | [`70-fx-ema-ribbon.md`](./daftar-88-strategi/70-fx-ema-ribbon.md) |
| #71 | `fx_supertrend_trailing` | **SuperTrend Dynamic Trailing** | Trailing | 1:1.8 | 1x | ✅ Logika Bersih | [`71-fx-supertrend-trailing.md`](./daftar-88-strategi/71-fx-supertrend-trailing.md) |
| #72 | `fx_ichimoku_quantum` | **Ichimoku Kumo Quantum** | Trend | 1:2.2 | 1x | ⚠️ Catatan Kondisi / Filter | [`72-fx-ichimoku-quantum.md`](./daftar-88-strategi/72-fx-ichimoku-quantum.md) |
| #73 | `fx_heikin_ashi_smooth` | **Heikin-Ashi Trend Continuum** | Trend | 1:2.2 | 1x | 🚨 Bug / Duplikat / Misnomer | [`73-fx-heikin-ashi-smooth.md`](./daftar-88-strategi/73-fx-heikin-ashi-smooth.md) |
| #74 | `fx_hedging_grid` | **Dynamic Hedging Grid** | Struktur | 1:1.8 | 1x | ✅ Logika Bersih | [`74-fx-hedging-grid.md`](./daftar-88-strategi/74-fx-hedging-grid.md) |
| #75 | `fx_camarilla_fader` | **Camarilla Multi-Confluence** | Struktur | 1:1.8 | 1x | 🚨 Bug / Duplikat / Misnomer | [`75-fx-camarilla-fader.md`](./daftar-88-strategi/75-fx-camarilla-fader.md) |
| #76 | `fx_orderflow_sweep` | **Order Flow Liquidity Sweep** | Order flow | 1:2.0 | 1x | ⚠️ Catatan Kondisi / Filter | [`76-fx-orderflow-sweep.md`](./daftar-88-strategi/76-fx-orderflow-sweep.md) |
| #77 | `fx_carry_yield_momentum` | **Synthetic Carry-Trade Yield** | Trend | 1:2.2 | 1x | 🚨 Bug / Duplikat / Misnomer | [`77-fx-carry-yield-momentum.md`](./daftar-88-strategi/77-fx-carry-yield-momentum.md) |
| #78 | `fx_economic_straddle` | **Economic Straddle Breakout** | Breakout | 1:2.2 | 1x | ⚠️ Catatan Kondisi / Filter | [`78-fx-economic-straddle.md`](./daftar-88-strategi/78-fx-economic-straddle.md) |
| #79 | `fx_smc_orderblock` | **SMC Order Block Mitigation** | ICT | 1:1.8 | 1x | ✅ Logika Bersih | [`79-fx-smc-orderblock.md`](./daftar-88-strategi/79-fx-smc-orderblock.md) |
| #80 | `fx_ict_fair_value_gap` | **ICT Fair Value Gap (FVG)** | ICT | 1:1.8 | 1x | 🚨 Bug / Duplikat / Misnomer | [`80-fx-ict-fair-value-gap.md`](./daftar-88-strategi/80-fx-ict-fair-value-gap.md) |
| #81 | `fx_smc_liquidity_sweep` | **SMC Liquidity Sweep & BOS** | Struktur | 1:1.8 | 1x | ✅ Logika Bersih | [`81-fx-smc-liquidity-sweep.md`](./daftar-88-strategi/81-fx-smc-liquidity-sweep.md) |
| #82 | `fx_ict_optimal_trade_entry` | **ICT Optimal Trade Entry** | ICT | 1:1.8 | 1x | ⚠️ Catatan Kondisi / Filter | [`82-fx-ict-optimal-trade-entry.md`](./daftar-88-strategi/82-fx-ict-optimal-trade-entry.md) |
| #83 | `fx_momentum_candle_burst` | **Momentum Candle Expansion** | Momentum | 1:2.0 | 1x | ⚠️ Catatan Kondisi / Filter | [`83-fx-momentum-candle-burst.md`](./daftar-88-strategi/83-fx-momentum-candle-burst.md) |
| #84 | `fx_xauusd_mc_fibo` | **XAUUSD MC-FIBO Retest** | Fibonacci | 1:1.8 | 1x | 🚨 Bug / Duplikat / Misnomer | [`84-fx-xauusd-mc-fibo.md`](./daftar-88-strategi/84-fx-xauusd-mc-fibo.md) |
| #85 | `fx_three_line_strike` | **Three Line Strike Pattern** | Price action | 1:1.8 | 1x | ⚠️ Catatan Kondisi / Filter | [`85-fx-three-line-strike.md`](./daftar-88-strategi/85-fx-three-line-strike.md) |
| #86 | `fx_pinbar_liquidity_reject` | **Pin Bar Liquidity Rejection** | Price action | 1:1.8 | 1x | ✅ Logika Bersih | [`86-fx-pinbar-liquidity-reject.md`](./daftar-88-strategi/86-fx-pinbar-liquidity-reject.md) |
| #87 | `fx_london_ny_overlap` | **London-NY Overlap Scalper** | Breakout | 1:2.2 | 1x | ✅ Logika Bersih | [`87-fx-london-ny-overlap.md`](./daftar-88-strategi/87-fx-london-ny-overlap.md) |
| #88 | `fx_supply_demand_zone` | **Supply & Demand Zone** | Struktur | 1:1.8 | 1x | ⚠️ Catatan Kondisi / Filter | [`88-fx-supply-demand-zone.md`](./daftar-88-strategi/88-fx-supply-demand-zone.md) |
| #89 | `fx_volume_spread_analysis` | **Volume Spread Analysis (VSA)** | Order flow | 1:2.0 | 1x | 🚨 Bug / Duplikat / Misnomer | [`89-fx-volume-spread-analysis.md`](./daftar-88-strategi/89-fx-volume-spread-analysis.md) |
