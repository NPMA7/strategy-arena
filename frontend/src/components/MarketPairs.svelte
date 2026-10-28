<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPrice } from '../lib/formatters.js';

  let isForex = $derived(arena.mode === 'forex');

  let pairs = $derived.by(() => {
    if (arena.mode === 'forex') {
      const fx = arena.forex?.pairs;
      if (fx && Array.isArray(fx) && fx.length > 0) return fx;
    } else if (arena.mode === 'futures') {
      const fut = arena.futures?.pairs;
      if (fut && Array.isArray(fut) && fut.length > 0) return fut;
    } else {
      const spt = arena.spot?.pairs;
      if (spt && Array.isArray(spt) && spt.length > 0) return spt;
    }
    if (arena.pairs && Array.isArray(arena.pairs) && arena.pairs.length > 0) {
      return arena.pairs;
    }
    const syms = Object.keys(arena.prices || {});
    if (syms.length > 0) {
      return syms.map((s, idx) => ({
        symbol: s,
        base: s.replace('USDT', ''),
        quote: 'USDT',
        rank: idx + 1,
        quote_volume: 50000000,
        last_close: arena.prices[s] || 0,
      }));
    }
    return [];
  });
</script>

<section class="panel pasar-panel">
  <div class="phead">
    <h2>Pasar</h2>
    <span class="sub muted">
      {pairs.length} pair {isForex ? 'Forex & Metals' : 'USDT'} · {isForex ? 'MT5 / MetaQuotes Live Stream' : 'peringkat volume 24 jam'} · tiles: {pairs.length}
    </span>
  </div>

  <div class="mkt-grid">
    {#each pairs as p (p.symbol)}
      {@const px = arena.prices[p.symbol] ?? p.last_close}
      {@const change = arena.priceChanges[p.symbol]}
      <div class="tile" data-symbol={p.symbol}>
        <div class="tile-top">
          <b>{isForex ? (p.base || p.symbol.slice(0, 3)) : (p.base || p.symbol.replace('USDT', ''))}</b>
          <span class="muted-sub">/{isForex ? (p.quote || (p.symbol.length === 6 ? p.symbol.slice(3) : '')) : 'USDT'}</span>
        </div>
        <div class="tile-px mono {change === 'up' ? 'text-up' : change === 'down' ? 'text-down' : ''}">
          {#if isForex}
            {px ? Number(px).toFixed(p.symbol.includes('JPY') || p.symbol === 'USOIL' ? 3 : (p.symbol === 'XAUUSD' ? 2 : 5)) : '—'}
          {:else}
            {px ? formatPrice(px) : '—'}
          {/if}
        </div>
        <div class="tile-vol mono muted">
          {#if isForex}
            vol {p.volume ? Number(p.volume).toLocaleString('en-US', { maximumFractionDigits: 1 }) + ' lot' : '—'}
          {:else}
            vol {formatUSD(p.quote_volume ?? 50000000, 0)}
          {/if}
        </div>
      </div>
    {/each}
  </div>
</section>

<style>
  .pasar-panel {
    background: #090d14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .phead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: #06090e;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0;
  }

  .phead h2 {
    font-size: 13.5px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
  }

  .sub {
    font-size: 10.5px;
    color: #64748b;
  }

  .mkt-grid {
    flex: 1 1 0;
    min-height: 0;
    overflow-y: scroll;
    scrollbar-gutter: stable;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 4px;
    padding: 8px;
    background: #06090e;
  }

  .tile {
    background: #0c1018;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    padding: 6px 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    transition: background 0.12s, border-color 0.12s;
  }

  .tile:hover {
    background: #111722;
    border-color: rgba(255, 255, 255, 0.12);
  }

  .tile-top {
    font-size: 11px;
    color: #f1f5f9;
  }

  .tile-top b {
    font-weight: 700;
  }

  .muted-sub {
    font-size: 9.5px;
    color: #64748b;
  }

  .tile-px {
    font-size: 11.5px;
    font-weight: 700;
    color: #e2e8f0;
    transition: color 0.25s ease;
  }

  .text-up {
    color: #10b981 !important;
  }

  .text-down {
    color: #f43f5e !important;
  }

  .tile-vol {
    font-size: 9px;
    color: #64748b;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
