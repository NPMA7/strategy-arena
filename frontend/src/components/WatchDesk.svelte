<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPrice } from '../lib/formatters.js';

  let activeTab = $state('positions'); // 'positions' | 'logs'
  let searchQuery = $state('');

  let allPositions = $derived(arena.allActivePositions);
  let allEvents = $derived(arena.activeEvents);

  let filteredPositions = $derived.by(() => {
    if (!searchQuery.trim()) return allPositions;
    const q = searchQuery.toLowerCase().trim();
    return allPositions.filter(
      (p) =>
        p.strategy.toLowerCase().includes(q) ||
        p.symbol.toLowerCase().includes(q) ||
        p.side.toLowerCase().includes(q)
    );
  });

  function selectStrategy(id) {
    arena.selectedStrategyId = id;
  }
</script>

<section class="watch-desk panel">
  <!-- Desk Header with Tabs -->
  <div class="desk-head">
    <div class="desk-tabs">
      <button
        type="button"
        class="tab-btn {activeTab === 'positions' ? 'active' : ''}"
        onclick={() => (activeTab = 'positions')}
      >
        <span>Semua Posisi Terbuka</span>
        <span class="count-pill">{allPositions.length}</span>
      </button>
      <button
        type="button"
        class="tab-btn {activeTab === 'logs' ? 'active' : ''}"
        onclick={() => (activeTab = 'logs')}
      >
        <span>Log Eksekusi Realtime</span>
        <span class="count-pill">{allEvents.length}</span>
      </button>
    </div>

    {#if activeTab === 'positions'}
      <div class="search-box">
        <input
          type="text"
          placeholder="Cari pair / strategi..."
          bind:value={searchQuery}
        />
      </div>
    {/if}
  </div>

  <!-- Content: All Open Positions Table -->
  {#if activeTab === 'positions'}
    <div class="desk-body">
      {#if filteredPositions.length === 0}
        <div class="empty-state">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
          </svg>
          <span>Belum ada posisi terbuka di arena ini.</span>
        </div>
      {:else}
        <div class="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Strategi</th>
                <th>Pair</th>
                <th>Arah</th>
                <th>{arena.mode === 'forex' ? 'Lot' : 'Lev'}</th>
                <th class="r">Entry</th>
                <th class="r">Mark</th>
                <th class="r">uPnL</th>
                <th class="r">Stop</th>
              </tr>
            </thead>
            <tbody>
              {#each filteredPositions as p (p.strategy + '_' + p.symbol)}
                {@const isUp = (p.upnl ?? 0) >= 0}
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
                  <td class="mono muted">
                    {#if arena.mode === 'forex'}
                      {((p.lot != null && Number(p.lot) > 0) ? Number(p.lot).toFixed(2) : (p.qty >= 1000 ? (p.qty / 100000).toFixed(2) : Number(p.qty || 0.10).toFixed(2)))} Lot
                    {:else}
                      {p.leverage}x
                    {/if}
                  </td>
                  <td class="r mono">{formatPrice(p.entry)}</td>
                  <td class="r mono">{formatPrice(p.mark)}</td>
                  <td class="r mono font-bold {isUp ? 'up' : 'down'}">
                    {formatUSD(p.upnl)}
                  </td>
                  <td class="r mono muted">{p.stop ? formatPrice(p.stop) : '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {:else}
    <!-- Content: Realtime Execution Logs Feed -->
    <div class="desk-body log-feed">
      {#if allEvents.length === 0}
        <div class="empty-state">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
          </svg>
          <span>Menunggu eksekusi order berikutnya…</span>
        </div>
      {:else}
        <div class="feed-list">
          {#each [...allEvents].reverse() as e (e.ts + '_' + (e.symbol || '') + '_' + Math.random())}
            {@const timeStr = new Date(e.ts).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            {@const isEntry = (e.kind || '').includes('entry') || (e.message || '').includes('OPEN')}
            {@const isExit = (e.kind || '').includes('exit') || (e.message || '').includes('CLOSE')}
            {@const isMC = (e.kind || '').includes('refill') || (e.message || '').includes('REFILL') || (e.message || '').includes('MC')}
            <div class="ev-item">
              <span class="ev-time mono">{timeStr}</span>
              <span class="ev-tag {isMC ? 'tag-mc' : isEntry ? 'tag-entry' : 'tag-exit'}">
                {isMC ? 'REFILL' : isEntry ? 'ENTRY' : 'EXIT'}
              </span>
              <span class="ev-who">{(e.strats || []).join(', ')}</span>
              <span class="ev-msg">{e.message}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .watch-desk {
    background: #090d14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .desk-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 14px;
    background: #06090e;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-wrap: wrap;
  }

  .desk-tabs {
    display: flex;
    gap: 6px;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    border: 1px solid transparent;
    color: #8b9bb4;
    font-size: 11.5px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, border-color 0.15s;
    font-family: inherit;
  }

  .tab-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.04);
  }

  .tab-btn.active {
    background: #111722;
    border-color: rgba(255, 255, 255, 0.12);
    color: #f59e0b;
  }

  .count-pill {
    font-size: 10px;
    background: rgba(255, 255, 255, 0.08);
    color: #94a3b8;
    padding: 1px 5px;
    border-radius: 10px;
    font-family: monospace;
  }

  .search-box input {
    background: #0c111a;
    border: 1px solid rgba(255, 255, 255, 0.09);
    color: #ffffff;
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 4px;
    outline: none;
    font-family: inherit;
    width: 170px;
  }

  .search-box input:focus {
    border-color: #f59e0b;
  }

  .desk-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 400px;
    max-height: 440px;
    overflow-y: auto;
  }

  .tablewrap {
    flex: 1;
    overflow-y: auto;
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

  /* Log Feed */
  .log-feed {
    padding: 8px 10px;
    font-size: 11.5px;
  }

  .feed-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ev-item {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 6px 8px;
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    line-height: 1.4;
  }

  .ev-time {
    color: #64748b;
    font-size: 10px;
    white-space: nowrap;
  }

  .ev-tag {
    font-size: 9px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    white-space: nowrap;
  }

  .tag-entry {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .tag-exit {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .tag-mc {
    background: rgba(244, 63, 94, 0.2);
    color: #f43f5e;
    border: 1px solid rgba(244, 63, 94, 0.4);
  }

  .ev-who {
    color: #38bdf8;
    font-weight: 600;
    font-size: 11px;
    white-space: nowrap;
  }

  .ev-msg {
    color: #cbd5e1;
    font-family: var(--font-mono);
    font-size: 10.5px;
    word-break: break-all;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 40px;
    color: #64748b;
    font-size: 12px;
  }
</style>
