<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPrice } from '../lib/formatters.js';

  let searchQuery = $state('');
  let allPositions = $derived(arena.allActivePositions);

  let filteredPositions = $derived.by(() => {
    const list = allPositions || [];
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase().trim();
    return list.filter(
      (p) =>
        (p.strategy || '').toLowerCase().includes(q) ||
        (p.symbol || '').toLowerCase().includes(q) ||
        (p.side || '').toLowerCase().includes(q)
    );
  });

  function selectStrategy(id) {
    arena.selectedStrategyId = id;
  }
</script>

<section class="panel watch">
  <!-- Header: Pair yang sedang diperdagangkan -->
  <div class="phead">
    <div class="phead-left">
      <h2>Pair yang sedang diperdagangkan</h2>
      <span class="count-badge mono">{allPositions.length}</span>
    </div>

    <div class="phead-right">
      <div class="search-wrap">
        <input
          type="text"
          placeholder="Cari pair / strategi..."
          bind:value={searchQuery}
        />
      </div>
    </div>
  </div>

  <!-- Table Body -->
  <div class="tablewrap">
    {#if filteredPositions.length === 0}
      <div class="empty-state">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
        </svg>
        <span>Belum ada posisi terbuka di arena ini.</span>
      </div>
    {:else}
      <table>
        <thead>
          <tr>
            <th>Strategi</th>
            <th>Pair</th>
            <th>Arah</th>
            <th>Lev</th>
            <th class="r">Entry</th>
            <th class="r">Mark</th>
            <th class="r">uPnL</th>
            <th class="r">Stop</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredPositions as p (p.strategy + '_' + p.symbol)}
            {@const currentMark = arena.prices[p.symbol] ?? p.mark ?? p.entry}
            {@const sideSign = (p.side === 'LONG' || p.side === 1) ? 1 : -1}
            {@const liveUpnl = p.qty > 0 && currentMark > 0 ? (currentMark - p.entry) * p.qty * sideSign : (p.upnl ?? 0)}
            {@const isUp = liveUpnl >= 0}
            {@const isSelected = arena.selectedStrategyId === p.strategy}
            <tr
              class="pos-row {isSelected ? 'selected' : ''}"
              onclick={() => selectStrategy(p.strategy)}
              title="Klik untuk melihat strategi {p.strategy}"
            >
              <td class="strat-cell">
                <span class="strat-link">{p.strategy}</span>
              </td>
              <td class="font-bold">{p.symbol}</td>
              <td>
                <span class="chip {p.side === 'LONG' ? 'chip-long' : 'chip-short'}">
                  {p.side}
                </span>
              </td>
              <td class="mono muted">{p.leverage}x</td>
              <td class="r mono">{formatPrice(p.entry)}</td>
              <td class="r mono">{formatPrice(currentMark)}</td>
              <td class="r mono font-bold {isUp ? 'up' : 'down'}">
                {formatUSD(liveUpnl)}
              </td>
              <td class="r mono muted">{p.stop ? formatPrice(p.stop) : '—'}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</section>

<style>
  .watch {
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
    gap: 10px;
    padding: 10px 14px;
    background: #06090e;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0;
  }

  .phead-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .phead h2 {
    font-size: 13.5px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
  }

  .count-badge {
    font-size: 10px;
    background: #111722;
    color: #94a3b8;
    padding: 1px 6px;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .search-wrap input {
    background: #0c111a;
    border: 1px solid rgba(255, 255, 255, 0.09);
    color: #ffffff;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 4px;
    outline: none;
    font-family: inherit;
    width: 160px;
  }

  .search-wrap input:focus {
    border-color: #f59e0b;
  }

  .tablewrap {
    flex: 1 1 0;
    min-height: 0;
    overflow-y: scroll;
    scrollbar-gutter: stable;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
  }

  th {
    position: sticky;
    top: 0;
    background: #090e17;
    text-align: left;
    font-size: 9.5px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #64748b;
    padding: 6px 10px;
    font-weight: 700;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    z-index: 2;
  }

  td {
    padding: 6px 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    white-space: nowrap;
    color: #e2e8f0;
  }

  .pos-row {
    cursor: pointer;
    transition: background 0.12s;
  }

  .pos-row:hover td {
    background: rgba(255, 255, 255, 0.04);
  }

  .pos-row.selected td {
    background: rgba(245, 158, 11, 0.1);
  }

  .strat-link {
    color: #38bdf8;
    font-weight: 500;
  }

  .chip {
    font-size: 9.5px;
    font-weight: 700;
    padding: 2px 5px;
    border-radius: 3px;
  }

  .chip-long {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .chip-short {
    background: rgba(244, 63, 94, 0.15);
    color: #f43f5e;
    border: 1px solid rgba(244, 63, 94, 0.3);
  }

  .r {
    text-align: right;
  }

  .font-bold {
    font-weight: 600;
  }

  .muted {
    color: #64748b;
  }

  .up {
    color: #10b981;
  }

  .down {
    color: #f43f5e;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 40px;
    color: #64748b;
    font-size: 12px;
  }
</style>
