# Dokumentasi Arsitektur & Spesifikasi 89 Strategi Arena

Direktori ini berisi **spesifikasi lengkap seluruh 89 strategi** yang berjalan secara universal pada **Spot**, **Futures**, dan **Forex MT5** di Strategy Arena (`server/strategies.py` + `server/engine.py`), termasuk hasil audit teknis yang sudah **diperbaiki dan diverifikasi** agar siap dikaji maupun dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**).

---

## Dokumen Spesial Strategi Baru (#84)
* [**XAUUSD Momentum Candle + Fibonacci Retest (MC-FIBO `M15` + `M30/H1`)**](./daftar-88-strategi/84-xauusd-mc-fibo.md) — Spesifikasi multi-timeframe *Body/Wick Anchor Fibonacci* (`1.0` SL ke `-0.27` TP via `custom_sl_tp`, strictly `XAUUSD` di mode Forex pada sesi Asia `00–07 UTC` & NY `12–21 UTC`, dan universal di Spot/Futures).

---

## Ringkasan Temuan Audit Kritis & Status Perbaikan (*POST-FIX STATUS*)

Seluruh temuan bug kritis dari audit awal telah diperbaiki pada kode produksi (`server/strategies.py`, `server/engine.py`, `server/forex_feed.py`, `server/bars.py`, `server/indicators.py`, `server/mt5_bridge_server.py`, dan database Postgres `arena`):

1. **Penghapusan Total Prefiks `fx_` & Pembukaan Leverage Universal**:
   Seluruh 33 strategi `#57–#89` kini resmi berstatus **universal** tanpa prefiks `fx_` (termasuk migrasi in-place tanpa reset pada Postgres `accounts`, `positions`, `trades`, `signals`, `equity_curve`, `events`, dan kompatibilitas alias pada API `/api/strategy/fx_*`). Seluruh 89 strategi kini memakai `DEFAULT_LEVERAGE` Futures (`5x–20x`) sambil menjaga lot sizing direct `1x` (1.5% risiko) di mode Forex MT5.
2. **Perbaikan 8 Bug Kritis Sinyal Terbalik, Overlap & Skala**:
   * [`delta_flow`](./daftar-88-strategi/52-delta-flow.md) (#52), [`wicks_reject`](./daftar-88-strategi/53-wicks-reject.md) (#53), [`vwap_trend`](./daftar-88-strategi/25-vwap-trend.md) (#25), [`tr_break`](./daftar-88-strategi/47-tr-break.md) (#47), dan [`snr_bounce`](./daftar-88-strategi/04-snr-bounce.md) (#04): Seluruh logika terbalik (*double-negation*, breakout-vs-bounce, sign inversion) kini telah diperbaiki.
   * [`supertrend`](./daftar-88-strategi/18-supertrend.md) (#18) & [`supertrend_trailing`](./daftar-88-strategi/71-supertrend-trailing.md) (#71): Kini menghitung band SuperTrend secara **stateful** dan menghapus dead code.
   * [`macd_div`](./daftar-88-strategi/14-macd-div.md) (#14): Jendela divergensinya kini benar-benar terpisah (*disjoint* `[i-30:i-14]` vs `[i-14:i+1]`).
   * [`vol_target`](./daftar-88-strategi/27-vol-target.md) (#27): Ambang `ATR/Close` diturunkan dari `0.15%` menjadi rentang sehat `0.03% – 1.20%` (`0.0003..0.012`) agar kompatibel dengan pair Forex & komoditas.
3. **Deduplikasi 5 Pasang Strategi Kembar**:
   [`ict_obs`](./daftar-88-strategi/03-ict-obs.md) (`ict_orderblock_sweep`), [`value_area`](./daftar-88-strategi/46-value-area.md) (`12-bin POC/VAH/VAL`), [`2b_rev`](./daftar-88-strategi/37-2b-rev.md) (`2B Close Reversal`), [`paint_bar`](./daftar-88-strategi/54-paint-bar.md) (`3-Bar Key Reversal`), dan [`mean_sd_band`](./daftar-88-strategi/33-mean-sd-band.md) (`Median/MAD`) kini memiliki algoritma independen.
4. **Perbaikan Strategi SMC/Price-Action/FVG & Multi-Bar Lookback**:
   [`ict_fair_value_gap`](./daftar-88-strategi/80-ict-fair-value-gap.md) (#80), [`smc_orderblock`](./daftar-88-strategi/79-smc-orderblock.md) (#79), [`supply_demand_zone`](./daftar-88-strategi/88-supply-demand-zone.md) (#88), [`three_line_strike`](./daftar-88-strategi/85-three-line-strike.md) (#85), [`engulfing`](./daftar-88-strategi/38-engulfing.md) (#38), [`camarilla_fader`](./daftar-88-strategi/75-camarilla-fader.md) (#75), [`heikin_ashi_smooth`](./daftar-88-strategi/73-heikin-ashi-smooth.md) (#73), [`time_open`](./daftar-88-strategi/35-time-open.md) (#35), dan [`volume_spread_analysis`](./daftar-88-strategi/89-volume-spread-analysis.md) (#89) telah ditulis ulang agar memproses struktur multi-bar, toleransi ATR, dan volume secara valid.
5. **Infrastruktur Data 1440-Bar M1 + Volume MT5 Riil + Adaptif `0.10%` Forex SL Floor**:
   * `BarRing.cap` dan `indicators.W` ditingkatkan dari `240` menjadi **`1440` bar M1 (24 jam)** yang di-seed riil dari MT5 Bridge (`/fetch_data_pos?num_bars=1440` + `tick_volume` asli) serta Binance REST terpaginasi (`limit=1440`), dengan komputasi indikator terakselerasi `sliding_window_view`.
   * Volume live di `forex_feed.py` kini hanya bertambah saat kuotasi Bid/Ask MT5 benar-benar berubah (`qty = 1.0`, bebas `random.uniform`).
   * `engine._resolve_stops()` menurunkan batas minimum Stop Loss di mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** sambil menjaga floor `0.35%` untuk Spot & Futures serta mendukung override presisi `custom_sl_tp`.

---

## Indeks Lengkap 89 Strategi (Klik Nama/ID untuk Detail Arsitektur & Kode)

| No | ID Strategi (Link Detail) | Nama Strategi | Kategori | R:R | Futures Lev | Status Implementasi |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `#01` | [`ict_momentum`](./daftar-88-strategi/01-ict-momentum.md) | **ICT Momentum** | `ICT` | `1.8R` | `15x` | ✅ Aktif |
| `#02` | [`ict_fvg`](./daftar-88-strategi/02-ict-fvg.md) | **ICT Fair Value Gap** | `ICT` | `1.8R` | `12x` | ✅ Aktif |
| `#03` | [`ict_obs`](./daftar-88-strategi/03-ict-obs.md) | **ICT Order Block Sweep** | `ICT` | `1.8R` | `15x` | ✅ Diperbaiki & Aktif |
| `#04` | [`snr_bounce`](./daftar-88-strategi/04-snr-bounce.md) | **Support Resistance Bounce** | `Price action` | `1.8R` | `10x` | ✅ Diperbaiki & Aktif |
| `#05` | [`trend_stack`](./daftar-88-strategi/05-trend-stack.md) | **EMA Stack 9/21/50** | `Trend` | `2.2R` | `10x` | ✅ Aktif |
| `#06` | [`donchian_55`](./daftar-88-strategi/06-donchian-55.md) | **Donchian Turtle 55** | `Breakout` | `2.2R` | `10x` | ✅ Aktif |
| `#07` | [`donchian_20`](./daftar-88-strategi/07-donchian-20.md) | **Donchian Breakout 20** | `Breakout` | `2.2R` | `10x` | ✅ Aktif |
| `#08` | [`keltner`](./daftar-88-strategi/08-keltner.md) | **Keltner Channel Break** | `Volatility` | `1.8R` | `12x` | ✅ Aktif |
| `#09` | [`bb_rev`](./daftar-88-strategi/09-bb-rev.md) | **Bollinger Fade** | `Mean reversion` | `1.5R` | `15x` | ✅ Aktif |
| `#10` | [`squeeze`](./daftar-88-strategi/10-squeeze.md) | **Squeeze Release** | `Volatility` | `1.8R` | `15x` | ✅ Aktif |
| `#11` | [`rsi_30_70`](./daftar-88-strategi/11-rsi-30-70.md) | **RSI Mean Reversion** | `Mean reversion` | `1.5R` | `15x` | ⚠️ Aktif (Catatan Desain Minor) |
| `#12` | [`stoch_cross`](./daftar-88-strategi/12-stoch-cross.md) | **Stochastic 20/80** | `Oscillator` | `1.5R` | `15x` | ✅ Aktif |
| `#13` | [`macd_cross`](./daftar-88-strategi/13-macd-cross.md) | **MACD Trend** | `Momentum` | `2.0R` | `10x` | ✅ Aktif |
| `#14` | [`macd_div`](./daftar-88-strategi/14-macd-div.md) | **MACD Divergence** | `Momentum` | `2.0R` | `12x` | ✅ Diperbaiki & Aktif |
| `#15` | [`ema_macd_fast`](./daftar-88-strategi/15-ema-macd-fast.md) | **EMA21/50 Golden** | `Trend` | `2.2R` | `8x` | ✅ Aktif |
| `#16` | [`golden_50_200`](./daftar-88-strategi/16-golden-50-200.md) | **Golden Cross 50/200** | `Trend` | `2.2R` | `5x` | ✅ Aktif |
| `#17` | [`ichimoku`](./daftar-88-strategi/17-ichimoku.md) | **Ichimoku Kumo** | `Trend` | `2.2R` | `8x` | ⚠️ Aktif (Catatan Desain Minor) |
| `#18` | [`supertrend`](./daftar-88-strategi/18-supertrend.md) | **SuperTrend ATR** | `Volatility` | `1.8R` | `10x` | ✅ Diperbaiki & Aktif |
| `#19` | [`chandelier`](./daftar-88-strategi/19-chandelier.md) | **Chandelier Exit** | `Trailing` | `1.8R` | `10x` | ✅ Aktif |
| `#20` | [`fib_retrace`](./daftar-88-strategi/20-fib-retrace.md) | **Fib Retracement 38-62** | `Fibonacci` | `1.8R` | `8x` | ⚠️ Aktif (Catatan Desain Minor) |
| `#21` | [`fib_ext`](./daftar-88-strategi/21-fib-ext.md) | **Fib Extension Trend** | `Fibonacci` | `1.8R` | `8x` | ⚠️ Aktif (Catatan Desain Minor) |
| `#22` | [`fib_golden_pocket`](./daftar-88-strategi/22-fib-golden-pocket.md) | **Fib Golden Pocket 61.8** | `Fibonacci` | `1.8R` | `10x` | ✅ Aktif |
| `#23` | [`fib_expansion_1618`](./daftar-88-strategi/23-fib-expansion-1618.md) | **Fib Extension 1.618** | `Fibonacci` | `1.8R` | `12x` | ✅ Aktif |
| `#24` | [`vwap_band`](./daftar-88-strategi/24-vwap-band.md) | **VWAP Deviation** | `Statistik` | `1.5R` | `12x` | ✅ Volume MT5 Riil |
| `#25` | [`vwap_trend`](./daftar-88-strategi/25-vwap-trend.md) | **VWAP Trend Follow** | `Statistik` | `1.5R` | `10x` | ✅ Diperbaiki & Aktif |
| `#26` | [`vol_breakout`](./daftar-88-strategi/26-vol-breakout.md) | **Volume Breakout** | `Breakout` | `2.2R` | `12x` | ✅ Volume MT5 Riil |
| `#27` | [`vol_target`](./daftar-88-strategi/27-vol-target.md) | **Volatility Trend Filter** | `Trend` | `2.2R` | `8x` | ✅ Diperbaiki & Aktif |
| `#28` | [`adx_trend`](./daftar-88-strategi/28-adx-trend.md) | **ADX Strong Trend** | `Trend` | `2.2R` | `10x` | ✅ Aktif |
| `#29` | [`roc_momentum`](./daftar-88-strategi/29-roc-momentum.md) | **ROC Momentum 12** | `Momentum` | `2.0R` | `15x` | ✅ Aktif |
| `#30` | [`hot_momentum`](./daftar-88-strategi/30-hot-momentum.md) | **Impulse Candle** | `Momentum` | `2.0R` | `15x` | ✅ Aktif |
| `#31` | [`momentum_60`](./daftar-88-strategi/31-momentum-60.md) | **Multi-Horizon Momentum** | `Momentum` | `2.0R` | `12x` | ✅ Aktif |
| `#32` | [`zscore_rev`](./daftar-88-strategi/32-zscore-rev.md) | **Z-Score Reversion** | `Statistik` | `1.5R` | `20x` | ✅ Aktif |
| `#33` | [`mean_sd_band`](./daftar-88-strategi/33-mean-sd-band.md) | **Mean Deviation Band** | `Statistik` | `1.5R` | `15x` | ✅ Diperbaiki & Aktif |
| `#34` | [`time_session`](./daftar-88-strategi/34-time-session.md) | **Timezone Session Bias** | `Waktu` | `1.8R` | `10x` | ✅ Aktif |
| `#35` | [`time_open`](./daftar-88-strategi/35-time-open.md) | **Opening Hour Range** | `Waktu` | `1.8R` | `12x` | ✅ Diperbaiki & Aktif |
| `#36` | [`gap_fill`](./daftar-88-strategi/36-gap-fill.md) | **Gap Fill Reversal** | `Price action` | `1.8R` | `15x` | ✅ Aktif |
| `#37` | [`2b_rev`](./daftar-88-strategi/37-2b-rev.md) | **2B Close Reversal** | `Price action` | `1.8R` | `10x` | ✅ Diperbaiki & Aktif |
| `#38` | [`engulfing`](./daftar-88-strategi/38-engulfing.md) | **Bullish/Bearish Engulfing** | `Price action` | `1.8R` | `15x` | ✅ Diperbaiki & Aktif |
| `#39` | [`inside_bar`](./daftar-88-strategi/39-inside-bar.md) | **Inside Bar Breakout** | `Price action` | `1.8R` | `15x` | ✅ Aktif |
| `#40` | [`swing_break`](./daftar-88-strategi/40-swing-break.md) | **Swing Volume Break** | `Price action` | `1.8R` | `10x` | ✅ Volume MT5 Riil |
| `#41` | [`vol_trend_sma`](./daftar-88-strategi/41-vol-trend-sma.md) | **SMA50/200 Regime** | `Trend` | `2.2R` | `6x` | ✅ Aktif |
| `#42` | [`ewma_trend`](./daftar-88-strategi/42-ewma-trend.md) | **EMA200 Trend Bias** | `Trend` | `2.2R` | `8x` | ✅ Aktif |
| `#43` | [`price_ema_dev`](./daftar-88-strategi/43-price-ema-dev.md) | **EMA Deviation** | `Statistik` | `1.5R` | `12x` | ⚠️ Aktif (Catatan Desain Minor) |
| `#44` | [`price_ema_dev2`](./daftar-88-strategi/44-price-ema-dev2.md) | **EMA50 Deviation** | `Statistik` | `1.5R` | `15x` | ⚠️ Aktif (Catatan Desain Minor) |
| `#45` | [`rotation`](./daftar-88-strategi/45-rotation.md) | **RSI+MACD Rotation** | `Momentum` | `2.0R` | `12x` | ✅ Aktif |
| `#46` | [`value_area`](./daftar-88-strategi/46-value-area.md) | **Value Area Auction** | `Volume profile` | `1.8R` | `10x` | ✅ Diperbaiki & Aktif |
| `#47` | [`tr_break`](./daftar-88-strategi/47-tr-break.md) | **Range Expansion Fade** | `Volatility` | `1.8R` | `15x` | ✅ Diperbaiki & Aktif |
| `#48` | [`trend_pullback`](./daftar-88-strategi/48-trend-pullback.md) | **Trend Pullback EMA9** | `Trend` | `2.2R` | `10x` | ✅ Aktif |
| `#49` | [`mean_ma_cross`](./daftar-88-strategi/49-mean-ma-cross.md) | **MA Cross Mean** | `Trend` | `2.2R` | `8x` | ✅ Aktif |
| `#50` | [`rsi2_extreme`](./daftar-88-strategi/50-rsi2-extreme.md) | **RSI2 Extreme** | `Mean reversion` | `1.5R` | `20x` | ⚠️ Aktif (Catatan Desain Minor) |
| `#51` | [`turtle_soup`](./daftar-88-strategi/51-turtle-soup.md) | **Turtle Soup Sweep** | `Struktur` | `1.8R` | `15x` | ✅ Aktif |
| `#52` | [`delta_flow`](./daftar-88-strategi/52-delta-flow.md) | **Candle Imbalance** | `Order flow` | `2.0R` | `20x` | ✅ Diperbaiki & Aktif |
| `#53` | [`wicks_reject`](./daftar-88-strategi/53-wicks-reject.md) | **Wick Rejection** | `Order flow` | `2.0R` | `15x` | ✅ Diperbaiki & Aktif |
| `#54` | [`paint_bar`](./daftar-88-strategi/54-paint-bar.md) | **Paint Bar Pattern** | `Price action` | `1.8R` | `15x` | ✅ Diperbaiki & Aktif |
| `#55` | [`price_action_2b`](./daftar-88-strategi/55-price-action-2b.md) | **2B Reversal** | `Price action` | `1.8R` | `15x` | ✅ Aktif |
| `#56` | [`fractal_break`](./daftar-88-strategi/56-fractal-break.md) | **Fractal Breakout** | `Breakout` | `2.2R` | `12x` | ✅ Aktif |
| `#57` | [`lob_alpha`](./daftar-88-strategi/57-lob-alpha.md) | **London Open Breakout** | `Breakout` | `2.2R` | `12x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#58` | [`tokyo_fader`](./daftar-88-strategi/58-tokyo-fader.md) | **Asian Range Fader** | `Mean reversion` | `1.5R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#59` | [`frankfurt_probe`](./daftar-88-strategi/59-frankfurt-probe.md) | **Frankfurt Liquidity Probe** | `Order flow` | `2.0R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#60` | [`ny_reversal`](./daftar-88-strategi/60-ny-reversal.md) | **New York Fixing Reversal** | `Mean reversion` | `1.5R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#61` | [`sunday_gap`](./daftar-88-strategi/61-sunday-gap.md) | **Sunday Gap Fill Engine** | `Statistik` | `1.5R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#62` | [`aud_nzd_arb`](./daftar-88-strategi/62-aud-nzd-arb.md) | **Aussie-Kiwi Cointegration** | `Statistik` | `1.5R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#63` | [`triangular_synth`](./daftar-88-strategi/63-triangular-synth.md) | **Triangular Arbitrage Synth** | `Statistik` | `1.5R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#64` | [`oil_cad_divergence`](./daftar-88-strategi/64-oil-cad-divergence.md) | **Petro-CAD Divergence** | `Trend` | `2.2R` | `8x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#65` | [`gold_safehaven_relay`](./daftar-88-strategi/65-gold-safehaven-relay.md) | **Safe-Haven Gold Relay** | `Trend` | `2.2R` | `8x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#66` | [`dragon_momentum`](./daftar-88-strategi/66-dragon-momentum.md) | **The Dragon Momentum Rider** | `Momentum` | `2.0R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#67` | [`bb_squeeze`](./daftar-88-strategi/67-bb-squeeze.md) | **BB Squeeze Volatility** | `Volatility` | `1.8R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#68` | [`atr_expansion`](./daftar-88-strategi/68-atr-expansion.md) | **ATR Expansion Breakout** | `Breakout` | `2.2R` | `12x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#69` | [`gold_flash_spike`](./daftar-88-strategi/69-gold-flash-spike.md) | **Gold Flash-Spike Reversal** | `Oscillator` | `1.5R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#70` | [`ema_ribbon`](./daftar-88-strategi/70-ema-ribbon.md) | **Multi-TF EMA Ribbon** | `Trend` | `2.2R` | `8x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#71` | [`supertrend_trailing`](./daftar-88-strategi/71-supertrend-trailing.md) | **SuperTrend Dynamic Trailing** | `Trailing` | `1.8R` | `10x` | ✅ Diperbaiki & Aktif |
| `#72` | [`ichimoku_quantum`](./daftar-88-strategi/72-ichimoku-quantum.md) | **Ichimoku Kumo Quantum** | `Trend` | `2.2R` | `8x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#73` | [`heikin_ashi_smooth`](./daftar-88-strategi/73-heikin-ashi-smooth.md) | **Heikin-Ashi Trend Continuum** | `Trend` | `2.2R` | `8x` | ✅ Diperbaiki & Aktif |
| `#74` | [`hedging_grid`](./daftar-88-strategi/74-hedging-grid.md) | **Dynamic Hedging Grid** | `Struktur` | `1.8R` | `10x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#75` | [`camarilla_fader`](./daftar-88-strategi/75-camarilla-fader.md) | **Camarilla Multi-Confluence** | `Struktur` | `1.8R` | `12x` | ✅ Diperbaiki & Aktif |
| `#76` | [`orderflow_sweep`](./daftar-88-strategi/76-orderflow-sweep.md) | **Order Flow Liquidity Sweep** | `Order flow` | `2.0R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#77` | [`carry_yield_momentum`](./daftar-88-strategi/77-carry-yield-momentum.md) | **Synthetic Carry-Trade Yield** | `Trend` | `2.2R` | `6x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#78` | [`economic_straddle`](./daftar-88-strategi/78-economic-straddle.md) | **Economic Straddle Breakout** | `Breakout` | `2.2R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#79` | [`smc_orderblock`](./daftar-88-strategi/79-smc-orderblock.md) | **SMC Order Block Mitigation** | `ICT` | `1.8R` | `15x` | ✅ Diperbaiki & Aktif |
| `#80` | [`ict_fair_value_gap`](./daftar-88-strategi/80-ict-fair-value-gap.md) | **ICT Fair Value Gap (FVG)** | `ICT` | `1.8R` | `12x` | ✅ Diperbaiki & Aktif |
| `#81` | [`smc_liquidity_sweep`](./daftar-88-strategi/81-smc-liquidity-sweep.md) | **SMC Liquidity Sweep & BOS** | `Struktur` | `1.8R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#82` | [`ict_optimal_trade_entry`](./daftar-88-strategi/82-ict-optimal-trade-entry.md) | **ICT Optimal Trade Entry** | `ICT` | `1.8R` | `12x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#83` | [`momentum_candle_burst`](./daftar-88-strategi/83-momentum-candle-burst.md) | **Momentum Candle Expansion** | `Momentum` | `2.0R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#84` | [`xauusd_mc_fibo`](./daftar-88-strategi/84-xauusd-mc-fibo.md) | **XAUUSD MC-FIBO Retest** | `Fibonacci` | `1.8R` | `10x` | ✅ Aktif (`XAUUSD` Forex / Universal Crypto) |
| `#85` | [`three_line_strike`](./daftar-88-strategi/85-three-line-strike.md) | **Three Line Strike Pattern** | `Price action` | `1.8R` | `15x` | ✅ Diperbaiki & Aktif |
| `#86` | [`pinbar_liquidity_reject`](./daftar-88-strategi/86-pinbar-liquidity-reject.md) | **Pin Bar Liquidity Rejection** | `Price action` | `1.8R` | `15x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#87` | [`london_ny_overlap`](./daftar-88-strategi/87-london-ny-overlap.md) | **London-NY Overlap Scalper** | `Breakout` | `2.2R` | `12x` | ✅ Universal (Ex-FX + Leverage Unlocked) |
| `#88` | [`supply_demand_zone`](./daftar-88-strategi/88-supply-demand-zone.md) | **Supply & Demand Zone** | `Struktur` | `1.8R` | `12x` | ✅ Diperbaiki & Aktif |
| `#89` | [`volume_spread_analysis`](./daftar-88-strategi/89-volume-spread-analysis.md) | **Volume Spread Analysis (VSA)** | `Order flow` | `2.0R` | `15x` | ✅ Diperbaiki & Aktif |
