<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent, formatPrice } from '../lib/formatters.js';

  let filterBySelected = $state(false);

  let allPositions = $derived(arena.activeData.positions || []);
  let selectedId = $derived(arena.selectedStrategyId);

  let displayedPositions = $derived(
    filterBySelected && selectedId
      ? allPositions.filter((p) => p.strategy === selectedId)
      : allPositions
  );

  let totalUnrealized = $derived(
    displayedPositions.reduce((acc, p) => acc + (p.pnl || 0), 0)
  );
</script>

<div class="positions-panel-root">
  <div class="panel-header">
    <div class="panel-title">
      <svg class="panel-icon-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="22" y1="12" x2="18" y2="12"></line>
        <line x1="6" y1="12" x2="2" y2="12"></line>
        <line x1="12" y1="6" x2="12" y2="2"></line>
        <line x1="12" y1="22" x2="12" y2="18"></line>
      </svg>
      <span>POSISI AKTIF</span>
      <span class="badge badge-neutral num">{displayedPositions.length} Open</span>
    </div>

    <div class="panel-actions">
      {#if selectedId}
        <button
          class="filter-toggle {filterBySelected ? 'active' : ''}"
          onclick={() => (filterBySelected = !filterBySelected)}
        >
          {filterBySelected ? `Filter: ${selectedId}` : 'Semua Strategi'}
        </button>
      {/if}
      <div class="total-pnl">
        <span class="lbl">TOTAL PNL:</span>
        <span class="val num {totalUnrealized >= 0 ? 'text-up' : 'text-down'}">
          {formatUSD(totalUnrealized)}
        </span>
      </div>
    </div>
  </div>

  <div class="positions-list">
    {#each displayedPositions as pos (pos.strategy + '_' + pos.symbol)}
      {@const side = (pos.side || 'LONG').toUpperCase()}
      {@const isLong = side === 'LONG'}
      {@const mark = arena.prices[pos.symbol] || pos.mark_price || pos.entry_price}
      {@const pnl = pos.pnl || 0}
      {@const pnlPct = pos.pnl_pct || (pos.margin ? (pnl / pos.margin) * 100 : 0)}

      <div class="position-card">
        <div class="pos-top">
          <div class="pos-pair">
            <span class="badge {isLong ? 'badge-up' : 'badge-down'} font-bold">
              {side}
            </span>
            {#if pos.leverage && pos.leverage > 1}
              <span class="badge badge-neutral num font-bold">{pos.leverage}x</span>
            {/if}
            <span class="pair-name font-bold">{pos.symbol.replace('USDT', '')}<span class="usdt">/USDT</span></span>
          </div>

          <button type="button" class="pos-strategy mono" onclick={() => (arena.selectedStrategyId = pos.strategy)}>
            {pos.strategy}
          </button>
        </div>

        <div class="pos-grid">
          <div class="grid-item">
            <span class="lbl">ENTRY</span>
            <span class="val num">${formatPrice(pos.entry_price, null, pos.symbol)}</span>
          </div>
          <div class="grid-item">
            <span class="lbl">MARK</span>
            <span class="val num">${formatPrice(mark, null, pos.symbol)}</span>
          </div>
          <div class="grid-item">
            <span class="lbl">TP</span>
            <span class="val num text-up">{pos.take_profit ? `$${formatPrice(pos.take_profit, null, pos.symbol)}` : '---'}</span>
          </div>
          <div class="grid-item">
            <span class="lbl">SL</span>
            <span class="val num text-down">{pos.stop_loss ? `$${formatPrice(pos.stop_loss, null, pos.symbol)}` : '---'}</span>
          </div>
        </div>

        <div class="pos-footer">
          <div class="margin-box">
            <span class="lbl">MARGIN:</span>
            <span class="val num">{formatUSD(pos.margin || 0)}</span>
          </div>
          <div class="pnl-box">
            <span class="pnl-val num {pnl >= 0 ? 'text-up' : 'text-down'}">
              {formatUSD(pnl)} ({formatPercent(pnlPct)})
            </span>
          </div>
        </div>
      </div>
    {:else}
      <div class="empty-positions">
        <svg class="empty-icon-svg" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        </svg>
        <span>Belum ada posisi terbuka {filterBySelected && selectedId ? `untuk strategi ${selectedId}` : 'di arena ini'}.</span>
      </div>
    {/each}
  </div>
</div>

<style>
  .positions-panel-root {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border-subtle);
    gap: 10px;
    background-color: var(--bg-surface-elevated);
  }

  .panel-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    color: var(--fg-muted);
    letter-spacing: 0.04em;
  }

  .panel-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .filter-toggle {
    font-size: 10.5px;
    padding: 3px 8px;
    border-radius: 4px;
    background: var(--bg-base);
    color: var(--fg-secondary);
    border: 1px solid var(--border-subtle);
  }

  .filter-toggle.active {
    background: rgba(56, 189, 248, 0.12);
    color: var(--color-cyan);
    border-color: var(--border-cyan);
  }

  .total-pnl {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
  }

  .total-pnl .lbl {
    color: var(--fg-muted);
    font-size: 9.5px;
  }

  .positions-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    overflow-y: auto;
    max-height: 520px;
  }

  .position-card {
    background-color: var(--bg-base);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    transition: border-color 0.15s ease;
  }

  .position-card:hover {
    border-color: var(--border-muted);
  }

  .pos-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .pos-pair {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .pair-name {
    font-size: 13px;
    color: var(--fg-primary);
  }

  .pair-name .usdt {
    font-size: 10px;
    color: var(--fg-muted);
    font-weight: 400;
  }

  .pos-strategy {
    font-size: 10px;
    color: var(--fg-muted);
    cursor: pointer;
    text-decoration: underline;
    text-decoration-color: transparent;
    transition: color 0.15s ease;
  }

  .pos-strategy:hover {
    color: var(--color-cyan);
    text-decoration-color: currentColor;
  }

  .pos-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    background-color: var(--bg-surface);
    padding: 6px 8px;
    border-radius: 4px;
  }

  .grid-item {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .grid-item .lbl {
    font-size: 9px;
    color: var(--fg-muted);
    font-weight: 600;
  }

  .grid-item .val {
    font-size: 11px;
    color: var(--fg-secondary);
  }

  .pos-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    border-top: 1px dashed var(--border-subtle);
    padding-top: 6px;
  }

  .margin-box {
    display: flex;
    gap: 4px;
    color: var(--fg-muted);
  }

  .pnl-val {
    font-weight: 700;
    font-size: 12px;
  }

  .text-up {
    color: var(--color-up);
  }

  .text-down {
    color: var(--color-down);
  }

  .empty-positions {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 40px 16px;
    color: var(--fg-muted);
    text-align: center;
    font-size: 12px;
  }

  .empty-icon-svg {
    color: var(--fg-muted);
    opacity: 0.6;
  }
</style>
