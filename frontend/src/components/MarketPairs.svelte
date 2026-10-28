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
      {pairs.length} pair {isForex ? 'Forex & Metals' : 'USDT'} · {isForex ? 'MT5 Headway Live (Bid / Ask / Spread)' : 'peringkat volume 24 jam'} · tiles: {pairs.length}
    </span>
  </div>

  <div class="mkt-grid">
    {#each pairs as p (p.symbol)}
      {@const px = arena.prices[p.symbol] ?? p.last_close}
      {@const change = arena.priceChanges[p.symbol]}
      {@const dec = p.digits ?? (p.symbol.includes('JPY') || p.symbol === 'USOIL' ? 3 : (p.symbol === 'XAUUSD' ? 2 : 5))}
      <div class="tile {isForex ? 'tile-forex' : ''}" data-symbol={p.symbol}>
        <div class="tile-top">
          <div class="tile-sym">
            <b>{isForex ? (p.base || p.symbol.slice(0, 3)) : (p.base || p.symbol.replace('USDT', ''))}</b>
            <span class="muted-sub">/{isForex ? (p.quote || (p.symbol.length === 6 ? p.symbol.slice(3) : '')) : 'USDT'}</span>
          </div>
          {#if isForex && p.change != null}
            <span class="chg-badge mono {p.change >= 0 ? 'badge-up' : 'badge-down'}">
              {p.change >= 0 ? '+' : ''}{Number(p.change).toFixed(2)}%
            </span>
          {/if}
        </div>
        <div class="tile-px mono {change === 'up' ? 'text-up' : change === 'down' ? 'text-down' : ''}">
          {#if isForex}
            {px ? Number(px).toFixed(dec) : '—'}
          {:else}
            {px ? formatPrice(px) : '—'}
          {/if}
        </div>
        {#if isForex}
          <div class="tile-ba mono">
            <span class="ba-val"><span class="ba-lbl">B</span>{p.bid ? Number(p.bid).toFixed(dec) : (px ? Number(px).toFixed(dec) : '—')}</span>
            <span class="ba-val"><span class="ba-lbl">A</span>{p.ask ? Number(p.ask).toFixed(dec) : (px ? Number(px).toFixed(dec) : '—')}</span>
            <span class="spr-tag">spr {p.spread_pips ?? '1.2'}p</span>
          </div>
        {:else}
          <div class="tile-vol mono muted">
            vol {formatUSD(p.quote_volume ?? 50000000, 0)}
          </div>
        {/if}
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
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .tile-sym {
    display: flex;
    align-items: baseline;
    gap: 1px;
  }

  .tile-top b {
    font-weight: 700;
  }

  .muted-sub {
    font-size: 9.5px;
    color: #64748b;
  }

  .chg-badge {
    font-size: 8.5px;
    font-weight: 600;
    padding: 0.5px 3.5px;
    border-radius: 3px;
    letter-spacing: -0.01em;
  }

  .badge-up {
    color: #10b981;
    background: rgba(16, 185, 129, 0.12);
  }

  .badge-down {
    color: #f43f5e;
    background: rgba(244, 63, 94, 0.12);
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

  .tile-ba {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 8.5px;
    color: #94a3b8;
    gap: 2px;
    margin-top: 1px;
  }

  .ba-val {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ba-lbl {
    color: #64748b;
    margin-right: 1.5px;
    font-size: 7.5px;
  }

  .spr-tag {
    font-size: 8px;
    color: #cbd5e1;
    background: rgba(255, 255, 255, 0.06);
    padding: 0 3px;
    border-radius: 2px;
    flex-shrink: 0;
  }
</style>
