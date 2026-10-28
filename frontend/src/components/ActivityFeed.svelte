<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatPrice, formatTimeAgo } from '../lib/formatters.js';

  let events = $derived(arena.activeData.events || []);
</script>

<div class="feed-root">
  <div class="feed-header">
    <div class="feed-title">
      <svg class="feed-title-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
      </svg>
      <span>LOG EKSEKUSI REALTIME</span>
    </div>
    <span class="badge badge-neutral num">{events.length} Event</span>
  </div>

  <div class="feed-list">
    {#each events.slice(-30).reverse() as ev (ev.t + '_' + ev.strategy + '_' + ev.symbol + '_' + (ev.type || ''))}
      {@const type = (ev.type || '').toUpperCase()}
      {@const isBuy = type.includes('BUY') || type.includes('LONG')}
      {@const isClose = type.includes('CLOSE') || type.includes('EXIT')}
      {@const isTP = type.includes('TP')}
      {@const isSL = type.includes('SL')}
      {@const isMC = type.includes('MC') || type.includes('REFILL')}

      <div class="feed-item">
        <div class="item-left">
          <span
            class="action-pill {isMC ? 'pill-mc' : isTP ? 'pill-tp' : isSL ? 'pill-sl' : isBuy ? 'pill-buy' : 'pill-sell'}"
          >
            {ev.type || 'TRADE'}
          </span>
          <span class="ev-symbol font-bold">{ev.symbol ? ev.symbol.replace('USDT', '') : 'ALL'}</span>
          <button type="button" class="ev-strat mono" onclick={() => (arena.selectedStrategyId = ev.strategy)}>
            {ev.strategy}
          </button>
        </div>

        <div class="item-right">
          {#if ev.price}
            <span class="ev-price num">${formatPrice(ev.price)}</span>
          {/if}
          {#if ev.pnl !== undefined}
            <span class="ev-pnl num {ev.pnl >= 0 ? 'text-up' : 'text-down'}">
              {ev.pnl >= 0 ? '+' : ''}${ev.pnl.toFixed(2)}
            </span>
          {/if}
          <span class="ev-time">{formatTimeAgo(ev.t)}</span>
        </div>
      </div>
    {:else}
      <div class="empty-feed">
        Menunggu eksekusi order berikutnya…
      </div>
    {/each}
  </div>
</div>

<style>
  .feed-root {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .feed-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border-subtle);
    background-color: var(--bg-surface-elevated);
  }

  .feed-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    color: var(--fg-muted);
    letter-spacing: 0.04em;
  }

  .feed-title-svg {
    opacity: 0.8;
    color: var(--fg-muted);
  }

  .feed-list {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    max-height: 260px;
    padding: 6px 0;
  }

  .feed-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 14px;
    border-bottom: 1px solid var(--border-subtle);
    font-size: 11.5px;
    gap: 10px;
  }

  .feed-item:hover {
    background-color: var(--bg-surface-hover);
  }

  .item-left {
    display: flex;
    align-items: center;
    gap: 8px;
    overflow: hidden;
  }

  .action-pill {
    font-size: 9.5px;
    font-weight: 700;
    padding: 2px 5px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }

  .pill-buy {
    background: var(--color-up-bg);
    color: var(--color-up);
  }

  .pill-sell {
    background: var(--color-down-bg);
    color: var(--color-down);
  }

  .pill-tp {
    background: rgba(16, 185, 129, 0.18);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .pill-sl {
    background: rgba(244, 63, 94, 0.18);
    color: #fb7185;
    border: 1px solid rgba(244, 63, 94, 0.3);
  }

  .pill-mc {
    background: rgba(245, 158, 11, 0.2);
    color: var(--color-amber);
    border: 1px solid var(--border-amber);
  }

  .ev-symbol {
    color: var(--fg-primary);
  }

  .ev-strat {
    color: var(--fg-muted);
    font-size: 10.5px;
    cursor: pointer;
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
    max-width: 140px;
  }

  .ev-strat:hover {
    color: var(--color-cyan);
  }

  .item-right {
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
  }

  .ev-price {
    color: var(--fg-secondary);
  }

  .ev-pnl {
    font-weight: 700;
  }

  .ev-time {
    font-size: 10px;
    color: var(--fg-dim);
  }

  .text-up {
    color: var(--color-up);
  }

  .text-down {
    color: var(--color-down);
  }

  .empty-feed {
    padding: 20px;
    text-align: center;
    color: var(--fg-muted);
    font-size: 11.5px;
    font-style: italic;
  }
</style>
