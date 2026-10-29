<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent } from '../lib/formatters.js';
  import { getStrategyCategory } from '../lib/constants.js';

  let accounts = $derived(arena.activeAccounts);
  let positions = $derived(arena.activeData.positions || []);

  // Top performer
  let sorted = $derived([...accounts].sort((a, b) => (b.equity || 0) - (a.equity || 0)));
  let topStrategy = $derived(sorted[0] || null);

  // Totals
  let totalEquity = $derived(accounts.reduce((acc, a) => acc + (a.equity || arena.startEquity), 0));
  let totalMargin = $derived(positions.reduce((acc, p) => acc + (p.margin || 0), 0));
  let openPositionsCount = $derived(positions.length);

  // Long vs Short in futures
  let longCount = $derived(positions.filter((p) => (p.side || '').toUpperCase() === 'LONG').length);
  let shortCount = $derived(positions.filter((p) => (p.side || '').toUpperCase() === 'SHORT').length);
  let longPct = $derived(openPositionsCount > 0 ? (longCount / openPositionsCount) * 100 : 50);

  // MC Count
  let totalRefills = $derived(accounts.reduce((acc, a) => acc + (a.refillCount || 0), 0));
</script>

<div class="bento-container">
  <!-- Card 1: Alpha Leader (Top Strategy) -->
  <div
    class="bento-card leader-card"
    role="button"
    tabindex="0"
    onclick={() => topStrategy && (arena.selectedStrategyId = topStrategy.id)}
    onkeydown={(e) => e.key === 'Enter' && topStrategy && (arena.selectedStrategyId = topStrategy.id)}
  >
    <div class="card-head">
      <div class="head-title">
        <svg class="head-svg text-amber" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path>
          <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path>
          <path d="M4 22h16"></path>
          <path d="M10 14.66V17c0 .55-.45 1-1 1H7v4h10v-4h-2c-.55 0-1-.45-1-1v-2.34"></path>
          <path d="M6 4h12v7a6 6 0 0 1-12 0V4z"></path>
        </svg>
        <span>ALPHA LEADER</span>
      </div>
      {#if topStrategy}
        <span class="badge badge-neutral">{getStrategyCategory(topStrategy.id)}</span>
      {/if}
    </div>

    {#if topStrategy}
      <div class="leader-body">
        <div class="leader-name font-display">{topStrategy.name || topStrategy.id}</div>
        <div class="leader-metrics">
          <div class="metric-col">
            <span class="lbl">RETURN</span>
            <span class="val num {topStrategy.returnPct >= 0 ? 'text-up' : 'text-down'}">
              {formatPercent(topStrategy.returnPct)}
            </span>
          </div>
          <div class="metric-col">
            <span class="lbl">EKUITAS</span>
            <span class="val num">{formatUSD(topStrategy.equity)}</span>
          </div>
          <div class="metric-col">
            <span class="lbl">WIN RATE</span>
            <span class="val num">{Number(topStrategy.win_rate || 0).toFixed(1)}%</span>
          </div>
        </div>
        {#if topStrategy.refillCount > 0}
          <div class="mc-warning">
            <svg class="warn-svg" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <span>Pernah MC ({topStrategy.refillCount}x Refill)</span>
          </div>
        {/if}
      </div>
    {:else}
      <div class="empty-text">Menghitung ranking…</div>
    {/if}
  </div>

  <!-- Card 2: Arena Capital & Exposure -->
  <div class="bento-card capital-card">
    <div class="card-head">
      <div class="head-title">
        <svg class="head-svg text-cyan" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        </svg>
        <span>TOTAL MODAL ARENA</span>
      </div>
      <span class="badge badge-neutral num">{accounts.length} Akun</span>
    </div>

    <div class="capital-body">
      <div class="big-metric num font-display">
        {formatUSD(totalEquity, 0)}
      </div>
      <div class="sub-breakdown">
        <div class="sub-item">
          <span class="lbl">MARGIN TERPASANG:</span>
          <span class="val num">{formatUSD(totalMargin, 0)}</span>
        </div>
        <div class="sub-item">
          <span class="lbl">STATUS:</span>
          <span class="val status-active">2% Risk ATR / Trade</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Card 3: Realtime Order Flow Sentiment -->
  <div class="bento-card sentiment-card">
    <div class="card-head">
      <div class="head-title">
        <svg class="head-svg text-amber" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
        <span>SENTIMEN POSISI TERBUKA</span>
      </div>
      <span class="badge badge-neutral num">{openPositionsCount} Posisi</span>
    </div>

    <div class="sentiment-body">
      {#if arena.mode === 'futures'}
        <div class="sentiment-bar">
          <div class="bar-long" style="width: {longPct}%;"></div>
          <div class="bar-short" style="width: {100 - longPct}%;"></div>
        </div>
        <div class="sentiment-labels">
          <span class="long-val num">LONG {longCount} ({longPct.toFixed(0)}%)</span>
          <span class="short-val num">SHORT {shortCount} ({(100 - longPct).toFixed(0)}%)</span>
        </div>
      {:else}
        <div class="sentiment-spot">
          <div class="spot-stat">
            <span class="lbl">MODE:</span>
            <span class="val">Long Only (Tanpa Leverage)</span>
          </div>
          <div class="spot-stat">
            <span class="lbl">PAIR AKTIF:</span>
            <span class="val num">{arena.symbolsCount} Pasang USDT</span>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Card 4: Risk & Refill Defense -->
  <div class="bento-card defense-card">
    <div class="card-head">
      <div class="head-title">
        <svg class="head-svg text-emerald" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
        <span>MANAJEMEN RISIKO</span>
      </div>
      {#if totalRefills > 0}
        <span class="badge badge-amber num">{totalRefills} MC Refill</span>
      {:else}
        <span class="badge badge-neutral">0 MC</span>
      {/if}
    </div>

    <div class="defense-body">
      <div class="defense-item">
        <span class="d-label">ATR Trailing Stop</span>
        <span class="d-val">Aktif (1.5 - 2.5x ATR)</span>
      </div>
      <div class="defense-item">
        <span class="d-label">Dynamic Margin Cap</span>
        <span class="d-val">Max 10% per order</span>
      </div>
      <div class="defense-item">
        <span class="d-label">Likuidasi & Proteksi</span>
        <span class="d-val">Auto Refill {formatUSD(arena.startEquity, 0)} + Flag</span>
      </div>
    </div>
  </div>
</div>

<style>
  .bento-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    padding: 16px 20px 8px 20px;
  }

  .bento-card {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: border-color 0.15s ease, background-color 0.15s ease;
  }

  .bento-card:hover {
    border-color: var(--border-muted);
    background-color: var(--bg-surface-elevated);
  }

  .leader-card {
    cursor: pointer;
    border-left: 3px solid var(--color-amber);
  }

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .head-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--fg-muted);
  }

  .head-svg {
    opacity: 0.9;
    flex-shrink: 0;
  }

  .warn-svg {
    color: var(--color-amber);
    flex-shrink: 0;
  }

  .text-amber {
    color: #f59e0b;
  }

  .text-cyan {
    color: #38bdf8;
  }

  .text-emerald {
    color: #10b981;
  }

  .leader-name {
    font-size: 14px;
    font-weight: 700;
    color: var(--fg-primary);
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .leader-metrics {
    display: flex;
    gap: 14px;
  }

  .metric-col {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .metric-col .lbl {
    font-size: 9.5px;
    color: var(--fg-muted);
    font-weight: 600;
  }

  .metric-col .val {
    font-size: 13px;
    font-weight: 700;
  }

  .text-up {
    color: var(--color-up);
  }

  .text-down {
    color: var(--color-down);
  }

  .mc-warning {
    margin-top: 8px;
    font-size: 11px;
    color: var(--color-amber);
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  /* Capital Card */
  .big-metric {
    font-size: 22px;
    font-weight: 800;
    color: var(--fg-primary);
    line-height: 1.1;
    margin-bottom: 8px;
  }

  .sub-breakdown {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 11px;
  }

  .sub-item {
    display: flex;
    justify-content: space-between;
  }

  .sub-item .lbl {
    color: var(--fg-muted);
  }

  .sub-item .val {
    color: var(--fg-secondary);
    font-weight: 600;
  }

  .status-active {
    color: var(--color-cyan);
  }

  /* Sentiment */
  .sentiment-bar {
    display: flex;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 8px;
    background-color: var(--bg-base);
  }

  .bar-long {
    background-color: var(--color-up);
    transition: width 0.3s ease;
  }

  .bar-short {
    background-color: var(--color-down);
    transition: width 0.3s ease;
  }

  .sentiment-labels {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    font-weight: 600;
  }

  .long-val {
    color: var(--color-up);
  }

  .short-val {
    color: var(--color-down);
  }

  .sentiment-spot {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 11px;
  }

  .spot-stat {
    display: flex;
    justify-content: space-between;
  }

  .spot-stat .lbl {
    color: var(--fg-muted);
  }

  .spot-stat .val {
    color: var(--fg-primary);
    font-weight: 600;
  }

  /* Defense Card */
  .defense-body {
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 11px;
  }

  .defense-item {
    display: flex;
    justify-content: space-between;
  }

  .d-label {
    color: var(--fg-muted);
  }

  .d-val {
    color: var(--fg-primary);
    font-weight: 500;
  }

  .empty-text {
    font-size: 12px;
    color: var(--fg-muted);
    font-style: italic;
  }

  @media (max-width: 1100px) {
    .bento-container {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 650px) {
    .bento-container {
      grid-template-columns: 1fr;
      padding: 12px 12px 6px 12px;
    }
  }
</style>
