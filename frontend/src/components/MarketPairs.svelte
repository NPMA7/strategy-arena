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
      {@const dec = p.digits ?? (p.symbol.includes('JPY') || p.symbol === 'XTIUSD' || p.symbol === 'USOIL' ? 3 : (p.symbol === 'XAUUSD' ? 2 : 5))}
      {@const bidNum = p.bid != null ? Number(p.bid) : (px != null ? Number(px) : null)}
      {@const askNum = p.ask != null ? Number(p.ask) : (px != null ? Number(px) : null)}
      {@const pipVal = p.pip || (dec === 3 ? 0.01 : (dec === 2 ? 0.1 : 0.0001))}
      {@const diff = (bidNum != null && askNum != null && askNum >= bidNum) ? (askNum - bidNum) : (p.spread != null ? Number(p.spread) : 0)}
      {@const sprPips = (diff > 0 && pipVal > 0) ? (diff / pipVal).toFixed(1) : (p.spread_pips != null ? Number(p.spread_pips).toFixed(1) : '0.0')}
      <div
        class="tile {isForex ? 'tile-forex' : ''}"
        data-symbol={p.symbol}
        role="button"
        tabindex="0"
        title="Klik untuk melihat Live Chart TradingView {p.symbol}"
        onclick={() => arena.openChart(p.symbol, isForex ? 'forex' : 'crypto')}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') arena.openChart(p.symbol, isForex ? 'forex' : 'crypto'); }}
      >
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

        {#if isForex}
          <div class="tile-fx-body">
            <div class="fx-row fx-bid mono">
              <span class="fx-lbl">Bid</span>
              <span class="fx-val text-bid">{bidNum != null ? bidNum.toFixed(dec) : '—'}</span>
            </div>
            <div class="fx-row fx-ask mono">
              <span class="fx-lbl">Ask</span>
              <span class="fx-val text-ask">{askNum != null ? askNum.toFixed(dec) : '—'}</span>
            </div>
            <div class="fx-spr-row mono">
              <span class="spr-tag" title="Spread dalam Pips">spread {sprPips}p</span>
              <span class="fx-spr-diff" title="Selisih Harga (Ask - Bid)">Δ {diff.toFixed(dec)}</span>
            </div>
          </div>
        {:else}
          <div class="tile-px mono {change === 'up' ? 'text-up' : change === 'down' ? 'text-down' : ''}">
            {px ? formatPrice(px) : '—'}
          </div>
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
    grid-template-columns: repeat(auto-fill, minmax(136px, 1fr));
    gap: 5px;
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
    cursor: pointer;
    transition: background 0.12s, border-color 0.12s, transform 0.12s, box-shadow 0.12s;
  }

  .tile-forex {
    padding: 7px 9px;
  }

  .tile:hover {
    background: #111728;
    border-color: rgba(245, 158, 11, 0.45);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
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

  .tile-fx-body {
    display: flex;
    flex-direction: column;
    gap: 2.5px;
    margin-top: 3px;
  }

  .fx-row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    line-height: 1.2;
  }

  .fx-lbl {
    font-size: 9.5px;
    font-weight: 700;
    color: #64748b;
    width: 14px;
    flex-shrink: 0;
  }

  .fx-val {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }

  .text-bid {
    color: #f43f5e;
  }

  .text-ask {
    color: #38bdf8;
  }

  .fx-spr-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 2px;
    gap: 4px;
  }

  .fx-spr-diff {
    font-size: 8.5px;
    font-weight: 500;
    color: #cbd5e1;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .spr-tag {
    font-size: 8.5px;
    font-weight: 600;
    color: #cbd5e1;
    white-space: nowrap;
    flex-shrink: 0;
  }

  @media (max-width: 480px) {
    .phead {
      padding: 8px 10px;
    }
    .mkt-grid {
      grid-template-columns: repeat(auto-fill, minmax(115px, 1fr));
      gap: 4px;
      padding: 6px;
    }
    .tile {
      padding: 5px 6px;
    }
    .tile-sym b {
      font-size: 10.5px;
    }
    .fx-val {
      font-size: 11px;
    }
  }
</style>
