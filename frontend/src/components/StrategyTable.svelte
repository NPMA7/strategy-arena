<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent } from '../lib/formatters.js';
  import { getStrategyCategory } from '../lib/constants.js';

  const ARCHETYPES = ['Semua', 'Trend Following', 'Momentum', 'Mean Reversion', 'Institutional', 'Quantitative'];

  let activeArchetype = $state('Semua');
  let search = $state('');
  let sortKey = $state('equity');
  let sortAsc = $state(false);

  function setSort(key) {
    if (sortKey === key) {
      sortAsc = !sortAsc;
    } else {
      sortKey = key;
      sortAsc = false;
    }
  }

  let accounts = $derived(arena.activeAccounts);

  let filtered = $derived(
    accounts.filter((a) => {
      const cat = getStrategyCategory(a.id);
      if (activeArchetype !== 'Semua' && cat !== activeArchetype) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const matchName = (a.name || '').toLowerCase().includes(q);
        const matchId = (a.id || '').toLowerCase().includes(q);
        return matchName || matchId;
      }
      return true;
    })
  );

  let sorted = $derived(
    [...filtered].sort((a, b) => {
      let valA = a[sortKey];
      let valB = b[sortKey];

      if (sortKey === 'returnPct') {
        valA = a.returnPct;
        valB = b.returnPct;
      } else if (sortKey === 'name') {
        valA = (a.name || a.id).toLowerCase();
        valB = (b.name || b.id).toLowerCase();
      }

      if (valA === valB) return 0;
      if (valA === undefined || valA === null) return 1;
      if (valB === undefined || valB === null) return -1;

      return sortAsc ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
    })
  );
</script>

<div class="table-container">
  <!-- Controls Bar -->
  <div class="table-controls">
    <div class="archetype-tabs">
      {#each ARCHETYPES as arch}
        <button
          class="tab-btn {activeArchetype === arch ? 'active' : ''}"
          onclick={() => (activeArchetype = arch)}
        >
          {arch}
        </button>
      {/each}
    </div>

    <div class="search-box">
      <svg class="search-icon-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
      <input
        type="text"
        placeholder="Cari strategi..."
        bind:value={search}
      />
      {#if search}
        <button class="clear-btn" onclick={() => (search = '')}>×</button>
      {/if}
    </div>
  </div>

  <!-- Table Body -->
  <div class="table-scroll">
    <table class="strategy-table">
      <thead>
        <tr>
          <th class="th-rank" onclick={() => setSort('equity')}>
            # {sortKey === 'equity' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-name" onclick={() => setSort('name')}>
            STRATEGI {sortKey === 'name' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-cat">KATEGORI</th>
          <th class="th-num" onclick={() => setSort('returnPct')}>
            RETURN {sortKey === 'returnPct' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-num" onclick={() => setSort('equity')}>
            EKUITAS {sortKey === 'equity' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-num" onclick={() => setSort('win_rate')}>
            WIN RATE {sortKey === 'win_rate' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-num" onclick={() => setSort('profit_factor')}>
            P.FACTOR {sortKey === 'profit_factor' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-num" onclick={() => setSort('max_drawdown')}>
            MAX DD {sortKey === 'max_drawdown' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-pos" onclick={() => setSort('open')}>
            POSISI {sortKey === 'open' ? (sortAsc ? '▲' : '▼') : ''}
          </th>
          <th class="th-status">STATUS</th>
          <th class="th-action">AKSI</th>
        </tr>
      </thead>
      <tbody>
        {#each sorted as s, idx (s.id)}
          {@const isSelected = arena.selectedStrategyId === s.id}
          {@const cat = getStrategyCategory(s.id)}
          <tr
            class="table-row {isSelected ? 'selected' : ''}"
            onclick={() => (arena.selectedStrategyId = s.id)}
          >
            <!-- Rank -->
            <td class="td-rank num">
              {#if idx === 0}
                <span class="rank-crown gold">1</span>
              {:else if idx === 1}
                <span class="rank-crown silver">2</span>
              {:else if idx === 2}
                <span class="rank-crown bronze">3</span>
              {:else}
                <span class="rank-num">{idx + 1}</span>
              {/if}
            </td>

            <!-- Strategy Name -->
            <td class="td-name">
              <div class="name-box">
                <span class="s-title font-display">{s.name || s.id}</span>
                <span class="s-id mono">{s.id}</span>
              </div>
            </td>

            <!-- Archetype Category -->
            <td class="td-cat">
              <span class="badge badge-neutral">{cat}</span>
            </td>

            <!-- Return % -->
            <td class="td-num">
              <span class="num font-bold {s.returnPct >= 0 ? 'text-up' : 'text-down'}">
                {formatPercent(s.returnPct)}
              </span>
            </td>

            <!-- Equity -->
            <td class="td-num">
              <span class="num font-semibold">{formatUSD(s.equity)}</span>
            </td>

            <!-- Win Rate -->
            <td class="td-num">
              <div class="winrate-cell">
                <span class="num">{Number(s.win_rate || 0).toFixed(1)}%</span>
                <div class="winrate-bar">
                  <div
                    class="winrate-fill"
                    style="width: {Math.min(100, Math.max(0, s.win_rate || 0))}%;"
                  ></div>
                </div>
              </div>
            </td>

            <!-- Profit Factor -->
            <td class="td-num">
              <span class="num">{Number(s.profit_factor || 0).toFixed(2)}</span>
            </td>

            <!-- Max Drawdown -->
            <td class="td-num">
              <span class="num text-down">
                {formatPercent(s.max_drawdown || 0, false)}
              </span>
            </td>

            <!-- Open Positions Count -->
            <td class="td-pos">
              <span class="pos-badge num {s.open > 0 ? 'has-pos' : ''}">
                {s.open || 0}
              </span>
            </td>

            <!-- MC Refill Status Badge -->
            <td class="td-status">
              {#if s.refillCount > 0}
                <span class="badge badge-amber badge-mc" title="Strategi ini pernah mencapai $0 dan telah diisi ulang modalnya">
                  <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                  <span>MC ({s.refillCount}x)</span>
                </span>
              {:else}
                <span class="badge badge-up">Aktif</span>
              {/if}
            </td>

            <!-- Action -->
            <td class="td-action">
              <button
                class="btn-inspect"
                onclick={(e) => {
                  e.stopPropagation();
                  arena.selectedStrategyId = s.id;
                }}
              >
                Inspect
              </button>
            </td>
          </tr>
        {:else}
          <tr>
            <td colspan="11" class="td-empty">
              Tidak ada strategi yang cocok dengan kriteria pencarian "{search}".
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

<style>
  .table-container {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .table-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-subtle);
    gap: 12px;
    flex-wrap: wrap;
  }

  .archetype-tabs {
    display: flex;
    gap: 4px;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .tab-btn {
    padding: 5px 10px;
    border-radius: 5px;
    font-size: 11.5px;
    font-weight: 500;
    color: var(--fg-secondary);
    background: transparent;
    transition: all 0.15s ease;
    white-space: nowrap;
  }

  .tab-btn:hover {
    color: var(--fg-primary);
    background: var(--bg-surface-elevated);
  }

  .tab-btn.active {
    color: var(--fg-primary);
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-muted);
    font-weight: 600;
  }

  .search-box {
    display: flex;
    align-items: center;
    gap: 6px;
    background-color: var(--bg-input);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 5px 10px;
    width: 220px;
  }

  .search-icon-svg {
    color: var(--fg-muted);
    flex-shrink: 0;
  }

  .badge-mc {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .search-box input {
    background: transparent;
    border: none;
    outline: none;
    color: var(--fg-primary);
    font-size: 12px;
    width: 100%;
  }

  .search-box input::placeholder {
    color: var(--fg-muted);
  }

  .clear-btn {
    color: var(--fg-muted);
    font-size: 14px;
  }

  /* Table */
  .table-scroll {
    overflow-x: auto;
    max-height: 580px;
  }

  .strategy-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
    text-align: left;
  }

  thead {
    position: sticky;
    top: 0;
    background-color: var(--bg-surface-elevated);
    z-index: 10;
  }

  th {
    padding: 9px 12px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--fg-muted);
    border-bottom: 1px solid var(--border-muted);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
  }

  th:hover {
    color: var(--fg-primary);
  }

  .th-rank { width: 44px; text-align: center; }
  .th-num { text-align: right; }
  .th-pos { text-align: center; }
  .th-status { text-align: center; }
  .th-action { text-align: right; width: 70px; }

  tbody tr {
    border-bottom: 1px solid var(--border-subtle);
    transition: background-color 0.12s ease;
    cursor: pointer;
  }

  tbody tr:hover {
    background-color: var(--bg-surface-hover);
  }

  tbody tr.selected {
    background-color: rgba(56, 189, 248, 0.07);
    border-left: 3px solid var(--color-cyan);
  }

  td {
    padding: 10px 12px;
    white-space: nowrap;
  }

  .td-rank {
    text-align: center;
  }

  .rank-crown {
    display: inline-grid;
    place-items: center;
    width: 20px;
    height: 20px;
    border-radius: 4px;
    font-weight: 800;
    font-size: 11px;
  }

  .rank-crown.gold {
    background: rgba(245, 158, 11, 0.2);
    color: var(--color-amber);
    border: 1px solid var(--border-amber);
  }

  .rank-crown.silver {
    background: rgba(148, 163, 184, 0.15);
    color: #cbd5e1;
  }

  .rank-crown.bronze {
    background: rgba(180, 83, 9, 0.15);
    color: #d97706;
  }

  .rank-num {
    color: var(--fg-muted);
    font-size: 11px;
  }

  .name-box {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .s-title {
    font-weight: 600;
    color: var(--fg-primary);
    font-size: 13px;
  }

  .s-id {
    font-size: 10.5px;
    color: var(--fg-muted);
  }

  .td-num {
    text-align: right;
  }

  .winrate-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 3px;
  }

  .winrate-bar {
    width: 50px;
    height: 4px;
    background-color: var(--bg-base);
    border-radius: 2px;
    overflow: hidden;
  }

  .winrate-fill {
    height: 100%;
    background-color: var(--color-up);
  }

  .pos-badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.05);
    color: var(--fg-muted);
    font-weight: 600;
    font-size: 11.5px;
  }

  .pos-badge.has-pos {
    background: rgba(56, 189, 248, 0.12);
    color: var(--color-cyan);
    border: 1px solid var(--border-cyan);
  }

  .td-pos, .td-status {
    text-align: center;
  }

  .td-action {
    text-align: right;
  }

  .btn-inspect {
    padding: 4px 10px;
    border-radius: 4px;
    background-color: var(--bg-surface-elevated);
    border: 1px solid var(--border-subtle);
    font-size: 11px;
    font-weight: 500;
    color: var(--fg-secondary);
    transition: all 0.15s ease;
  }

  .btn-inspect:hover {
    color: var(--fg-primary);
    border-color: var(--border-muted);
    background-color: var(--bg-surface-hover);
  }

  .text-up {
    color: var(--color-up);
  }

  .text-down {
    color: var(--color-down);
  }

  .td-empty {
    text-align: center;
    padding: 30px;
    color: var(--fg-muted);
    font-style: italic;
  }
</style>
