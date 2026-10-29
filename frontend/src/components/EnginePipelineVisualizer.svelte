<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD } from '../lib/formatters.js';

  // Live prices from Binance WebSocket (with sensible fallbacks)
  let btcPrice = $derived(arena.prices['BTCUSDT']?.price ?? 67840);
  let ethPrice = $derived(arena.prices['ETHUSDT']?.price ?? 3485);
  let solPrice = $derived(arena.prices['SOLUSDT']?.price ?? 182.5);
  let bnbPrice = $derived(arena.prices['BNBUSDT']?.price ?? 594.2);

  function goTo(path) {
    arena.navigate(path);
  }
</script>

<div class="pipeline-panel">
  <!-- Header Bar -->
  <div class="panel-header">
    <div class="header-left">
      <span class="live-dot"></span>
      <span class="header-title mono">DIAGRAM ARSITEKTUR STRATEGY ARENA</span>
    </div>
    <div class="header-badges">
      <span class="mono badge-live">WS: CONNECTED</span>
      <span class="mono badge-latency">&lt; 5ms MTM</span>
    </div>
  </div>

  <div class="pipeline-flow">
    <!-- STAGE 01: MARKET INGESTION -->
    <div class="flow-stage stage-ingest">
      <div class="stage-tag-bar">
        <span class="stage-num mono">TAHAP 01</span>
        <span class="stage-label">MARKET INGESTION LAYER</span>
        <span class="stage-badge mono">BINANCE WS</span>
      </div>

      <div class="stage-body">
        <p class="stage-desc">
          Menerima data tick harga dan orderbook real-time dari <strong>100++ Pair Likuid USDT</strong> di Binance tanpa perantara.
        </p>

        <!-- Live Ticker Tapes -->
        <div class="ticker-pills">
          <div class="ticker-chip">
            <span class="t-sym mono">BTC/USDT</span>
            <span class="t-val mono">${formatUSD(btcPrice).replace('$', '')}</span>
          </div>
          <div class="ticker-chip">
            <span class="t-sym mono">ETH/USDT</span>
            <span class="t-val mono">${formatUSD(ethPrice).replace('$', '')}</span>
          </div>
          <div class="ticker-chip">
            <span class="t-sym mono">SOL/USDT</span>
            <span class="t-val mono">${formatUSD(solPrice).replace('$', '')}</span>
          </div>
          <div class="ticker-chip">
            <span class="t-sym mono">BNB/USDT</span>
            <span class="t-val mono">${formatUSD(bnbPrice).replace('$', '')}</span>
          </div>
          <div class="ticker-chip more-chip mono">
            +96 PAIRS MORE
          </div>
        </div>
      </div>
    </div>

    <!-- Animated Connector Arrow 1 -->
    <div class="pipeline-connector">
      <div class="connector-line">
        <span class="pulse-beam"></span>
      </div>
      <div class="connector-tag mono">
        <span>TICK DATA STREAM (1000ms / Cycle)</span>
        <span class="arrow-icon">▼</span>
      </div>
    </div>

    <!-- STAGE 02: QUANT ENGINE & ALGO WORKER POOL -->
    <div class="flow-stage stage-core">
      <div class="stage-tag-bar core-bar">
        <span class="stage-num mono core-num">TAHAP 02</span>
        <span class="stage-label">QUANT ENGINE & 50++ ALGO WORKERS</span>
        <span class="stage-badge core-badge mono">EVALUASI PARALEL</span>
      </div>

      <div class="stage-body">
        <p class="stage-desc">
          Setiap pergerakan harga dianalisis secara independen oleh model kuantitatif tanpa emosi, terbagi dalam 4 kelompok strategi:
        </p>

        <div class="archetype-grid">
          <div class="arch-card">
            <div class="arch-head">
              <span class="arch-name">Trend Following</span>
              <span class="arch-count mono">15 Algos</span>
            </div>
            <div class="arch-sub mono">EMA · SuperTrend · MACD</div>
          </div>

          <div class="arch-card">
            <div class="arch-head">
              <span class="arch-name">Volatility Breakout</span>
              <span class="arch-count mono">14 Algos</span>
            </div>
            <div class="arch-sub mono">Bollinger · ATR · Donchian</div>
          </div>

          <div class="arch-card">
            <div class="arch-head">
              <span class="arch-name">Mean Reversion</span>
              <span class="arch-count mono">12 Algos</span>
            </div>
            <div class="arch-sub mono">RSI 14 · Z-Score · Extrema</div>
          </div>

          <div class="arch-card">
            <div class="arch-head">
              <span class="arch-name">Grid & Scalping</span>
              <span class="arch-count mono">12 Algos</span>
            </div>
            <div class="arch-sub mono">Dynamic Matrix · Micro Spread</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Animated Connector Arrow 2 -->
    <div class="pipeline-connector">
      <div class="connector-line">
        <span class="pulse-beam gold-beam"></span>
      </div>
      <div class="connector-tag mono">
        <span>SINYAL BUY / SELL / LEVERAGE POSITIONING</span>
        <span class="arrow-icon">▼</span>
      </div>
    </div>

    <!-- STAGE 03: DUAL ARENA EXECUTION -->
    <div class="flow-stage stage-execution">
      <div class="stage-tag-bar exec-bar">
        <span class="stage-num mono exec-num">TAHAP 03</span>
        <span class="stage-label">DUAL ARENA EXECUTION TERMINALS</span>
        <span class="stage-badge exec-badge mono">MARK-TO-MARKET</span>
      </div>

      <div class="stage-body">
        <div class="terminals-grid">
          <!-- Spot Terminal Card -->
          <div 
            class="terminal-card spot-terminal" 
            role="button" 
            tabindex="0"
            onclick={() => goTo('/crypto-spot')}
            onkeydown={(e) => e.key === 'Enter' && goTo('/crypto-spot')}
          >
            <div class="term-head">
              <span class="term-title mono">CRYPTO SPOT</span>
              <span class="term-lev mono">1X NO-LEVERAGE</span>
            </div>
            <div class="term-stats">
              <div class="t-row">
                <span class="t-key">Peserta:</span>
                <span class="t-val mono">39 Model Strategi</span>
              </div>
              <div class="t-row">
                <span class="t-key">Modal:</span>
                <span class="t-val mono">{formatUSD(arena.startEquity, 0)} Modal Awal</span>
              </div>
              <div class="t-row">
                <span class="t-key">Fee:</span>
                <span class="t-val mono">Komisi 0.04% / Trade</span>
              </div>
            </div>
            <button type="button" class="term-btn spot-btn mono">Buka Arena Spot →</button>
          </div>

          <!-- Futures Terminal Card -->
          <div 
            class="terminal-card futures-terminal" 
            role="button" 
            tabindex="0"
            onclick={() => goTo('/crypto-futures')}
            onkeydown={(e) => e.key === 'Enter' && goTo('/crypto-futures')}
          >
            <div class="term-head">
              <span class="term-title mono">CRYPTO FUTURES</span>
              <span class="term-lev futures-tag mono">LEVERAGE 20X</span>
            </div>
            <div class="term-stats">
              <div class="t-row">
                <span class="t-key">Peserta:</span>
                <span class="t-val mono">53 Model Strategi</span>
              </div>
              <div class="t-row">
                <span class="t-key">Funding:</span>
                <span class="t-val mono">Simulasi 8 Jam (0.01%)</span>
              </div>
              <div class="t-row">
                <span class="t-key">Margin:</span>
                <span class="t-val mono">Mark-to-Market Realtime</span>
              </div>
            </div>
            <button type="button" class="term-btn futures-btn mono">Buka Arena Futures →</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Bottom Institutional Telemetry Footer -->
  <div class="panel-footer mono">
    <span>DATABASE: TIMESCALE POSTGRESQL</span>
    <span class="bullet">·</span>
    <span>EKSEKUSI: SYNTHETIC ZERO-SLIPPAGE</span>
    <span class="bullet">·</span>
    <span>SETTLEMENT: LIVE PER DETIK</span>
  </div>
</div>

<style>
  .pipeline-panel {
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
  }

  /* Header */
  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .live-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .header-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #e2e8f0;
  }

  .header-badges {
    display: flex;
    gap: 8px;
  }

  .badge-live {
    font-size: 10px;
    background: rgba(16, 185, 129, 0.12);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.25);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
  }

  .badge-latency {
    font-size: 10px;
    background: rgba(255, 255, 255, 0.05);
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
  }

  /* Pipeline Flow */
  .pipeline-flow {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .flow-stage {
    background: #090e17;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 8px;
    overflow: hidden;
  }

  .stage-tag-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: rgba(56, 189, 248, 0.06);
    border-bottom: 1px solid rgba(56, 189, 248, 0.12);
  }

  .stage-num {
    font-size: 10px;
    font-weight: 800;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.12);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .stage-label {
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.04em;
  }

  .stage-badge {
    font-size: 9.5px;
    font-weight: 700;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .stage-body {
    padding: 12px;
  }

  .stage-desc {
    font-size: 12px;
    color: #94a3b8;
    line-height: 1.5;
    margin: 0 0 10px 0;
  }

  .stage-desc strong {
    color: #f1f5f9;
  }

  /* Ticker Pills */
  .ticker-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .ticker-chip {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #05080f;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 11px;
  }

  .t-sym {
    color: #64748b;
    font-weight: 600;
  }

  .t-val {
    color: #38bdf8;
    font-weight: 700;
  }

  .more-chip {
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.04);
    font-size: 10px;
    font-weight: 700;
  }

  /* Pipeline Connector Arrow */
  .pipeline-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 2px 0;
  }

  .connector-line {
    position: relative;
    width: 2px;
    height: 14px;
    background: rgba(255, 255, 255, 0.15);
    overflow: hidden;
  }

  .pulse-beam {
    position: absolute;
    top: -10px;
    left: 0;
    width: 100%;
    height: 10px;
    background: #38bdf8;
    box-shadow: 0 0 6px #38bdf8;
    animation: flowDown 1.4s infinite linear;
  }

  .gold-beam {
    background: #f59e0b;
    box-shadow: 0 0 6px #f59e0b;
  }

  @keyframes flowDown {
    0% { top: -10px; }
    100% { top: 18px; }
  }

  .connector-tag {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 9.5px;
    color: #64748b;
    font-weight: 700;
    letter-spacing: 0.05em;
  }

  .arrow-icon {
    font-size: 10px;
    color: #f59e0b;
  }

  /* Stage 02: Core */
  .stage-core {
    border-color: rgba(245, 158, 11, 0.2);
  }

  .core-bar {
    background: rgba(245, 158, 11, 0.06);
    border-bottom: 1px solid rgba(245, 158, 11, 0.15);
  }

  .core-num {
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.15);
  }

  .core-badge {
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.12);
  }

  .archetype-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .arch-card {
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.06);
    padding: 8px 10px;
    border-radius: 6px;
  }

  .arch-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 3px;
  }

  .arch-name {
    font-size: 11px;
    font-weight: 700;
    color: #e2e8f0;
  }

  .arch-count {
    font-size: 10px;
    font-weight: 700;
    color: #f59e0b;
  }

  .arch-sub {
    font-size: 9.5px;
    color: #64748b;
  }

  /* Stage 03: Execution */
  .stage-execution {
    border-color: rgba(16, 185, 129, 0.2);
  }

  .exec-bar {
    background: rgba(16, 185, 129, 0.06);
    border-bottom: 1px solid rgba(16, 185, 129, 0.15);
  }

  .exec-num {
    color: #10b981;
    background: rgba(16, 185, 129, 0.15);
  }

  .exec-badge {
    color: #10b981;
    background: rgba(16, 185, 129, 0.12);
  }

  .terminals-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .terminal-card {
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .spot-terminal:hover {
    border-color: rgba(16, 185, 129, 0.4);
    background: #07130e;
    transform: translateY(-2px);
  }

  .futures-terminal:hover {
    border-color: rgba(245, 158, 11, 0.4);
    background: #130e05;
    transform: translateY(-2px);
  }

  .term-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .term-title {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.04em;
    color: #ffffff;
  }

  .term-lev {
    font-size: 9px;
    font-weight: 700;
    color: #10b981;
    background: rgba(16, 185, 129, 0.12);
    padding: 2px 5px;
    border-radius: 4px;
  }

  .futures-tag {
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.15);
  }

  .term-stats {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 10px;
  }

  .t-row {
    display: flex;
    justify-content: space-between;
    font-size: 10.5px;
  }

  .t-key {
    color: #64748b;
  }

  .t-val {
    color: #cbd5e1;
    font-weight: 600;
  }

  .term-btn {
    border: none;
    padding: 6px 10px;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
    text-align: center;
    transition: opacity 0.15s ease;
  }

  .spot-btn {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .spot-btn:hover {
    background: #10b981;
    color: #040806;
  }

  .futures-btn {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .futures-btn:hover {
    background: #f59e0b;
    color: #0b0702;
  }

  /* Footer */
  .panel-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    font-size: 9.5px;
    color: #64748b;
    letter-spacing: 0.05em;
  }

  .bullet {
    color: #334155;
  }

  @media (max-width: 600px) {
    .archetype-grid,
    .terminals-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
