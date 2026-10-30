<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent } from '../lib/formatters.js';
  import { getStrategyCategory } from '../lib/constants.js';

  let currentSort = $state('balance'); // 'balance' | 'winrate' | 'pf' | 'trades' | 'dd'
  let currentFamily = $state('all'); // 'all' | string
  let searchQuery = $state('');

  const FAMILIES = [
    'all',
    'Breakout',
    'Fibonacci',
    'ICT',
    'Mean reversion',
    'Momentum',
    'Order flow',
    'Oscillator',
    'Price action',
    'Statistik',
    'Struktur',
    'Trailing',
    'Trend',
    'Volatility',
    'Volume profile',
    'Waktu',
  ];

  let rawAccounts = $derived(arena.activeAccounts);
  let curves = $derived(arena.activeCurves);

  // Overall rank mapping (1-indexed based strictly on balance)
  let rankMap = $derived.by(() => {
    const sorted = [...rawAccounts].sort((a, b) => (b.balance ?? b.cash ?? b.equity ?? 0) - (a.balance ?? a.cash ?? a.equity ?? 0));
    const m = new Map();
    sorted.forEach((a, i) => m.set(a.id, i + 1));
    return m;
  });

  // Filter and Sort for the Grid Display
  let displayedAccounts = $derived.by(() => {
    let list = rawAccounts;
    if (currentFamily !== 'all') {
      const famLower = currentFamily.toLowerCase();
      list = list.filter((a) => {
        const cat = (a.family || getStrategyCategory(a.id)).toLowerCase();
        if (famLower.startsWith('fibo') && cat.startsWith('fibo')) return true;
        return cat.includes(famLower);
      });
    }

    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter((a) => {
        const name = (a.name || '').toLowerCase();
        const id = (a.id || '').toLowerCase();
        const cat = (a.family || getStrategyCategory(a.id)).toLowerCase();
        return name.includes(q) || id.includes(q) || cat.includes(q);
      });
    }

    const copy = [...list];
    copy.sort((a, b) => {
      if (currentSort === 'balance' || currentSort === 'equity') return (b.balance ?? b.cash ?? b.equity ?? 0) - (a.balance ?? a.cash ?? a.equity ?? 0);
      if (currentSort === 'winrate') {
        const wrA = a.trades > 0 ? a.wins / a.trades : 0;
        const wrB = b.trades > 0 ? b.wins / b.trades : 0;
        return wrB - wrA;
      }
      if (currentSort === 'pf') {
        const pfA = a.gross_loss > 0 ? a.gross_win / a.gross_loss : (a.gross_win > 0 ? 999 : 0);
        const pfB = b.gross_loss > 0 ? b.gross_win / b.gross_loss : (b.gross_win > 0 ? 999 : 0);
        return pfB - pfA;
      }
      if (currentSort === 'trades') return (b.trades ?? 0) - (a.trades ?? 0);
      if (currentSort === 'dd') return (a.max_dd ?? 0) - (b.max_dd ?? 0);
      return (b.balance ?? b.cash ?? b.equity ?? 0) - (a.balance ?? a.cash ?? a.equity ?? 0);
    });

    return copy;
  });

  function selectStrategy(id) {
    arena.selectedStrategyId = id;
  }

  // Coming Soon / In R&D Strategies
  let activeComingSoon = $state(null);

  const COMING_SOON_STRATEGIES = [
    {
      id: 'other',
      name: 'Other Strategy',
      family: 'Other Strategy',
      badge: 'Other Strategy',
      eta: 'SOON',
      desc: 'SOON',
      curve: 'M 0,11 L 30,11 L 45,4 L 60,18 L 75,7 L 90,14 L 110,11 L 180,11',
      dotX: 90,
      dotY: 14,
    },
  ];

  let displayedComingSoon = $derived.by(() => {
    let list = COMING_SOON_STRATEGIES;
    if (currentFamily !== 'all') {
      const famLower = currentFamily.toLowerCase();
      list = list.filter((s) => s.family.toLowerCase().includes(famLower));
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter((s) =>
        (s.name || '').toLowerCase().includes(q) ||
        (s.id || '').toLowerCase().includes(q) ||
        (s.family || '').toLowerCase().includes(q)
      );
    }
    return list;
  });

  // Calculate SVG sparkline path from curve numbers with a precise 24-hour range
  function calculateSpark(id, curBal) {
    const raw = curves[id] || [];
    const width = 180;
    const height = 22;
    const now = Date.now();
    const windowMs = 24 * 3600 * 1000;
    const baseEq = arena.startEquity || 1000;
    const liveBal = typeof curBal === 'number' ? curBal : baseEq;

    // Normalize points array
    let pts = [];
    if (Array.isArray(raw) && raw.length > 0) {
      pts = raw.map((p, idx) => {
        if (Array.isArray(p) && p.length >= 2) {
          return { ts: Number(p[0]), equity: Number(p[1]) };
        } else if (p && typeof p === 'object' && 'ts' in p && 'equity' in p) {
          return { ts: Number(p.ts), equity: Number(p.equity) };
        } else {
          const val = typeof p === 'number' ? p : Number(p) || baseEq;
          const fakeTs = now - windowMs + (idx / Math.max(raw.length - 1, 1)) * windowMs;
          return { ts: fakeTs, equity: val };
        }
      }).sort((a, b) => a.ts - b.ts);
    }

    if (pts.length === 0) {
      pts = [
        { ts: now - windowMs, equity: baseEq },
        { ts: now, equity: liveBal },
      ];
    }

    // Always ensure current live balance is attached at now
    const lastPt = pts[pts.length - 1];
    if (now - lastPt.ts > 4000 || Math.abs(liveBal - lastPt.equity) > 0.01) {
      pts.push({ ts: now, equity: liveBal });
    }

    const endTs = Math.max(now, pts[pts.length - 1].ts);
    const earliestDataTs = pts[0].ts;

    // Rentang waktu 24 jam konsisten dengan StrategyDossier
    const startTs = Math.max(endTs - windowMs, earliestDataTs);
    const spanMs = Math.max(endTs - startTs, 60000);

    // Filter titik dalam jendela 24 jam
    pts = pts.filter((p) => p.ts >= startTs);
    if (pts.length === 0) {
      pts = [{ ts: startTs, equity: liveBal }, { ts: endTs, equity: liveBal }];
    }
    // Pastikan ada titik di startTs agar kurva membentang dari paling kiri
    if (pts[0].ts > startTs + 60000) {
      pts.unshift({ ts: startTs, equity: pts[0].equity });
    }

    // Skala Y konsisten dengan StrategyDossier (menyertakan baseline modal awal & padding)
    const equities = pts.map((p) => p.equity);
    let minV = Math.min(...equities, baseEq * 0.995);
    let maxV = Math.max(...equities, baseEq * 1.005);
    const vSpan = maxV - minV || 50;
    minV = minV - vSpan * 0.08;
    maxV = maxV + vSpan * 0.08;
    const range = maxV - minV;

    const coords = pts.map((p) => {
      const x = Math.max(0, Math.min(1, (p.ts - startTs) / spanMs)) * width;
      const y = height - 3 - Math.max(0, Math.min(1, (p.equity - minV) / range)) * (height - 6);
      return [x, y];
    });

    const path = coords.reduce(
      (acc, [x, y], i) => (i === 0 ? `M ${x.toFixed(1)},${y.toFixed(1)}` : `${acc} L ${x.toFixed(1)},${y.toFixed(1)}`),
      ''
    );
    const [lx, ly] = coords[coords.length - 1];
    const area = `${path} L ${width},${height} L 0,${height} Z`;

    return { path, area, lastX: lx, lastY: ly };
  }
</script>

<section class="board panel">
  <!-- Papan Peringkat Header -->
  <div class="phead">
    <div class="phead-left">
      <h2>
        Papan peringkat — {#if searchQuery.trim() || currentFamily !== 'all'}{displayedAccounts.length} dari {/if}{rawAccounts.length} strategi {arena.mode === 'spot' ? 'spot' : (arena.mode === 'futures' ? 'futures' : 'forex & metals')}, modal {formatUSD(arena.startEquity, 0)} (Saldo Bersih / Balance)
      </h2>
    </div>

    <div class="phead-right">
      <!-- Search Input Filter -->
      <div class="search-box">
        <svg class="search-icon-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <input
          type="text"
          placeholder="Cari strategi (nama / id)..."
          bind:value={searchQuery}
          onkeydown={(e) => { if (e.key === 'Escape') searchQuery = ''; }}
        />
        {#if searchQuery}
          <button
            type="button"
            class="clear-btn"
            onclick={() => (searchQuery = '')}
            aria-label="Hapus pencarian"
          >×</button>
        {/if}
      </div>

      <!-- Sorting buttons -->
      <div class="seg" role="radiogroup" aria-label="Urutkan strategi">
        <button
          type="button"
          class="seg-btn {currentSort === 'balance' || currentSort === 'equity' ? 'active' : ''}"
          onclick={() => (currentSort = 'balance')}
        >
          Balance
        </button>
        <button
          type="button"
          class="seg-btn {currentSort === 'winrate' ? 'active' : ''}"
          onclick={() => (currentSort = 'winrate')}
        >
          Win Rate
        </button>
        <button
          type="button"
          class="seg-btn {currentSort === 'pf' ? 'active' : ''}"
          onclick={() => (currentSort = 'pf')}
        >
          Profit Factor
        </button>
        <button
          type="button"
          class="seg-btn {currentSort === 'trades' ? 'active' : ''}"
          onclick={() => (currentSort = 'trades')}
        >
          Trade
        </button>
        <button
          type="button"
          class="seg-btn {currentSort === 'dd' ? 'active' : ''}"
          onclick={() => (currentSort = 'dd')}
        >
          Drawdown
        </button>
      </div>
    </div>
  </div>

  <!-- Category filter horizontal pill track -->
  <div class="fam-track">
    {#each FAMILIES as fam}
      <button
        type="button"
        class="fam-btn {currentFamily === fam ? 'active' : ''}"
        onclick={() => (currentFamily = fam)}
      >
        {fam === 'all' ? 'Semua' : fam}
      </button>
    {/each}
  </div>

  <!-- The 7-Column Card Grid (.rows / .row) -->
  <div class="rows">
    {#each displayedAccounts as a (a.id)}
      {@const rank = rankMap.get(a.id) || 1}
      {@const isSelected = arena.selectedStrategyId === a.id}
      {@const curBal = a.balance ?? a.cash ?? a.equity ?? arena.startEquity}
      {@const isPositive = curBal >= arena.startEquity}
      {@const spark = calculateSpark(a.id, curBal)}
      {@const strokeColor = isPositive ? '#10b981' : '#f43f5e'}
      {@const fillColor = isPositive ? 'rgba(16, 185, 129, 0.16)' : 'rgba(244, 63, 94, 0.16)'}

      <div
        class="row {isSelected ? 'selected' : ''}"
        role="button"
        tabindex="0"
        aria-pressed={isSelected}
        onclick={() => selectStrategy(a.id)}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') selectStrategy(a.id); }}
      >
        <!-- Line 1: Rank, Name, MC Pill, Return % -->
        <div class="r1">
          <span class="pos mono">#{rank}</span>
          <span class="nm" title={a.name}>{a.name}</span>
          {#if a.refillCount > 0}
            <span class="chip-mc" title="Strategi ini telah mengalami margin call dan direfill {a.refillCount}x">
              MC {a.refillCount}x
            </span>
          {/if}
          {#if currentSort === 'winrate'}
            {@const wr = a.trades > 0 ? (a.wins / a.trades) * 100 : 0}
            <span class="ret mono {wr >= 50 ? 'up' : 'down'}" title="Win Rate: {wr.toFixed(1)}% ({a.wins}/{a.trades} menang)">
              {wr.toFixed(1)}% WR
            </span>
          {:else if currentSort === 'pf'}
            {@const pf = a.gross_loss > 0 ? (a.gross_win / a.gross_loss) : (a.gross_win > 0 ? 99 : 0)}
            <span class="ret mono {pf >= 1.0 ? 'up' : 'down'}" title="Profit Factor: {pf >= 99 ? '∞' : pf.toFixed(2)}">
              PF {pf >= 99 ? '∞' : pf.toFixed(2)}
            </span>
          {:else if currentSort === 'dd'}
            {@const ddPct = (a.max_dd ?? 0) * 100}
            <span class="ret mono down" title="Max Drawdown: -{ddPct.toFixed(1)}%">
              -{ddPct.toFixed(1)}% DD
            </span>
          {:else if currentSort === 'trades'}
            <span class="ret mono" style="color: #94a3b8;" title="Total Trades: {a.trades ?? 0}">
              {a.trades ?? 0} trd
            </span>
          {:else}
            <span class="ret mono {isPositive ? 'up' : 'down'}">
              {formatPercent(a.returnPct ?? ((curBal - arena.startEquity) / arena.startEquity) * 100)}
            </span>
          {/if}
        </div>

        <!-- Center: Sparkline SVG curve -->
        <div class="spark-wrap">
          <svg
            class="spark"
            viewBox="0 0 180 22"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path d={spark.area} fill={fillColor} />
            <path d={spark.path} fill="none" stroke={strokeColor} stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
            <circle cx={spark.lastX} cy={spark.lastY} r="2.2" fill={strokeColor} />
          </svg>
        </div>

        <!-- Line 2: Category Family and Current Balance -->
        <div class="r2">
          <span class="fam">{a.family || getStrategyCategory(a.id)}</span>
          <span class="grow"></span>
          <span class="eq mono" title="Saldo Bersih Terealisasi: {formatUSD(curBal)}">{formatUSD(curBal, 0)}</span>
        </div>
      </div>
    {/each}

    <!-- Coming Soon / R&D Strategy Blocks -->
    {#each displayedComingSoon as cs (cs.id)}
      <div
        class="row row-cs"
        role="button"
        tabindex="0"
        title="{cs.name} ({cs.family}): {cs.desc} — Klik untuk detail model"
        onclick={() => (activeComingSoon = cs)}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') activeComingSoon = cs; }}
      >
        <!-- Line 1: CS Tag, Name, R&D Badge -->
        <div class="r1">
          <span class="pos-cs mono">SOON</span>
          <span class="nm cs-nm" title={cs.name}>{cs.name}</span>
          <span class="cs-tag mono">{cs.badge}</span>
        </div>

        <!-- Center: R&D Simulation Pulse Waveform -->
        <div class="spark-wrap">
          <svg
            class="spark spark-cs"
            viewBox="0 0 180 22"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path d={cs.curve} fill="none" stroke="rgba(245, 158, 11, 0.45)" stroke-width="1.3" stroke-dasharray="3,3" />
            <circle cx={cs.dotX} cy={cs.dotY} r="2.2" fill="#f59e0b" class="pulse-dot" />
          </svg>
        </div>

        <!-- Line 2: Category Family and Stage Status -->
        <div class="r2">
          <span class="fam cs-fam">{cs.family}</span>
          <span class="grow"></span>
          <span class="cs-status mono">{cs.eta}</span>
        </div>
      </div>
    {/each}

    {#if displayedAccounts.length === 0 && displayedComingSoon.length === 0}
      <div class="no-results">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
        <p>Tidak ada strategi yang cocok dengan pencarian "<strong>{searchQuery}</strong>"{currentFamily !== 'all' ? ` di kategori ${currentFamily}` : ''}</p>
        <button type="button" class="btn-clear-filter" onclick={() => { searchQuery = ''; currentFamily = 'all'; }}>
          Reset Filter & Pencarian
        </button>
      </div>
    {/if}
  </div>
</section>

{#if activeComingSoon}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="cs-modal-backdrop" onclick={() => (activeComingSoon = null)}>
    <div class="cs-modal-dialog" onclick={(e) => e.stopPropagation()}>
      <div class="cs-modal-head">
        <div class="cs-m-title">
          <span class="chip-cs mono">{activeComingSoon.badge}</span>
          <h3>{activeComingSoon.name}</h3>
        </div>
        <button class="cs-m-close" onclick={() => (activeComingSoon = null)} aria-label="Tutup Modal">×</button>
      </div>

      <div class="cs-modal-body">
        <div class="cs-info-grid">
          <div class="cs-info-item">
            <span class="cs-lbl mono">STATUS MODEL</span>
            <b class="cs-val mono text-amber">{activeComingSoon.eta}</b>
          </div>
          <div class="cs-info-item">
            <span class="cs-lbl mono">KLASIFIKASI</span>
            <b class="cs-val">{activeComingSoon.family}</b>
          </div>
          <div class="cs-info-item">
            <span class="cs-lbl mono">ARSITEKTUR</span>
            <b class="cs-val mono">SOON</b>
          </div>
        </div>

        <div class="cs-desc-box">
          <span class="cs-desc-title mono">LOGIKA & HIPOTESIS KUANTITATIF</span>
          <p>{activeComingSoon.desc}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .board {
    background: #090d14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 12px 14px 14px 14px;
    margin-bottom: 12px;
  }

  .phead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 10px;
  }

  .phead h2 {
    font-size: 13.5px;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: -0.01em;
  }

  .phead-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  /* Search input filter */
  .search-box {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 4px;
    padding: 3px 8px;
    width: 210px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .search-box:focus-within {
    border-color: rgba(245, 158, 11, 0.5);
    box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.2);
  }

  .search-icon-svg {
    color: #64748b;
    flex-shrink: 0;
  }

  .search-box input {
    background: transparent;
    border: none;
    outline: none;
    color: #e2e8f0;
    font-size: 11px;
    width: 100%;
    font-family: inherit;
  }

  .search-box input::placeholder {
    color: #64748b;
  }

  .clear-btn {
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    padding: 0 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s;
  }

  .clear-btn:hover {
    color: #f1f5f9;
  }

  /* Segmented sort buttons */
  .seg {
    display: flex;
    align-items: center;
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 4px;
    padding: 2px;
    gap: 2px;
  }

  .seg-btn {
    background: transparent;
    border: none;
    color: #8b9bb4;
    font-size: 11px;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 3px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    font-family: inherit;
  }

  .seg-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.05);
  }

  .seg-btn.active {
    background: rgba(245, 158, 11, 0.18);
    color: #f59e0b;
    font-weight: 600;
  }

  /* Category pills track */
  .fam-track {
    display: flex;
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    padding-bottom: 8px;
    margin-bottom: 10px;
    scrollbar-width: thin;
  }

  .fam-btn {
    background: #0f1522;
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: #8b9bb4;
    font-size: 11px;
    padding: 3px 9px;
    border-radius: 4px;
    white-space: nowrap;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
  }

  .fam-btn:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.16);
  }

  .fam-btn.active {
    background: rgba(245, 158, 11, 0.12);
    border-color: #f59e0b;
    color: #f59e0b;
    font-weight: 600;
  }

  /* The 7-column card grid */
  .rows {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(215px, 1fr));
    gap: 1px;
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 5px;
    overflow: hidden;
  }

  .row {
    background: #0c1018;
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    border-left: 3px solid transparent;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    user-select: none;
  }

  .row:hover {
    background: #121824;
  }

  .row.selected {
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.14), #0c1018 75%);
    border-left-color: #f59e0b;
  }

  .r1 {
    display: flex;
    align-items: baseline;
    gap: 6px;
    min-width: 0;
  }

  .pos {
    font-size: 10px;
    font-weight: 700;
    color: #64748b;
    min-width: 20px;
  }

  .nm {
    font-size: 12px;
    font-weight: 600;
    color: #f1f5f9;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chip-mc {
    font-size: 9px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    background: rgba(244, 63, 94, 0.18);
    color: #f43f5e;
    border: 1px solid rgba(244, 63, 94, 0.35);
    white-space: nowrap;
    letter-spacing: -0.02em;
  }

  .ret {
    font-size: 12.5px;
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  .ret.up {
    color: #10b981;
  }

  .ret.down {
    color: #f43f5e;
  }

  .spark-wrap {
    width: 100%;
    height: 22px;
    margin: 1px 0;
  }

  .spark {
    width: 100%;
    height: 22px;
    display: block;
  }

  .r2 {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 10.5px;
    color: #64748b;
    min-width: 0;
  }

  .fam {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 110px;
  }

  .grow {
    flex: 1;
  }

  .eq {
    font-size: 11px;
    color: #cbd5e1;
    font-weight: 500;
  }

  /* Coming Soon Strategy Block Styles */
  .row.row-cs {
    background: #080c14;
    border-left: 3px solid rgba(245, 158, 11, 0.4);
    opacity: 0.88;
    position: relative;
    transition: all 0.18s ease;
  }

  .row.row-cs:hover {
    background: #0e1422;
    border-left-color: #f59e0b;
    opacity: 1;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
  }

  .pos-cs {
    font-size: 8.5px;
    font-weight: 700;
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.28);
    padding: 1px 4px;
    border-radius: 3px;
    letter-spacing: -0.01em;
  }

  .cs-nm {
    color: #cbd5e1;
  }

  .row.row-cs:hover .cs-nm {
    color: #ffffff;
  }

  .cs-tag {
    font-size: 8.5px;
    font-weight: 700;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    padding: 1px 4px;
    border-radius: 3px;
    white-space: nowrap;
    letter-spacing: -0.01em;
  }

  .cs-fam {
    color: #64748b;
  }

  .cs-status {
    font-size: 10px;
    font-weight: 700;
    color: #f59e0b;
    letter-spacing: -0.01em;
  }

  @keyframes csPulse {
    0%, 100% {
      opacity: 0.35;
      r: 2;
    }
    50% {
      opacity: 1;
      r: 2.8;
    }
  }

  .pulse-dot {
    animation: csPulse 2.2s ease-in-out infinite;
  }

  /* Coming Soon Modal Styles */
  .cs-modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.78);
    backdrop-filter: blur(4px);
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
  }

  .cs-modal-dialog {
    background: #090e17;
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    width: 100%;
    max-width: 520px;
    box-shadow: 0 20px 45px rgba(0, 0, 0, 0.8), 0 0 1px 1px rgba(245, 158, 11, 0.2);
    overflow: hidden;
  }

  .cs-modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 18px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #0c121e;
  }

  .cs-m-title {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .chip-cs {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.35);
  }

  .cs-m-title h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.01em;
  }

  .cs-m-close {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 20px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: color 0.15s, background 0.15s;
  }

  .cs-m-close:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.08);
  }

  .cs-modal-body {
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .cs-info-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
  }

  .cs-info-item {
    background: #060910;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 5px;
    padding: 9px 11px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .cs-lbl {
    font-size: 9.5px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.03em;
  }

  .cs-val {
    font-size: 12.5px;
    color: #f1f5f9;
  }

  .text-amber {
    color: #f59e0b;
  }

  .cs-desc-box {
    background: #060910;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 5px;
    padding: 12px 14px;
  }

  .cs-desc-title {
    display: block;
    font-size: 10px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
  }

  .cs-desc-box p {
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
    color: #cbd5e1;
  }

  .no-results {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 16px;
    background: #090d14;
    color: #94a3b8;
    text-align: center;
    gap: 8px;
  }

  .no-results p {
    margin: 0;
    font-size: 13px;
    color: #cbd5e1;
  }

  .no-results strong {
    color: #f59e0b;
  }

  .btn-clear-filter {
    margin-top: 6px;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #f59e0b;
    padding: 5px 12px;
    border-radius: 4px;
    font-size: 11.5px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-clear-filter:hover {
    background: rgba(245, 158, 11, 0.22);
  }

  @media (max-width: 768px) {
    .rows {
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    }
    .phead {
      flex-direction: column;
      align-items: stretch;
      gap: 10px;
    }
    .phead-right {
      width: 100%;
      flex-direction: column;
      align-items: stretch;
      gap: 8px;
    }
    .search-box {
      width: 100%;
      min-width: 0;
    }
    .seg {
      width: 100%;
      overflow-x: auto;
      white-space: nowrap;
      -webkit-overflow-scrolling: touch;
      padding: 3px;
    }
    .seg-btn {
      padding: 4px 8px;
      font-size: 10.5px;
      flex-shrink: 0;
    }
    .cs-info-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 480px) {
    .rows {
      grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
    }
    .row {
      padding: 6px 8px;
    }
    .pos {
      font-size: 9.5px;
    }
    .nm {
      font-size: 11px;
    }
  }
</style>
