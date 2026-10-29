<script>
  import { onMount, onDestroy } from 'svelte';
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent, formatUptime, calculateForexPnl } from '../lib/formatters.js';
  import { STRATEGIES_88 } from '../lib/strategies_data.js';
  import ExecutionNeuralVisualizer from './ExecutionNeuralVisualizer.svelte';

  // Filters State
  let marketFilter = $state('all'); // 'all', 'spot', 'futures', 'forex'
  let viewTab = $state('open'); // 'open' (Posisi Aktif) or 'closed' (Riwayat Selesai)
  let searchQuery = $state('');
  let sideFilter = $state('all'); // 'all', 'long', 'short'
  let outcomeFilter = $state('all'); // 'all', 'win', 'loss'

  // Data State
  let rawClosedTrades = $state([]);
  let rawOpenPositions = $state([]);
  let totalDbTrades = $state(9200);
  let isLoading = $state(true);
  let pollTimer = null;

  // Active Trade being inspected in Neural Network (Hanya aktif saat DIKLIK, tidak nyangkut saat hover)
  let selectedTrade = $state(null);
  let activeTrade = $derived(selectedTrade || null);

  // Real-time newly opened trade highlight (sinkron dengan pergerakan dot pulse)
  let latestOpenedTradeKey = $state(null);
  let latestTradeTimer = null;

  function getTimestamp(ts) {
    let n = Number(ts) || 0;
    if (n > 0 && n < 1e11) n *= 1000;
    return n;
  }

  function getPosKey(pos) {
    if (!pos) return '';
    const m = pos.mode || 'spot';
    const s = pos.strategy || '';
    const sym = pos.symbol || '';
    const ts = getTimestamp(pos.opened_at || pos.openedAt);
    return `${m}_${s}_${sym}_${ts}`;
  }

  function handleRealtimeNewTrade(trade) {
    if (!trade) return;
    latestOpenedTradeKey = getPosKey(trade);
    if (latestTradeTimer) clearTimeout(latestTradeTimer);
    latestTradeTimer = setTimeout(() => {
      latestOpenedTradeKey = null;
    }, 6000);
  }

  // Fetch real-time executions from API
  async function fetchExecutions() {
    try {
      const res = await fetch(`/api/executions?mode=${marketFilter}&limit=200`);
      if (res.ok) {
        const data = await res.json();
        rawClosedTrades = data.trades || [];
        rawOpenPositions = data.open_positions || [];
        totalDbTrades = data.total_db_trades || 9200;
        isLoading = false;
      }
    } catch (err) {
      console.error('Failed to fetch executions:', err);
    }
  }

  onMount(() => {
    fetchExecutions();
    pollTimer = setInterval(fetchExecutions, 1000);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
    if (latestTradeTimer) clearTimeout(latestTradeTimer);
  });

  // Re-fetch when market filter changes
  $effect(() => {
    const _m = marketFilter;
    fetchExecutions();
  });

  // Realtime Live Open Positions (Instant WebSocket & API Merge, Urutan Terbaru di Atas)
  let allLiveOpenPositions = $derived.by(() => {
    const stratMap = new Map();
    STRATEGIES_88.forEach(s => {
      stratMap.set(s.id.toLowerCase(), s.name);
      stratMap.set(s.name.toLowerCase(), s.name);
    });

    for (const acct of [
      ...(arena.spot?.accounts || []),
      ...(arena.futures?.accounts || []),
      ...(arena.forex?.accounts || [])
    ]) {
      if (acct?.id && acct?.name) {
        stratMap.set(acct.id.toLowerCase(), acct.name);
      }
    }

    const list = [];
    const seen = new Set();

    // 1. Ambil dari arena store (WebSocket Realtime)
    const storePositions = [
      ...(arena.spot?.positions || []).map(p => ({ ...p, mode: 'spot' })),
      ...(arena.futures?.positions || []).map(p => ({ ...p, mode: 'futures' })),
      ...(arena.forex?.positions || []).map(p => ({ ...p, mode: 'forex' }))
    ];

    for (const p of storePositions) {
      const sym = (p.symbol || '').toUpperCase();
      const strat = (p.strategy || '').toLowerCase();
      const key = getPosKey(p);
      if (seen.has(key)) continue;
      seen.add(key);

      const stratName = stratMap.get(strat) || p.strategy_name || p.strategy || 'Quantitative Strategy';
      const isLong = (p.side === 1 || p.side === 'LONG' || p.side_label === 'LONG');
      const sideLabel = isLong ? 'LONG' : 'SHORT';
      const side = isLong ? 1 : -1;
      const mark = arena.prices[sym] ?? p.mark ?? p.entry;

      let upnl = p.upnl;
      if (p.mode === 'forex') {
        const lot = p.lot || 0.10;
        upnl = calculateForexPnl(sym, p.entry, mark, sideLabel, lot, arena.prices);
      } else if (p.qty && mark && p.entry) {
        upnl = (mark - p.entry) * p.qty * side;
      }

      list.push({
        ...p,
        symbol: sym,
        strategy: p.strategy,
        strategy_name: stratName,
        side,
        side_label: sideLabel,
        mark,
        upnl: Math.round(upnl * 100) / 100,
        opened_at: getTimestamp(p.opened_at),
        risk_reward: p.risk_reward || (p.target && p.stop ? `1:${(Math.abs(p.target - p.entry) / Math.max(Math.abs(p.entry - p.stop), 1e-4)).toFixed(1)}` : '1:1.8')
      });
    }

    // 2. Gabungkan dengan rawOpenPositions dari backend jika ada yang belum tercakup
    for (const p of rawOpenPositions) {
      const sym = (p.symbol || '').toUpperCase();
      const strat = (p.strategy || '').toLowerCase();
      const key = getPosKey(p);
      if (seen.has(key)) continue;
      seen.add(key);

      const stratName = stratMap.get(strat) || p.strategy_name || p.strategy || 'Quantitative Strategy';
      const isLong = (p.side === 1 || p.side_label === 'LONG');
      const sideLabel = isLong ? 'LONG' : 'SHORT';
      const mark = arena.prices[sym] ?? p.mark ?? p.entry;

      list.push({
        ...p,
        symbol: sym,
        strategy_name: stratName,
        side_label: sideLabel,
        mark,
        opened_at: getTimestamp(p.opened_at),
        risk_reward: p.risk_reward || '1:1.8'
      });
    }

    // SANGAT PENTING: URUTAN TERBARU DIATASNYA (Opened At Descending + Prioritas Trade Baru)
    list.sort((a, b) => {
      const aIsNew = latestOpenedTradeKey && latestOpenedTradeKey === getPosKey(a) ? 1 : 0;
      const bIsNew = latestOpenedTradeKey && latestOpenedTradeKey === getPosKey(b) ? 1 : 0;
      if (bIsNew !== aIsNew) return bIsNew - aIsNew;
      return getTimestamp(b.opened_at) - getTimestamp(a.opened_at);
    });

    return list;
  });

  // Filtered Open Positions (Live MTM & Urutan Terbaru di Atas)
  let filteredOpenPositions = $derived.by(() => {
    let list = allLiveOpenPositions;
    if (marketFilter !== 'all') {
      list = list.filter(p => p.mode === marketFilter);
    }
    if (sideFilter === 'long') {
      list = list.filter(p => p.side === 1 || p.side_label === 'LONG');
    } else if (sideFilter === 'short') {
      list = list.filter(p => p.side === -1 || p.side_label === 'SHORT');
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(p =>
        (p.symbol || '').toLowerCase().includes(q) ||
        (p.strategy || '').toLowerCase().includes(q) ||
        (p.strategy_name || '').toLowerCase().includes(q)
      );
    }
    // Selalu pastikan urutan terbaru di atas: trade baru (BARU ⚡) selalu paling pertama
    return [...list].sort((a, b) => {
      const aIsNew = latestOpenedTradeKey && latestOpenedTradeKey === getPosKey(a) ? 1 : 0;
      const bIsNew = latestOpenedTradeKey && latestOpenedTradeKey === getPosKey(b) ? 1 : 0;
      if (bIsNew !== aIsNew) return bIsNew - aIsNew;
      return getTimestamp(b.opened_at) - getTimestamp(a.opened_at);
    });
  });

  // Filtered Closed Trades
  let filteredClosedTrades = $derived.by(() => {
    let list = rawClosedTrades;
    if (marketFilter !== 'all') {
      list = list.filter(t => t.mode === marketFilter);
    }
    if (sideFilter === 'long') {
      list = list.filter(t => t.side === 1);
    } else if (sideFilter === 'short') {
      list = list.filter(t => t.side === -1);
    }
    if (outcomeFilter === 'win') {
      list = list.filter(t => t.pnl > 0);
    } else if (outcomeFilter === 'loss') {
      list = list.filter(t => t.pnl <= 0);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(t =>
        (t.symbol || '').toLowerCase().includes(q) ||
        (t.strategy || '').toLowerCase().includes(q) ||
        (t.strategy_name || '').toLowerCase().includes(q)
      );
    }
    return list;
  });

  // Statistical KPIs
  let kpis = $derived.by(() => {
    const closed = rawClosedTrades;
    const wins = closed.filter(t => t.pnl > 0).length;
    const losses = closed.filter(t => t.pnl <= 0).length;
    const totalPnl = closed.reduce((acc, t) => acc + (t.pnl || 0), 0);
    const winRate = closed.length > 0 ? (wins / closed.length) * 100 : 0;

    const openCount = allLiveOpenPositions.length;
    const openFloatingPnl = allLiveOpenPositions.reduce((acc, p) => acc + (p.upnl || 0), 0);

    return {
      totalClosed: closed.length,
      wins,
      losses,
      winRate: winRate.toFixed(1),
      totalPnl,
      openCount,
      openFloatingPnl
    };
  });

  // Format Helper for Timestamps
  function formatTime(ts) {
    if (!ts) return '-';
    const ms = getTimestamp(ts);
    const d = new Date(ms);
    const pad = (n) => n.toString().padStart(2, '0');
    return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  function formatDate(ts) {
    if (!ts) return '-';
    const d = new Date(Number(ts));
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    const pad = (n) => n.toString().padStart(2, '0');
    return `${d.getDate()} ${months[d.getMonth()]}, ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }

  // Quick Pair Filter Click
  function applyPairFilter(sym) {
    searchQuery = sym;
  }
</script>

<div class="neural-exec-root">

  <div class="exec-page-container">
    <!-- Header Hero Banner -->
    <div class="exec-hero-banner">
      <div class="hero-text-col">
        <h1>Statistik Eksekusi Multi-Pasar</h1>

        <!-- KPI Strip -->
        <div class="kpi-strip mono">
          <div class="kpi-cell">
            <span class="kpi-lbl">TOTAL TRADE DB</span>
            <span class="kpi-val text-gold">{totalDbTrades.toLocaleString()}</span>
            <span class="kpi-sub">Audited Executions</span>
          </div>
          <div class="kpi-cell">
            <span class="kpi-lbl">POSISI TERBUKA (LIVE)</span>
            <span class="kpi-val text-cyan">{kpis.openCount}</span>
            <span class="kpi-sub">Sedang Aktif di Pasar</span>
          </div>
          <div class="kpi-cell">
            <span class="kpi-lbl">WIN RATE KONTINU</span>
            <span class="kpi-val text-emerald">{kpis.winRate}%</span>
            <span class="kpi-sub">{kpis.wins}W / {kpis.losses}L</span>
          </div>
          <div class="kpi-cell">
            <span class="kpi-lbl">REALIZED NET ALPHA</span>
            <span class="kpi-val {kpis.totalPnl >= 0 ? 'up' : 'down'}">
              {kpis.totalPnl >= 0 ? '+' : ''}{formatUSD(kpis.totalPnl)}
            </span>
            <span class="kpi-sub">Kumulatif 3 Pasar</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 1. The Interactive Neural Network Architecture -->
    <div class="neural-visual-section">
      <div class="section-title-bar">
        <div class="bar-left">
          <span class="bar-tag mono">PIPELINE ARSITEKTUR</span>
          <h3>Deep Quantitative Neural Network</h3>
        </div>
        {#if activeTrade}
          <div class="active-trade-pill mono">
            <span class="glow-dot"></span>
            <span>INSPEKSI JALUR: <strong>{activeTrade.strategy_name || activeTrade.strategy}</strong> ({activeTrade.symbol} {activeTrade.side_label || (activeTrade.side === 1 ? 'LONG' : 'SHORT')})</span>
            <button
              type="button"
              class="clear-trade-btn"
              onclick={() => { selectedTrade = null; }}
            >✕</button>
          </div>
        {:else}
          <span class="bar-hint mono">💡 Klik baris trade di bawah untuk melihat rute sinyal neuralnya</span>
        {/if}
      </div>

      <div class="nn-stage-wrap">
        <ExecutionNeuralVisualizer
          {activeTrade}
          onSelectPair={(sym) => {
            selectedTrade = null;
            applyPairFilter(sym);
          }}
          onClearTrade={() => {
            selectedTrade = null;
          }}
          onNewTrade={(t) => handleRealtimeNewTrade(t)}
        />
      </div>
    </div>

    <!-- 2. Master Execution Control & Table -->
    <div class="execution-table-card">
      <!-- Toolbar & Filters -->
      <div class="card-toolbar">
        <!-- Market Switcher Tabs -->
        <div class="market-pills mono">
          <button
            type="button"
            class="pill-btn {marketFilter === 'all' ? 'active' : ''}"
            onclick={() => marketFilter = 'all'}
          >
            Semua Pasar (Tri-Market)
          </button>
          <button
            type="button"
            class="pill-btn {marketFilter === 'spot' ? 'active active-spot' : ''}"
            onclick={() => marketFilter = 'spot'}
          >
            <span class="dot dot-amber"></span> Crypto Spot
          </button>
          <button
            type="button"
            class="pill-btn {marketFilter === 'futures' ? 'active active-futures' : ''}"
            onclick={() => marketFilter = 'futures'}
          >
            <span class="dot dot-cyan"></span> Crypto Futures
          </button>
          <button
            type="button"
            class="pill-btn {marketFilter === 'forex' ? 'active active-forex' : ''}"
            onclick={() => marketFilter = 'forex'}
          >
            <span class="dot dot-emerald"></span> Forex & Metals
          </button>
        </div>
        <span>{kpis.openCount} Posisi Terbuka</span>
      </div>

      <!-- Secondary Search & Attribute Filter Bar -->
      <div class="secondary-filter-bar">
        <div class="search-wrap">
          <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            placeholder="Cari pair (XAU, BTC, EUR) atau nama strategi..."
            bind:value={searchQuery}
            class="search-input mono"
          />
          {#if searchQuery}
            <button type="button" class="clear-search" onclick={() => searchQuery = ''}>✕</button>
          {/if}
        </div>

        <div class="quick-pair-pills mono">
          <span class="pair-lbl">Pair Cepat:</span>
          {#each ['XAUUSD', 'BTCUSDT', 'ETHUSDT', 'EURUSD', 'GBPUSD', 'USDJPY', 'XTIUSD', 'SOLUSDT'] as sym}
            <button
              type="button"
              class="quick-sym-btn {searchQuery === sym ? 'active' : ''}"
              onclick={() => applyPairFilter(sym)}
            >
              {sym}
            </button>
          {/each}
        </div>

        <div class="side-filter-group mono">
          <select bind:value={sideFilter} class="filter-select">
            <option value="all">Semua Arah</option>
            <option value="long">🟢 LONG / BUY</option>
            <option value="short">🔴 SHORT / SELL</option>
          </select>

          {#if viewTab === 'closed'}
            <select bind:value={outcomeFilter} class="filter-select">
              <option value="all">Semua Hasil</option>
              <option value="win">Win (+PnL)</option>
              <option value="loss">Loss (-PnL)</option>
            </select>
          {/if}
        </div>
      </div>

      <!-- Execution Data Table -->
      <div class="table-responsive">
        {#if viewTab === 'open'}
          <!-- Open Positions Table -->
          <table class="exec-table mono">
            <thead>
              <tr>
                <th class="l">Waktu Buka</th>
                <th class="c">Pasar</th>
                <th class="l">Model Strategi</th>
                <th class="l">Pair / Simbol</th>
                <th class="c">Arah</th>
                <th class="l">Rute Neural</th>
              </tr>
            </thead>
            <tbody>
              {#if filteredOpenPositions.length === 0}
                <tr>
                  <td colspan="6" class="empty-cell">
                    Tidak ada posisi aktif yang sesuai filter.
                  </td>
                </tr>
              {:else}
                {#each filteredOpenPositions as pos (getPosKey(pos))}
                  {@const isNewTrade = Boolean(latestOpenedTradeKey && latestOpenedTradeKey === getPosKey(pos))}
                  <tr
                    class="exec-row {activeTrade === pos ? 'row-highlighted' : ''} {isNewTrade ? 'row-new-entry' : ''}"
                    onclick={() => selectedTrade = (selectedTrade === pos ? null : pos)}
                  >
                    <td class="muted">
                      {#if isNewTrade}
                        <span class="live-dot-pulse" title="Trade baru aktif!"></span>
                      {/if}
                      {formatTime(pos.opened_at)}
                    </td>
                    <td class="c">
                      {#if pos.mode === 'spot'}
                        <span class="market-tag tag-spot">SPOT</span>
                      {:else if pos.mode === 'futures'}
                        <span class="market-tag tag-futures">FUTURES</span>
                      {:else}
                        <span class="market-tag tag-forex">FOREX & METALS</span>
                      {/if}
                    </td>
                    <td class="font-bold text-white">
                      {pos.strategy_name || pos.strategy}
                    </td>
                    <td class="font-bold text-cyan">{pos.symbol}</td>
                    <td class="c">
                      <span class="side-badge {pos.side_label === 'LONG' || pos.side === 1 ? 'side-long' : 'side-short'}">
                        {pos.side_label || (pos.side === 1 ? 'LONG' : 'SHORT')}
                      </span>
                    </td>
                    <td class="l">
                      <span class="neural-trace-btn {activeTrade === pos ? 'trace-active' : ''}" title="Klik untuk sorot rute di Neural Network">
                        {activeTrade === pos ? 'Sedang Disorot' : 'Jalur Neural ➔'}
                      </span>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .neural-exec-root {
    min-height: 100vh;
    background: #04070d;
    color: #e2e8f0;
    padding-bottom: 60px;
  }
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .exec-page-container {
    max-width: 1740px;
    margin: 24px auto 0;
    padding: 0 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  /* Hero Banner */
  .exec-hero-banner {
    background: linear-gradient(135deg, #090e1a 0%, #060910 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 24px 28px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  }


  .hero-text-col h1 {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 8px 0;
    letter-spacing: -0.01em;
  }

  .kpi-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    background: rgba(0, 0, 0, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 16px 20px;
  }

  .kpi-cell {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .kpi-lbl {
    font-size: 9.5px;
    color: #64748b;
    font-weight: 800;
    letter-spacing: 0.08em;
  }

  .kpi-val {
    font-size: 20px;
    font-weight: 800;
  }

  .kpi-sub {
    font-size: 10px;
    color: #94a3b8;
  }

  /* Neural Network Section */
  .neural-visual-section {
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  }

 
  .section-title-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .bar-tag {
    font-size: 10px;
    font-weight: 800;
    color: #f59e0b;
    letter-spacing: 0.08em;
    display: block;
    margin-bottom: 4px;
  }

  .bar-left h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
  }

  .active-trade-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #fbbf24;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 11px;
    animation: pulseBorder 1.5s infinite;
  }

  @keyframes pulseBorder {
    0%, 100% { border-color: rgba(245, 158, 11, 0.4); }
    50% { border-color: rgba(245, 158, 11, 0.9); }
  }

  .clear-trade-btn {
    background: transparent;
    border: none;
    color: #fbbf24;
    cursor: pointer;
    font-weight: bold;
    font-size: 12px;
    padding: 0 4px;
  }

  .bar-hint {
    font-size: 11px;
    color: #64748b;
  }

  .nn-stage-wrap {
    background: #05080e;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    overflow: hidden;
  }

  /* Execution Table Card */
  .execution-table-card {
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
  }

  .card-toolbar {
    padding: 16px 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 14px;
    background: #0a0f1a;
  }

  .market-pills {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .pill-btn {
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }

  .pill-btn:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  .pill-btn.active {
    background: #1e293b;
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.35);
  }

  .pill-btn.active-spot {
    border-color: rgba(245, 158, 11, 0.6);
    color: #fbbf24;
    background: rgba(245, 158, 11, 0.12);
  }

  .pill-btn.active-futures {
    border-color: rgba(6, 182, 212, 0.6);
    color: #38bdf8;
    background: rgba(6, 182, 212, 0.12);
  }

  .pill-btn.active-forex {
    border-color: rgba(16, 185, 129, 0.6);
    color: #34d399;
    background: rgba(16, 185, 129, 0.12);
  }

  .dot { width: 6px; height: 6px; border-radius: 50%; }
  .dot-amber { background: #f59e0b; }
  .dot-cyan { background: #06b6d4; }
  .dot-emerald { background: #10b981; }


  /* Secondary Search Bar */
  .secondary-filter-bar {
    padding: 12px 20px;
    background: #080c14;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }

  .search-wrap {
    position: relative;
    display: flex;
    align-items: center;
    width: 320px;
  }

  .search-icon {
    position: absolute;
    left: 10px;
    color: #64748b;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    background: #05080e;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 6px 30px 6px 32px;
    font-size: 11px;
    color: #ffffff;
  }

  .search-input:focus {
    outline: none;
    border-color: #f59e0b;
  }

  .clear-search {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    color: #64748b;
    cursor: pointer;
  }

  .quick-pair-pills {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .pair-lbl {
    font-size: 10px;
    color: #64748b;
    font-weight: 700;
  }

  .quick-sym-btn {
    background: #0e1524;
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: #94a3b8;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 10px;
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .quick-sym-btn:hover, .quick-sym-btn.active {
    background: #17243c;
    color: #f59e0b;
    border-color: rgba(245, 158, 11, 0.4);
  }

  .side-filter-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .filter-select {
    background: #05080e;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #cbd5e1;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 11px;
    cursor: pointer;
  }

  /* Table */
  .table-responsive {
    overflow-x: auto;
    max-height: 600px;
    overflow-y: auto;
  }

  .exec-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
    white-space: nowrap;
  }

  .exec-table thead th {
    background: #060910;
    color: #64748b;
    font-weight: 800;
    font-size: 10px;
    letter-spacing: 0.05em;
    padding: 10px 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .exec-row {
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    cursor: pointer;
    transition: background 0.12s ease;
  }

  .exec-row:hover {
    background: rgba(255, 255, 255, 0.035);
  }

  .exec-row.row-highlighted {
    background: rgba(245, 158, 11, 0.08);
    border-left: 3px solid #f59e0b;
  }

  .exec-row.row-new-entry {
    background: rgba(16, 185, 129, 0.16) !important;
    border-left: 3px solid #10b981 !important;
    animation: pulseNewRow 2s ease-in-out infinite;
  }

  @keyframes pulseNewRow {
    0%, 100% {
      background: rgba(16, 185, 129, 0.16);
    }
    50% {
      background: rgba(16, 185, 129, 0.32);
      box-shadow: inset 0 0 14px rgba(16, 185, 129, 0.25);
    }
  }

  .live-dot-pulse {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    margin-right: 6px;
    animation: blink 0.8s ease-in-out infinite alternate;
  }


  .exec-table td {
    padding: 10px 14px;
  }

  .market-tag {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 9.5px;
    font-weight: 800;
  }

  .tag-spot {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .tag-futures {
    background: rgba(6, 182, 212, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(6, 182, 212, 0.3);
  }

  .tag-forex {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .side-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 9.5px;
    font-weight: 800;
  }

  .side-long {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
  }

  .side-short {
    background: rgba(244, 63, 94, 0.15);
    color: #f87171;
    border: 1px solid rgba(244, 63, 94, 0.35);
  }

  .neural-trace-btn {
    color: #94a3b8;
    font-size: 10px;
    transition: color 0.12s ease;
  }

  .exec-row:hover .neural-trace-btn,
  .exec-row.row-highlighted .neural-trace-btn {
    color: #f59e0b;
    font-weight: bold;
  }

  .empty-cell {
    text-align: center;
    padding: 40px;
    color: #64748b;
  }

  .text-white { color: #ffffff; }
  .text-cyan { color: #38bdf8; }
  .text-gold { color: #f59e0b; }
  .text-emerald { color: #34d399; }
  .font-bold { font-weight: 700; }
  .muted { color: #64748b; }
  .up { color: #10b981; }
  .down { color: #f43f5e; }
  .mono { font-family: monospace; }

  @media (max-width: 900px) {
    .kpi-strip {
      grid-template-columns: 1fr 1fr;
    }
    .card-toolbar {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>

