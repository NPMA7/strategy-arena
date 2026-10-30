// Strategy Archetypes classification and rule descriptions for Strategy Arena

export const STRATEGY_CATEGORIES = {
  // Institutional / Smart Money
  ict: 'Institutional',
  ict_silver_bullet: 'Institutional',
  order_block: 'Institutional',
  liquidity_sweep: 'Institutional',
  fair_value_gap: 'Institutional',
  market_structure: 'Institutional',
  ict_fv_gap: 'Institutional',

  // Trend Following
  turtle: 'Trend Following',
  turtle_soup: 'Trend Following',
  supertrend: 'Trend Following',
  ema_cross_fast: 'Trend Following',
  ema_cross_slow: 'Trend Following',
  macd_trend: 'Trend Following',
  adx_trend: 'Trend Following',
  parabolic_sar: 'Trend Following',
  donchian_breakout: 'Trend Following',
  aroon_trend: 'Trend Following',
  keltner_trend: 'Trend Following',
  ichimoku_cloud: 'Trend Following',
  ichimoku_kumo: 'Trend Following',
  golden_cross: 'Trend Following',

  // Momentum / Breakout
  momentum_surge: 'Momentum',
  rsi_momentum: 'Momentum',
  stochastic_momentum: 'Momentum',
  volume_breakout: 'Momentum',
  vol_breakout: 'Momentum',
  range_breakout: 'Momentum',
  atr_breakout: 'Momentum',
  volatility_squeeze: 'Momentum',
  high_tight_flag: 'Momentum',
  cup_and_handle: 'Momentum',
  impulse_candle: 'Momentum',
  hot_momentum: 'Momentum',

  // Mean Reversion / Oscillators
  bollinger_reversal: 'Mean Reversion',
  rsi_oversold: 'Mean Reversion',
  cci_reversal: 'Mean Reversion',
  mfi_divergence: 'Mean Reversion',
  vwap_mean_reversion: 'Mean Reversion',
  kdj_oscillator: 'Mean Reversion',
  williams_r: 'Mean Reversion',
  fisher_transform: 'Mean Reversion',
  rsi2_extreme: 'Mean Reversion',
  z_score: 'Mean Reversion',

  // Quantitative / Price Action / Volume / Fibonacci
  engulfing: 'Price Action',
  snr_bounce: 'Price Action',
  gap_fill: 'Price Action',
  paint_bar: 'Quantitative',
  fib_retrace: 'Fibonacci',
  fib_ext: 'Fibonacci',
  fib_golden_pocket: 'Fibonacci',
  fib_expansion_1618: 'Fibonacci',
  fibonacci_retracement: 'Fibonacci',
};

export const RULE_NOTES = {
  ICT: 'Membaca jejak likuiditas institusional: sapuan, order block, fair value gap.',
  Institutional: 'Membaca jejak likuiditas institusional: sapuan, order block, fair value gap.',
  Fibonacci: 'Entry pada retracement 38–62% dari swing terakhir, golden pocket 61.8%, searah tren.',
  Fibonaci: 'Entry pada retracement 38–62% dari swing terakhir, golden pocket 61.8%, searah tren.',
  Trend: 'Mengikuti arah tren utama; hanya masuk saat struktur searah.',
  'Trend Following': 'Mengikuti arah tren utama; hanya masuk saat struktur searah.',
  Breakout: 'Masuk saat harga keluar dari rentang; keluar saat rentang pecah balik.',
  'Mean reversion': 'Melawan gerak berlebih, kembali ke rata-rata.',
  'Mean Reversion': 'Melawan gerak berlebih, kembali ke rata-rata.',
  Momentum: 'Mengikuti dorongan harga kuat dengan filter volume.',
  'Order flow': 'Mendeteksi akumulasi/distribusi di level mikro.',
  Oscillator: 'Sinyal oversold/overbought dengan konfirmasi multi-timeframe.',
  'Price action': 'Pola candlestick murni dan level support/resistance kunci.',
  'Price Action': 'Pola candlestick murni dan level support/resistance kunci.',
  Statistik: 'Deviasi standar dan Z-score dari rata-rata bergerak.',
  Struktur: 'Market structure break (BOS) dan change of character (CHoCH).',
  Trailing: 'Menglocking profit bertahap mengikuti pergerakan tren.',
  Volatility: 'Ekspansi volatilitas Bollinger/Keltner channel.',
  'Volume profile': 'Reaksi harga terhadap Point of Control (POC) dan Value Area.',
  Quantitative: 'Model kuantitatif berbasis deviasi statistik dan momentum volume.',
  Waktu: 'Sesi pembukaan London/New York dan bias waktu.'
};

export function getStrategyCategory(id) {
  if (!id) return 'Quantitative';
  if (STRATEGY_CATEGORIES[id]) return STRATEGY_CATEGORIES[id];
  const lower = id.toLowerCase();
  if (lower.includes('fib')) return 'Fibonacci';
  if (lower.includes('ict') || lower.includes('order') || lower.includes('block') || lower.includes('fvg')) return 'ICT';
  if (lower.includes('trend') || lower.includes('turtle') || lower.includes('ema') || lower.includes('ichimoku') || lower.includes('golden')) return 'Trend';
  if (lower.includes('break') || lower.includes('mom') || lower.includes('surge') || lower.includes('impulse')) return 'Momentum';
  if (lower.includes('rev') || lower.includes('boll') || lower.includes('rsi') || lower.includes('osc') || lower.includes('extreme') || lower.includes('z_score')) return 'Mean reversion';
  if (lower.includes('snr') || lower.includes('engulf') || lower.includes('candle') || lower.includes('gap')) return 'Price action';
  return 'Quantitative';
}

export function getRuleText(strategy) {
  if (!strategy) return 'Pilih strategi di papan peringkat.';
  const fam = strategy.family || getStrategyCategory(strategy.id);
  const note = RULE_NOTES[fam] || RULE_NOTES[strategy.family] || 'Aturan kuantitatif otomatis berbasis sinyal teknikal.';
  if (strategy.mode === 'forex' || (strategy.id && strategy.id.startsWith('fx_'))) {
    return `${note} Modal $1.000 · Alokasi maks 20% ($200) per pair · Hingga 5 pair simultan · Spread Riil MT5 Headway · Tanpa Biaya Funding (Non-Crypto).`;
  }
  const lev = strategy.leverage || 1;
  const isFutures = strategy.mode === 'futures';
  const levText = isFutures ? `leverage ${lev}x · funding 0.01%/8j` : 'tanpa leverage (1x)';
  return `${note} Modal $1.000 · alokasi maks 20% ($200) per pair · hingga 5 pair simultan · ${levText} · fee 0.05%.`;
}
