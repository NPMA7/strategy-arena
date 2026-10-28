<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent, formatUptime } from '../lib/formatters.js';
  import NeuralNetworkVisualizer from './NeuralNetworkVisualizer.svelte';

  // Live top 3 strategies from active state with properly calculated returnPct
  let topSpot = $derived.by(() => {
    const list = [...arena.spotAccounts];
    list.sort((a, b) => (b.equity ?? 0) - (a.equity ?? 0));
    return list.slice(0, 3);
  });

  let topFutures = $derived.by(() => {
    const list = [...arena.futuresAccounts];
    list.sort((a, b) => (b.equity ?? 0) - (a.equity ?? 0));
    return list.slice(0, 3);
  });

  let topForex = $derived.by(() => {
    const list = [...arena.forexAccounts];
    list.sort((a, b) => (b.equity ?? 0) - (a.equity ?? 0));
    return list.slice(0, 3);
  });

  function enterTerminal(mode, stratId = null) {
    if (stratId) {
      arena.selectedStrategyId = stratId;
    }
    arena.navigate(mode === 'forex' ? '/forex' : (mode === 'futures' ? '/crypto-futures' : '/crypto-spot'));
  }
</script>

<div class="landing-root">
  <!-- Minimalist Institutional Top Navigation -->
  <header class="landing-header">
    <div class="landing-nav-container">
      <div class="brand">
        <div class="brand-emblem">
          <svg viewBox="0 0 64 64" width="32" height="32" class="emblem-svg">
            <defs>
              <linearGradient id="lndBg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#151b26"/>
                <stop offset="100%" stop-color="#080c12"/>
              </linearGradient>
              <linearGradient id="lndGold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fbbf24"/>
                <stop offset="100%" stop-color="#d97706"/>
              </linearGradient>
              <linearGradient id="lndCyan" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#38bdf8"/>
                <stop offset="100%" stop-color="#0284c7"/>
              </linearGradient>
            </defs>
            <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#lndBg)" stroke="#232d3d" stroke-width="1.5"/>
            <path d="M26 16 L15 16 L15 29 L26 31 L26 47 L14 47" stroke="url(#lndGold)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M31 47 L41 16 L51 47" stroke="url(#lndGold)" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M35 37 L47 37" stroke="url(#lndCyan)" stroke-width="3" stroke-linecap="round"/>
            <circle cx="41" cy="16" r="3.2" fill="#ffffff"/>
          </svg>
        </div>
        <div class="brand-text">
          <div class="brand-title">STRATEGY <span>ARENA</span></div>
          <div class="brand-sub mono">MULTI-ASSET QUANT BENCHMARK</div>
        </div>
      </div>

      <div class="header-actions">
        <!-- Live Uptime Pill -->
        <div class="uptime-pill">
          <span class="live-dot"></span>
          <span class="mono lbl">UPTIME:</span>
          <span class="mono val">{formatUptime(arena.uptime)}</span>
        </div>

        <!-- Terminal Enter CTA -->
        <button class="nav-btn btn-spot" onclick={() => enterTerminal('spot')}>
          <span>Terminal Spot</span>
        </button>
        <button class="nav-btn btn-futures" onclick={() => enterTerminal('futures')}>
          <span>Terminal Futures</span>
        </button>
        <button class="nav-btn btn-forex" onclick={() => enterTerminal('forex')}>
          <span>Terminal Forex</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Hero Section with 3D Core Viewport -->
  <section class="hero-section">
    <div class="hero-container">
      <!-- Left Column: Copy & Direct CTAs -->
      <div class="hero-content">
        <div class="eyebrow mono">
          <span>LIVE BINANCE & METATRADER 5</span>
          <span class="bullet">·</span>
          <span>120++ PAIRS MULTI-ASSET</span>
        </div>

        <h1 class="hero-title">
          ARENA KUANTITATIF<br />
          MULTI-PASAR TERBESAR.
        </h1>

        <p class="hero-desc">
          86 algoritma kuantitatif independen bertarung tanpa emosi di pasar kripto Binance dan Forex & Metals MT5 secara real-time. Dilengkapi mark-to-market live per detik, eksekusi MT5 Direct tanpa funding fee, simulasi leverage kripto & spread nyata broker.
        </p>

        <!-- CTAs -->
        <div class="hero-ctas">
          <button class="cta-secondary" onclick={() => enterTerminal('spot')}>
            <div class="cta-title">Arena Spot</div>
            <div class="cta-sub mono">NO-LEVERAGE · 35++ STRATEGI</div>
          </button>
          <button class="cta-primary" onclick={() => enterTerminal('futures')}>
            <div class="cta-title">Arena Futures</div>
            <div class="cta-sub mono">LEVERAGE 1-20X · 50++ STRATEGI</div>
          </button>

          <button class="cta-forex" onclick={() => enterTerminal('forex')}>
            <div class="cta-title">Arena Forex</div>
            <div class="cta-sub mono">MT5 DIRECT · 30++ STRATEGI</div>
          </button>

        </div>

        <!-- Key Metrics Quad -->
        <div class="metrics-quad">
          <div class="metric-item">
            <span class="m-val mono">50++</span>
            <span class="m-lbl">Model Algoritma</span>
          </div>
          <div class="metric-item">
            <span class="m-val mono">100++</span>
            <span class="m-lbl">Pairs</span>
          </div>
          <div class="metric-item">
            <span class="m-val mono">$10.000</span>
            <span class="m-lbl">Modal Awal Seragam</span>
          </div>
          <div class="metric-item">
            <span class="m-val mono">&lt; 5ms</span>
            <span class="m-lbl">Latensi Sinyal Internal</span>
          </div>
        </div>
      </div>

      <!-- Right Column: Deep Neural Network Architecture -->
      <div class="hero-pipeline">
        <NeuralNetworkVisualizer />
      </div>
    </div>
  </section>

  <!-- Live Strategy Podium Section (Top Spot & Top Futures) -->
  <section class="podium-section">
    <div class="section-container">
      <div class="section-head">
        <div>
          <h2>PAPAN KLASEMEN SEMENTARA</h2>
          <p class="section-desc">Peringkat strategi teratas yang saat ini memimpin perolehan ekuitas di kedua arena.</p>
        </div>
        <div class="podium-badges mono">
          <span>DATA REALTIME DARI DATABASE ENGINE</span>
        </div>
      </div>

      <div class="podium-grid">
        <!-- Top Spot Column -->
        <div class="podium-col">
          <div class="col-header">
            <span class="col-tag spot-tag">CRYPTO SPOT</span>
          </div>

          <div class="card-stack">
            {#each topSpot as s, idx}
              <div
                class="podium-card"
                role="button"
                tabindex="0"
                onclick={() => enterTerminal('spot', s.id)}
                onkeydown={(e) => e.key === 'Enter' && enterTerminal('spot', s.id)}
              >
                <div class="card-left">
                  <span class="rank-badge mono">#{idx + 1}</span>
                  <div>
                    <div class="strat-name">{s.name}</div>
                    <div class="strat-sub mono">{s.trades || 0} Trade · WR {s.trades > 0 ? ((s.wins / s.trades) * 100).toFixed(0) : 0}%</div>
                  </div>
                </div>
                <div class="card-right">
                  <div class="strat-eq mono">{formatUSD(s.equity)}</div>
                  <div class="strat-ret mono {s.returnPct >= 0 ? 'up' : 'down'}">{formatPercent(s.returnPct)}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Top Futures Column -->
        <div class="podium-col">
          <div class="col-header">
            <span class="col-tag futures-tag">CRYPTO FUTURES</span>
          </div>

          <div class="card-stack">
            {#each topFutures as s, idx}
              <div
                class="podium-card"
                role="button"
                tabindex="0"
                onclick={() => enterTerminal('futures', s.id)}
                onkeydown={(e) => e.key === 'Enter' && enterTerminal('futures', s.id)}
              >
                <div class="card-left">
                  <span class="rank-badge mono">#{idx + 1}</span>
                  <div>
                    <div class="strat-name">{s.name}</div>
                    <div class="strat-sub mono">{s.leverage || 1}x Lev · {s.trades || 0} Trade · WR {s.trades > 0 ? ((s.wins / s.trades) * 100).toFixed(0) : 0}%</div>
                  </div>
                </div>
                <div class="card-right">
                  <div class="strat-eq mono">{formatUSD(s.equity)}</div>
                  <div class="strat-ret mono {s.returnPct >= 0 ? 'up' : 'down'}">{formatPercent(s.returnPct)}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Top Forex Column -->
        <div class="podium-col">
          <div class="col-header">
            <span class="col-tag forex-tag">FOREX & METALS</span>
          </div>

          <div class="card-stack">
            {#each topForex as s, idx}
              <div
                class="podium-card"
                role="button"
                tabindex="0"
                onclick={() => enterTerminal('forex', s.id)}
                onkeydown={(e) => e.key === 'Enter' && enterTerminal('forex', s.id)}
              >
                <div class="card-left">
                  <span class="rank-badge mono">#{idx + 1}</span>
                  <div>
                    <div class="strat-name">{s.name}</div>
                    <div class="strat-sub mono">MT5 Direct · {s.trades || 0} Trade · WR {s.trades > 0 ? ((s.wins / s.trades) * 100).toFixed(0) : 0}%</div>
                  </div>
                </div>
                <div class="card-right">
                  <div class="strat-eq mono">{formatUSD(s.equity)}</div>
                  <div class="strat-ret mono {s.returnPct >= 0 ? 'up' : 'down'}">{formatPercent(s.returnPct)}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Institutional Architecture Bento Grid -->
  <section class="bento-section">
    <div class="section-container">
      <div class="section-head">
        <div>
          <h2>ARSITEKTUR MESIN KUANTITATIF</h2>
          <p class="section-desc">Infrastruktur modular yang dirancang untuk keandalan simulasi pasar tanpa jeda.</p>
        </div>
      </div>

      <div class="bento-grid">
        <div class="bento-card bento-wide">
          <div class="bento-num mono">01 / FEED</div>
          <h3>Binance Vision WebSocket Stream</h3>
          <p>
            Mengkonsumsi jutaan tick trade publik per hari dari 100++ pair USDT dengan likuiditas tertinggi di Binance. Engine merangkum candle M1 internal secara real-time dan mengevaluasi sinyal di setiap penutupan bar.
          </p>
          <div class="bento-meta mono">TICK STREAM 100++ PAIR · LATENSI &lt; 5MS</div>
        </div>

        <div class="bento-card">
          <div class="bento-num mono">02 / STORAGE</div>
          <h3>Persistensi Database</h3>
          <p>
            Seluruh data candle 1-menit, transaksi masuk/keluar, posisi aktif, dan snapshot ekuitas 24 jam tersimpan persisten dalam database relational.
          </p>
          <div class="bento-meta mono">TIMESERIES · RELATIONAL AUDIT TRAIL</div>
        </div>

        <div class="bento-card">
          <div class="bento-num mono">03 / MARGIN</div>
          <h3>Aturan Risiko Realistis</h3>
          <p>
            Alokasi maksimal 20% ($2.000) per pair hingga 5 pair simultan. Memperhitungkan leverage 1x-20x, biaya komisi taker 0.05%, dan pendanaan funding 0.01%/8 jam.
          </p>
          <div class="bento-meta mono">LEVERAGE 1x-20x · SL & TP TERJADWAL</div>
        </div>

        <div class="bento-card bento-wide">
          <div class="bento-num mono">04 / COPY-TRADE</div>
          <h3>API Copy-Trade & Ekspor Sinyal</h3>
          <p>
            Sinyal eksekusi order disiarkan secara instan melalui WebSocket channel publik. Dilengkapi modul API key untuk menghubungkan bot eksternal atau terminal eksekusi otomatis.
          </p>
          <div class="bento-meta mono">WEBSOCKET BROADCAST · REST API ENDPOINTS</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Institutional Footer -->
  <footer class="landing-footer">
    <div class="footer-container">
      <div class="foot-left">
        <div class="foot-title">STRATEGY ARENA</div>
        <p class="foot-desc">Platform benchmark kuantitatif mandiri.</p>
      </div>

      <div class="foot-links">
        <button class="foot-btn" onclick={() => enterTerminal('spot')}>Terminal Spot</button>
        <button class="foot-btn" onclick={() => enterTerminal('futures')}>Terminal Futures</button>
        <button class="foot-btn" onclick={() => enterTerminal('forex')}>Terminal Forex</button>
        <a href="/api/bootstrap" target="_blank" class="foot-btn">API Bootstrap</a>
      </div>
    </div>
  </footer>
</div>

<style>
  .landing-root {
    min-height: 100vh;
    background-color: #070a0f;
    color: #f1f5f9;
    display: flex;
    flex-direction: column;
    font-family: 'Inter', sans-serif;
  }

  /* Header */
  .landing-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #090d14;
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .landing-nav-container {
    max-width: 1440px;
    margin: 0 auto;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .brand-title {
    font-size: 15px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
  }

  .brand-title span {
    color: #f59e0b;
  }

  .brand-sub {
    font-size: 9px;
    letter-spacing: 0.12em;
    color: #64748b;
    font-weight: 600;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .uptime-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #111722;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 11px;
  }

  .live-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .uptime-pill .lbl {
    color: #64748b;
    font-weight: 600;
  }

  .uptime-pill .val {
    color: #f1f5f9;
    font-weight: 700;
  }

  .nav-btn {
    padding: 7px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-spot {
    background: #151c29;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .btn-spot:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  .btn-futures {
    background: #f59e0b;
    color: #000000;
    border: 1px solid #f59e0b;
    font-weight: 700;
  }

  .btn-futures:hover {
    background: #fbbf24;
  }

  .btn-forex {
    background: rgba(16, 185, 129, 0.12);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.4);
    font-weight: 600;
  }

  .btn-forex:hover {
    background: rgba(16, 185, 129, 0.22);
  }

  /* Hero Section */
  .hero-section {
    padding: 56px 24px 72px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: radial-gradient(ellipse at 80% 20%, rgba(245, 158, 11, 0.05) 0%, transparent 60%);
  }

  .hero-container {
    max-width: 1440px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
    gap: 48px;
    align-items: center;
  }

  .eyebrow {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: #f59e0b;
    margin-bottom: 16px;
  }

  .bullet {
    color: #64748b;
  }

  .hero-title {
    font-size: 42px;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.03em;
    color: #ffffff;
    margin: 0 0 20px 0;
  }

  .hero-desc {
    font-size: 15px;
    line-height: 1.6;
    color: #94a3b8;
    max-width: 580px;
    margin: 0 0 32px 0;
  }

  .hero-ctas {
    display: flex;
    gap: 14px;
    margin-bottom: 40px;
    flex-wrap: wrap;
  }

  .cta-primary {
    background: #f59e0b;
    color: #04070c;
    border: 1px solid #f59e0b;
    padding: 12px 22px;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    transition: transform 0.15s ease, background 0.15s ease;
  }

  .cta-primary:hover {
    background: #fbbf24;
    transform: translateY(-1px);
  }

  .cta-primary .cta-title {
    font-size: 15px;
    font-weight: 800;
    letter-spacing: -0.01em;
  }

  .cta-primary .cta-sub {
    font-size: 9.5px;
    font-weight: 700;
    opacity: 0.85;
    margin-top: 3px;
  }

  .cta-forex {
    background: rgba(16, 185, 129, 0.08);
    color: #ffffff;
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 12px 22px;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s ease;
  }

  .cta-forex:hover {
    border-color: #10b981;
    background: rgba(16, 185, 129, 0.16);
    transform: translateY(-1px);
  }

  .cta-forex .cta-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #10b981;
  }

  .cta-forex .cta-sub {
    font-size: 9.5px;
    font-weight: 600;
    color: #64748b;
    margin-top: 3px;
  }

  .cta-secondary {
    background: #111722;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    padding: 12px 22px;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s ease;
  }

  .cta-secondary:hover {
    border-color: rgba(255, 255, 255, 0.35);
    background: #161e2c;
    transform: translateY(-1px);
  }

  .cta-secondary .cta-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }

  .cta-secondary .cta-sub {
    font-size: 9.5px;
    font-weight: 600;
    color: #64748b;
    margin-top: 3px;
  }

  .metrics-quad {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .metric-item .m-val {
    display: block;
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
  }

  .metric-item .m-lbl {
    display: block;
    font-size: 11px;
    color: #64748b;
    margin-top: 4px;
  }

  .hero-pipeline {
    width: 100%;
    min-height: 480px;
  }

  /* Podium Section */
  .podium-section {
    padding: 64px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #090d14;
  }

  .section-container {
    max-width: 1440px;
    margin: 0 auto;
  }

  .section-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 28px;
    flex-wrap: wrap;
    gap: 16px;
  }

  .section-head h2 {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
    margin: 0 0 6px 0;
  }

  .section-desc {
    font-size: 13.5px;
    color: #64748b;
    margin: 0;
  }

  .podium-badges {
    font-size: 10.5px;
    color: #64748b;
    font-weight: 600;
    letter-spacing: 0.06em;
  }

  .podium-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 20px;
  }

  .podium-col {
    background: #070a0f;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 16px;
  }

  .col-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .col-tag {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
  }

  .spot-tag {
    color: #fbbf24;
  }

  .futures-tag {
    color: #38bdf8;
  }

  .forex-tag {
    color: #10b981;
  }


  .card-stack {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .podium-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    background: #0d131e;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .podium-card:hover {
    background: #131b2a;
    border-color: rgba(255, 255, 255, 0.2);
    transform: translateX(2px);
  }

  .card-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .rank-badge {
    font-size: 11.5px;
    font-weight: 800;
    color: #f59e0b;
    background: #1a2233;
    padding: 2px 7px;
    border-radius: 4px;
  }

  .strat-name {
    font-size: 13.5px;
    font-weight: 700;
    color: #f1f5f9;
  }

  .strat-sub {
    font-size: 10.5px;
    color: #64748b;
    margin-top: 2px;
  }

  .card-right {
    text-align: right;
  }

  .strat-eq {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
  }

  .strat-ret {
    font-size: 11.5px;
    font-weight: 700;
    margin-top: 2px;
  }

  .up {
    color: #10b981;
  }

  .down {
    color: #f43f5e;
  }

  /* Bento Architecture Section */
  .bento-section {
    padding: 64px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .bento-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
  }

  .bento-card {
    background: #090d14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .bento-wide {
    grid-column: span 2;
  }

  .bento-num {
    font-size: 11px;
    font-weight: 700;
    color: #f59e0b;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
  }

  .bento-card h3 {
    font-size: 17px;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 10px 0;
  }

  .bento-card p {
    font-size: 13.5px;
    line-height: 1.6;
    color: #94a3b8;
    margin: 0 0 20px 0;
  }

  .bento-meta {
    font-size: 10px;
    color: #475569;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  /* Footer */
  .landing-footer {
    padding: 36px 24px;
    background: #05080c;
  }

  .footer-container {
    max-width: 1440px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
  }

  .foot-title {
    font-size: 13px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.04em;
  }

  .foot-desc {
    font-size: 12px;
    color: #64748b;
    margin: 4px 0 0 0;
  }

  .foot-links {
    display: flex;
    gap: 12px;
  }

  .foot-btn {
    background: none;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 11.5px;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s ease;
  }

  .foot-btn:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  @media (max-width: 1024px) {
    .hero-container {
      grid-template-columns: 1fr;
    }
    .podium-grid {
      grid-template-columns: 1fr;
    }
    .bento-grid {
      grid-template-columns: 1fr;
    }
    .bento-wide {
      grid-column: span 1;
    }
  }
</style>
