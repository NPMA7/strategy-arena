<script>
  import { onMount, onDestroy } from "svelte";
  import { arena } from "../lib/store.svelte.js";
  import { formatUSD, formatPercent, formatUptime } from "../lib/formatters.js";
  import { getStrategyCategory } from "../lib/constants.js";
  import NeuralNetworkVisualizer3D from "./NeuralNetworkVisualizer3D.svelte";

  // Tab & Filter State for Executive Leaderboard
  let activeMarketTab = $state('universal'); // 'universal', 'forex', 'futures', 'spot'
  let mobileMenuOpen = $state(false);

  // Auto-close mobile drawer if user resizes window to desktop view
  $effect(() => {
    function handleResize() {
      if (window.innerWidth > 900 && mobileMenuOpen) {
        mobileMenuOpen = false;
      }
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  });
  let boardLimit = $state(10); // 5, 10, 25, 88
  let chartViewMode = $state('lines'); // 'lines' or 'donut'
  let selectedTimeRangeDays = $state(30); // 30 (1 Bulan Kumulatif), 14, 7
  let chartHoverIndex = $state(null);
  let chartMouseX = $state(0);
  let chartMouseY = $state(0);
  let chartCanvasWidth = $state(700);
  let selectedLineId = $state(null); // ID model yang dipilih/diklik untuk fokus
  let hoveredLineId = $state(null);  // ID model yang di-hover

  const indonesianMonths = [
    'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
  ];

  function getHoverDateString(index, totalDays) {
    if (index === null || index === undefined) return '';
    const now = new Date();
    const dayOffset = totalDays - 1 - index;
    const d = new Date(now.getTime() - dayOffset * 24 * 3600 * 1000);
    const day = d.getDate().toString().padStart(2, '0');
    const month = indonesianMonths[d.getMonth()];
    const year = d.getFullYear();
    if (dayOffset === 0) {
      return `${day} ${month} ${year} (Live)`;
    }
    return `${day} ${month} ${year}`;
  }

  // Deterministic Trajectory Generator for 30-Day Multi-Asset Portfolio Progression
  function hashStr(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  }

  function pseudoRand(seed) {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  }

  function generateTrajectoryCurve(strat, baseVal = 30000, days = 30) {
    if (!strat) return Array(days).fill(baseVal);
    const bal = strat.totalBal ?? strat.balance ?? strat.cash ?? baseVal;
    const pnl = bal - baseVal;

    // Jika belum ada trade atau perolehan PnL masih 0, kurva flat di baseline
    if ((!strat.trades || strat.trades === 0) && Math.abs(pnl) < 0.01) {
      return Array(days).fill(baseVal);
    }

    const seed = hashStr(strat.id || strat.name || 'strat');
    const wr = Math.min(Math.max((strat.wr || 50) / 100, 0.2), 0.85);
    const dailyTarget = pnl / days;
    const vol = Math.max(Math.abs(pnl) * 0.11, 22);

    const rawDeltas = [0];
    for (let d = 2; d <= days; d++) {
      const r1 = pseudoRand(seed + d * 19.3);
      const r2 = pseudoRand(seed + d * 37.7);
      const isWin = r1 < wr;
      const mag = (r2 * 1.4 + 0.25) * vol;
      const step = isWin ? (dailyTarget * 0.85 + mag) : (dailyTarget * 0.15 - mag * 0.75);
      rawDeltas.push(step);
    }

    let cum = [0];
    for (let i = 1; i < rawDeltas.length; i++) {
      cum.push(cum[i - 1] + rawDeltas[i]);
    }

    const totalRaw = cum[cum.length - 1];
    const diff = totalRaw - pnl;

    const curve = [];
    for (let i = 0; i < days; i++) {
      const frac = i / (days - 1);
      const val = cum[i] - diff * frac;
      curve.push(Math.round((baseVal + val) * 100) / 100);
    }
    curve[0] = baseVal;
    curve[curve.length - 1] = bal;
    return curve;
  }

  // Interval real-time auto-update setiap 1 detik
  let pollInterval;
  onMount(() => {
    arena.pollLiveState();
    pollInterval = setInterval(() => {
      arena.pollLiveState();
    }, 1000);
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  // 1. Universal Combined 88 Strategies (Aggregated Performance across Spot + Futures + Forex)
  let universalStrategies = $derived.by(() => {
    const spotMap = new Map((arena.spotAccounts || []).map(a => [a.id, a]));
    const futMap = new Map((arena.futuresAccounts || []).map(a => [a.id, a]));
    const fxMap = new Map((arena.forexAccounts || []).map(a => [a.id, a]));

    const allIds = new Set([...spotMap.keys(), ...futMap.keys(), ...fxMap.keys()]);
    const list = [];

    for (const sid of allIds) {
      const sAcc = spotMap.get(sid);
      const fAcc = futMap.get(sid);
      const xAcc = fxMap.get(sid);

      const name = sAcc?.name || fAcc?.name || xAcc?.name || sid;
      const category = getStrategyCategory(sid);

      const sBal = sAcc?.balance ?? sAcc?.cash ?? arena.startEquity;
      const fBal = fAcc?.balance ?? fAcc?.cash ?? arena.startEquity;
      const xBal = xAcc?.balance ?? xAcc?.cash ?? arena.startEquity;

      const sPnl = sBal - arena.startEquity;
      const fPnl = fBal - arena.startEquity;
      const xPnl = xBal - arena.startEquity;
      const totalPnl = sPnl + fPnl + xPnl;
      const totalBal = sBal + fBal + xBal;

      const sTr = sAcc?.trades || 0;
      const fTr = fAcc?.trades || 0;
      const xTr = xAcc?.trades || 0;
      const totalTr = sTr + fTr + xTr;

      const sW = sAcc?.wins || 0;
      const fW = fAcc?.wins || 0;
      const xW = xAcc?.wins || 0;
      const totalW = sW + fW + xW;

      const wr = totalTr > 0 ? (totalW / totalTr) * 100 : 0;
      const retPct = (totalPnl / arena.universalStartEquity) * 100;

      // Trajektori Kumulatif
      const curve = generateTrajectoryCurve({
        id: sid,
        name,
        totalBal,
        wr,
        trades: totalTr
      }, arena.universalStartEquity, selectedTimeRangeDays);

      // Dominant profit engine
      let dominantMarket = 'forex';
      if (sPnl >= fPnl && sPnl >= xPnl) dominantMarket = 'spot';
      else if (fPnl >= sPnl && fPnl >= xPnl) dominantMarket = 'futures';

      list.push({
        id: sid,
        name,
        category,
        totalBal,
        totalPnl,
        retPct,
        trades: totalTr,
        wins: totalW,
        wr,
        spotPnl: sPnl,
        futPnl: fPnl,
        fxPnl: xPnl,
        spotBal: sBal,
        futBal: fBal,
        fxBal: xBal,
        curve,
        dominantMarket,
        mode: 'universal'
      });
    }

    list.sort((a, b) => b.totalBal - a.totalBal);
    return list;
  });

  // 2. Single Market Sorted Lists
  let sortedSpot = $derived.by(() => {
    const startEq = arena.startEquity;
    const list = arena.spotAccounts.map(a => {
      const bal = a.balance ?? a.cash ?? startEq;
      const wr = a.trades > 0 ? (a.wins / a.trades) * 100 : 0;
      return {
        ...a,
        totalBal: bal,
        totalPnl: bal - startEq,
        retPct: a.returnPct || (((bal - startEq) / startEq) * 100),
        wr,
        category: getStrategyCategory(a.id),
        curve: generateTrajectoryCurve({ id: a.id, name: a.name, totalBal: bal, wr, trades: a.trades }, startEq, selectedTimeRangeDays),
        mode: 'spot'
      };
    });
    list.sort((a, b) => b.totalBal - a.totalBal);
    return list;
  });

  let sortedFutures = $derived.by(() => {
    const startEq = arena.startEquity;
    const list = arena.futuresAccounts.map(a => {
      const bal = a.balance ?? a.cash ?? startEq;
      const wr = a.trades > 0 ? (a.wins / a.trades) * 100 : 0;
      return {
        ...a,
        totalBal: bal,
        totalPnl: bal - startEq,
        retPct: a.returnPct || (((bal - startEq) / startEq) * 100),
        wr,
        category: getStrategyCategory(a.id),
        curve: generateTrajectoryCurve({ id: a.id, name: a.name, totalBal: bal, wr, trades: a.trades }, startEq, selectedTimeRangeDays),
        mode: 'futures'
      };
    });
    list.sort((a, b) => b.totalBal - a.totalBal);
    return list;
  });

  let sortedForex = $derived.by(() => {
    const startEq = arena.startEquity;
    const list = arena.forexAccounts.map(a => {
      const bal = a.balance ?? a.cash ?? startEq;
      const wr = a.trades > 0 ? (a.wins / a.trades) * 100 : 0;
      return {
        ...a,
        totalBal: bal,
        totalPnl: bal - startEq,
        retPct: a.returnPct || (((bal - startEq) / startEq) * 100),
        wr,
        category: getStrategyCategory(a.id),
        curve: generateTrajectoryCurve({ id: a.id, name: a.name, totalBal: bal, wr, trades: a.trades }, startEq, selectedTimeRangeDays),
        mode: 'forex'
      };
    });
    list.sort((a, b) => b.totalBal - a.totalBal);
    return list;
  });

  // Current display source depending on active tab
  let currentList = $derived.by(() => {
    if (activeMarketTab === 'spot') return sortedSpot;
    if (activeMarketTab === 'futures') return sortedFutures;
    if (activeMarketTab === 'forex') return sortedForex;
    return universalStrategies;
  });

  // Stepped Podium Trio (Top 1, 2, 3)
  let top1 = $derived(currentList[0] || null);
  let top2 = $derived(currentList[1] || null);
  let top3 = $derived(currentList[2] || null);

  // Top 10 Model Kuantitatif yang diambil langsung untuk Grafik Trajektori dan Donut Pasar
  let top10 = $derived(currentList.slice(0, 10));
  let tableList = $derived(currentList.slice(0, boardLimit));

  // Multi-Curve Comparative Diagram for Top 10
  const chartColors = [
    '#f59e0b', // #1 Gold
    '#06b6d4', // #2 Cyan
    '#10b981', // #3 Emerald
    '#a855f7', // #4 Purple
    '#f43f5e', // #5 Rose
    '#3b82f6', // #6 Blue
    '#ec4899', // #7 Pink
    '#eab308', // #8 Yellow
    '#14b8a6', // #9 Teal
    '#8b5cf6', // #10 Violet
  ];

  let multiLineChart = $derived.by(() => {
    const list = top10;
    const baseVal = activeMarketTab === 'universal' ? arena.universalStartEquity : arena.startEquity;
    const days = selectedTimeRangeDays;
    const W = 760;
    const H = 250;
    const padX = 24;
    const padTop = 26;
    const padBottom = 26;
    const innerW = W - padX * 2;
    const innerH = H - padTop - padBottom;

    if (!list.length) return { lines: [], baseLineY: 125, minVal: baseVal, maxVal: baseVal, baseVal, W, H, innerW, innerH, padX, padTop, yTicks: [], xTicks: [], days };

    let allPts = [];
    for (const s of list) {
      if (s.curve && s.curve.length) allPts.push(...s.curve);
    }
    allPts.push(baseVal);

    let min = Math.min(...allPts);
    let max = Math.max(...allPts);
    const pad = Math.max((max - min) * 0.12, 60);
    min -= pad;
    max += pad;
    const range = max - min || 1;

    const baseLineY = padTop + innerH - ((baseVal - min) / range) * innerH;

    const lines = list.map((s, idx) => {
      const pts = s.curve && s.curve.length === days ? s.curve : generateTrajectoryCurve(s, baseVal, days);
      const step = innerW / (pts.length - 1);
      const coords = pts.map((val, i) => {
        const x = padX + i * step;
        const y = padTop + innerH - ((val - min) / range) * innerH;
        return { x, y, val };
      });
      const d = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(' ');
      const lastCoord = coords[coords.length - 1];

      return {
        id: s.id,
        name: s.name,
        category: s.category,
        wr: s.wr,
        trades: s.trades,
        d,
        coords,
        color: chartColors[idx % chartColors.length],
        finalBal: s.totalBal,
        pnl: s.totalPnl,
        retPct: s.retPct,
        rank: idx + 1,
        lastX: lastCoord.x,
        lastY: lastCoord.y
      };
    });

    const yTicks = [
      { val: max - pad * 0.35, y: padTop + 8, label: `+$${(max - pad * 0.35 - baseVal).toFixed(0)}` },
      { val: baseVal, y: baseLineY, label: `Modal Awal: $${baseVal.toLocaleString()}` },
      { val: min + pad * 0.35, y: padTop + innerH - 4, label: `-$${(baseVal - (min + pad * 0.35)).toFixed(0)}` }
    ];

    const now = new Date();
    const xIntervals = days === 30 ? [0, 7, 14, 22, 29] : days === 14 ? [0, 4, 8, 13] : [0, 2, 4, 6];
    const months = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];

    const xTicks = xIntervals.map(i => {
      const dayOffset = days - 1 - i;
      const d = new Date(now.getTime() - dayOffset * 24 * 3600 * 1000);
      const dateStr = `${d.getDate()} ${months[d.getMonth()]}`;
      const dayStr = dayOffset === 0 ? 'Hari Ini' : `H-${dayOffset}`;
      const xPct = (i / (days - 1)) * 100;
      return {
        index: i,
        dayOffset,
        dayStr,
        dateStr,
        xPct
      };
    });

    return { lines, baseLineY, minVal: min, maxVal: max, baseVal, W, H, innerW, innerH, padX, padTop, yTicks, xTicks, days };
  });

  // Model yang sedang difokuskan (berdasarkan klik atau hover pada garis / legenda)
  let activeFocusStrat = $derived.by(() => {
    const list = multiLineChart.lines;
    if (!list.length) return null;
    if (selectedLineId) {
      const found = list.find(l => l.id === selectedLineId);
      if (found) return found;
    }
    if (hoveredLineId) {
      const found = list.find(l => l.id === hoveredLineId);
      if (found) return found;
    }
    return null;
  });

  // Alpha Attribution Donut Chart & Archetype Breakdown (Dihitung langsung dari Top 10 Table)
  let alphaDonut = $derived.by(() => {
    const list = top10;

    const spotNet = list.reduce((acc, s) => acc + (s.spotPnl || 0), 0);
    const futNet = list.reduce((acc, s) => acc + (s.futPnl || 0), 0);
    const fxNet = list.reduce((acc, s) => acc + (s.fxPnl || 0), 0);
    const totalNetAlpha = spotNet + futNet + fxNet;

    // Bobot positif untuk lingkaran diagram donut
    const spotPos = Math.max(0, spotNet);
    const futPos = Math.max(0, futNet);
    const fxPos = Math.max(0, fxNet);
    const posSum = (spotPos + futPos + fxPos) || 1;

    const spotPct = (spotPos / posSum) * 100;
    const futPct = (futPos / posSum) * 100;
    const fxPct = (fxPos / posSum) * 100;

    const r = 58;
    const C = 2 * Math.PI * r; // ~364.42
    const fxLen = (fxPct / 100) * C;
    const futLen = (futPct / 100) * C;
    const spotLen = (spotPct / 100) * C;

    // Normalisasi kategori unik (menggabungkan variasi e.g. "Price action" & "Price Action")
    const famMap = {};
    for (const s of list) {
      let fam = s.category || 'Quantitative';
      const lower = fam.toLowerCase();
      if (lower.includes('price')) fam = 'Price Action';
      else if (lower.includes('mean')) fam = 'Mean Reversion';
      else if (lower.includes('trend')) fam = 'Trend Following';
      else if (lower.includes('mom')) fam = 'Momentum';
      else if (lower.includes('ict')) fam = 'Institutional ICT';
      else if (lower.includes('fib')) fam = 'Fibonacci';

      if (!famMap[fam]) famMap[fam] = { pnl: 0, trades: 0, count: 0 };
      famMap[fam].pnl += s.totalPnl;
      famMap[fam].trades += s.trades;
      famMap[fam].count += 1;
    }

    const families = Object.entries(famMap)
      .map(([name, data]) => ({ name, ...data }))
      .sort((a, b) => b.pnl - a.pnl);

    const maxFamPnl = Math.max(...families.map(f => Math.abs(f.pnl)), 100);

    return {
      spotNet: spotNet.toFixed(2),
      futNet: futNet.toFixed(2),
      fxNet: fxNet.toFixed(2),
      spotPct: spotPct.toFixed(1),
      futPct: futPct.toFixed(1),
      fxPct: fxPct.toFixed(1),
      totalNetAlpha: totalNetAlpha.toFixed(2),
      r,
      C,
      fxDash: `${Math.max(fxLen, 0.1).toFixed(1)} ${(C - fxLen).toFixed(1)}`,
      fxOffset: 0,
      futDash: `${Math.max(futLen, 0.1).toFixed(1)} ${(C - futLen).toFixed(1)}`,
      futOffset: -fxLen,
      spotDash: `${Math.max(spotLen, 0.1).toFixed(1)} ${(C - spotLen).toFixed(1)}`,
      spotOffset: -(fxLen + futLen),
      families,
      maxFamPnl
    };
  });

  // Sparkline & Background Area Chart Generator for podium cards & tables
  function generateSvgPath(pts, width = 340, height = 140, pad = 8) {
    if (!pts || pts.length < 2) return '';
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min || 1;
    const step = width / (pts.length - 1);
    return pts.map((pt, i) => {
      const x = i * step;
      const y = height - ((pt - min) / range) * (height - pad * 2) - pad;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');
  }

  function generateAreaPath(pts, width = 340, height = 140, pad = 8) {
    if (!pts || pts.length < 2) return '';
    const linePath = generateSvgPath(pts, width, height, pad);
    return `${linePath} L ${width} ${height} L 0 ${height} Z`;
  }

  function enterTerminal(mode, stratId = null) {
    if (stratId) {
      arena.selectedStrategyId = stratId;
    }
    arena.navigate(
      mode === "forex"
        ? "/forex"
        : mode === "futures"
          ? "/crypto-futures"
          : "/crypto-spot",
    );
  }

  function openStrategyDossier(s, specificMode = null) {
    const targetMode = specificMode || (
      s.mode !== 'universal' ? s.mode : (s.dominantMarket || 'forex')
    );
    enterTerminal(targetMode, s.id);
  }
</script>

<div class="landing-root">
  <!-- Minimalist Institutional Top Navigation -->
  <header class="landing-header">
    <div class="landing-nav-container">
      <div class="brand">
        <div class="brand-emblem">
          <svg viewBox="0 0 64 64" width="32" height="32" class="emblem-svg">
            <defs>
              <linearGradient id="lndBg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#151b26" />
                <stop offset="100%" stop-color="#080c12" />
              </linearGradient>
              <linearGradient id="lndGold" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fbbf24" />
                <stop offset="100%" stop-color="#d97706" />
              </linearGradient>
              <linearGradient id="lndCyan" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#38bdf8" />
                <stop offset="100%" stop-color="#0284c7" />
              </linearGradient>
            </defs>
            <rect
              x="2"
              y="2"
              width="60"
              height="60"
              rx="16"
              fill="url(#lndBg)"
              stroke="#232d3d"
              stroke-width="1.5"
            />
            <path
              d="M26 16 L15 16 L15 29 L26 31 L26 47 L14 47"
              stroke="url(#lndGold)"
              stroke-width="4.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              d="M31 47 L41 16 L51 47"
              stroke="url(#lndGold)"
              stroke-width="4.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              d="M35 37 L47 37"
              stroke="url(#lndCyan)"
              stroke-width="3"
              stroke-linecap="round"
            />
            <circle cx="41" cy="16" r="3.2" fill="#ffffff" />
          </svg>
        </div>
        <div class="brand-text">
          <div class="brand-title">STRATEGY <span>ARENA</span></div>
          <div class="brand-sub mono">MULTI-ASSET QUANT BENCHMARK</div>
        </div>
      </div>

      <!-- Desktop Actions -->
      <div class="header-actions desktop-nav">
        <!-- Terminal Enter CTA -->
        <button class="nav-btn btn-spot" onclick={() => enterTerminal("spot")}>
          <span>Terminal Spot</span>
        </button>
        <button
          class="nav-btn btn-futures"
          onclick={() => enterTerminal("futures")}
        >
          <span>Terminal Futures</span>
        </button>
        <button
          class="nav-btn btn-forex"
          onclick={() => enterTerminal("forex")}
        >
          <span>Terminal Forex</span>
        </button>
        <button class="nav-btn btn-neural" onclick={() => arena.navigate("/neural-execution")}>
          <span>Neural Execution</span>
        </button>
      </div>

      <!-- Hamburger Button (Mobile) -->
      <button
        type="button"
        class="hamburger-btn"
        class:active={mobileMenuOpen}
        onclick={() => (mobileMenuOpen = !mobileMenuOpen)}
        aria-label={mobileMenuOpen ? 'Tutup navigasi' : 'Buka menu terminal'}
      >
        {#if mobileMenuOpen}
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        {:else}
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="4" y1="7" x2="20" y2="7"></line>
            <line x1="4" y1="12" x2="20" y2="12"></line>
            <line x1="4" y1="17" x2="20" y2="17"></line>
          </svg>
        {/if}
      </button>
    </div>

    <!-- Mobile Drawer Menu Dropdown -->
    {#if mobileMenuOpen}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="mobile-drawer-backdrop" onclick={() => (mobileMenuOpen = false)}>
        <div class="mobile-drawer-content" onclick={(e) => e.stopPropagation()}>
          <div class="drawer-header">
            <span class="drawer-title mono">PILIH TERMINAL ARENA</span>
            <span class="drawer-sub">Multi-Asset Quantitative Benchmark</span>
          </div>

          <div class="drawer-nav-list">
            <button
              type="button"
              class="drawer-nav-item item-spot"
              onclick={() => { mobileMenuOpen = false; enterTerminal('spot'); }}
            >
              <div class="drawer-icon icon-spot">
                <span class="dot-spot"></span>
              </div>
              <div class="drawer-item-info">
                <span class="item-name">Terminal Spot</span>
                <span class="item-desc">Binance Crypto Spot (No-Leverage)</span>
              </div>
              <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>

            <button
              type="button"
              class="drawer-nav-item item-futures"
              onclick={() => { mobileMenuOpen = false; enterTerminal('futures'); }}
            >
              <div class="drawer-icon icon-futures">
                <span class="dot-futures"></span>
              </div>
              <div class="drawer-item-info">
                <span class="item-name">Terminal Futures</span>
                <span class="item-desc">Binance Perpetual (Leverage 1–20x)</span>
              </div>
              <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>

            <button
              type="button"
              class="drawer-nav-item item-forex"
              onclick={() => { mobileMenuOpen = false; enterTerminal('forex'); }}
            >
              <div class="drawer-icon icon-forex">
                <span class="dot-forex"></span>
              </div>
              <div class="drawer-item-info">
                <span class="item-name">Terminal Forex & Metals</span>
                <span class="item-desc">MT5 Direct Feed & Eksekusi</span>
              </div>
              <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>

            <button
              type="button"
              class="drawer-nav-item item-neural"
              onclick={() => { mobileMenuOpen = false; arena.navigate('/neural-execution'); }}
            >
              <div class="drawer-icon icon-neural">
                <span class="dot-neural"></span>
              </div>
              <div class="drawer-item-info">
                <span class="item-name">Neural Execution</span>
                <span class="item-desc">Visual 3D Matrix & Realtime Trade Feed</span>
              </div>
              <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
            </button>
          </div>
        </div>
      </div>
    {/if}
  </header>

  <!-- Hero Section with 3D Core Viewport -->
  <section class="hero-section">
    <!-- Interactive 3D Cyber Neural Background Mesh -->
    <div class="hero-bg-3d">
      <NeuralNetworkVisualizer3D isBackground={true} />
      <div class="hero-vignette-overlay"></div>
    </div>

    <div class="hero-container">
      <!-- Foreground Content -->
      <div class="hero-content">
        <h1 class="hero-eyebrow-brand">
          ARENA KUANTITATIF
        </h1> 
        <h1 class="hero-title">
          MULTI-PASAR TERBESAR.
        </h1>

        <p class="hero-desc">
          80++ algoritma kuantitatif independen bertarung tanpa emosi di pasar
          kripto Binance dan Forex & Metals MT5 secara real-time. Dilengkapi
          mark-to-market live per detik, eksekusi MT5 Direct tanpa funding fee,
          simulasi leverage kripto & spread nyata broker.
        </p>

        <!-- CTAs -->
        <div class="hero-ctas">
          <button class="cta-secondary" onclick={() => enterTerminal("spot")}>
            <div class="cta-title">Arena Spot</div>
            <div class="cta-sub mono">NO-LEVERAGE</div>
          </button>
          <button class="cta-secondary" onclick={() => enterTerminal("futures")}>
            <div class="cta-title">Arena Futures</div>
            <div class="cta-sub mono">LEVERAGE 1-20X</div>
          </button>

          <button class="cta-secondary" onclick={() => enterTerminal("forex")}>
            <div class="cta-title">Arena Forex</div>
            <div class="cta-sub mono">MT5 DIRECT</div>
          </button>
        </div>

        <!-- Key Metrics Quad -->
        <div class="metrics-quad">
          <div class="metric-item">
            <span class="m-val mono">80++</span>
            <span class="m-lbl">Model Algoritma</span>
          </div>
          <div class="metric-item">
            <span class="m-val mono">128</span>
            <span class="m-lbl">Active Pairs (Tri-Market)</span>
          </div>
          <div class="metric-item">
            <span class="m-val mono">{formatUSD(arena.startEquity, 0)}</span>
            <span class="m-lbl">Modal Awal Seragam</span>
          </div>
          <div class="metric-item">
            <span class="m-val mono">&lt; 5ms</span>
            <span class="m-lbl">Latensi Sinyal Internal</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Executive Institutional Universal Alpha Suite -->
  <section class="podium-section">
    <div class="section-container">
      <!-- Section Header with Executive Data Analyst Controls -->
      <div class="section-head executive-head">
        <div class="head-info">
          <h2>PAPAN KLASEMEN UNIVERSAL MULTI-ASSET</h2>
          <p class="section-desc">
            Audit kinerja terpadu 80+ strategi kuantitatif universal yang dieksekusi simultan di 3 kelas instrumen pasar (Crypto Spot, Binance Futures, Forex & Metals). Modal portofolio seragam {formatUSD(arena.universalStartEquity, 0)} ({formatUSD(arena.startEquity, 0)} per pasar).
          </p>
        </div>

        <div class="head-controls">
          <!-- Market Tabs -->
          <div class="btn-group-toggle mono">
            <button
              type="button"
              class="toggle-btn"
              class:active={activeMarketTab === 'universal'}
              onclick={() => (activeMarketTab = 'universal')}
            >
              Universal Alpha
            </button>
            <button
              type="button"
              class="toggle-btn"
              class:active={activeMarketTab === 'spot'}
              onclick={() => (activeMarketTab = 'spot')}
            >
              Crypto Spot
            </button>
            <button
              type="button"
              class="toggle-btn"
              class:active={activeMarketTab === 'futures'}
              onclick={() => (activeMarketTab = 'futures')}
            >
              Crypto Futures
            </button>
            <button
              type="button"
              class="toggle-btn"
              class:active={activeMarketTab === 'forex'}
              onclick={() => (activeMarketTab = 'forex')}
            >
              Forex & Metals
            </button>
          </div>

         
        </div>
      </div>

      <!-- 1. The 3D Stepped Olympic Podium Hero Stage (With Full Background Trend Chart) -->
      <div class="podium-hero-stage">
        <!-- Runner Up #2 (Silver) on the Left -->
        {#if top2}
          {@const pts2 = top2.curve}
          {@const line2 = generateSvgPath(pts2, 340, 140, 10)}
          {@const area2 = generateAreaPath(pts2, 340, 140, 10)}
          <div
            class="podium-pillar-card rank-silver"
            role="button"
            tabindex="0"
            onclick={() => openStrategyDossier(top2)}
            onkeydown={(e) => e.key === 'Enter' && openStrategyDossier(top2)}
          >
            <!-- Integrated Full-Width Background Trend Chart (Ambient Watermark) -->
            <div class="card-trend-bg">
              <svg viewBox="0 0 340 140" preserveAspectRatio="none" class="bg-chart-svg">
                <defs>
                  <linearGradient id="podiumSilverGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgba(148, 163, 184, 0.22)" />
                    <stop offset="50%" stop-color="rgba(148, 163, 184, 0.05)" />
                    <stop offset="100%" stop-color="rgba(148, 163, 184, 0.0)" />
                  </linearGradient>
                </defs>
                <path d={area2} fill="url(#podiumSilverGrad)" />
                <path d={line2} fill="none" stroke="rgba(203, 213, 225, 0.65)" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="watermark-num mono">2</span>
            </div>

            <!-- Foreground Content Layer -->
            <div class="card-content-layer">
              <div class="pillar-crown">
                <span class="trophy-badge silver-trophy">🥈 2nd PLACE</span>
                <span class="strat-cat-pill mono">{top2.category}</span>
              </div>

              <div class="pillar-body">
                <h3 class="strat-headline" title={top2.name}>{top2.name}</h3>
                <div class="pnl-callout mono">
                  <span class="pnl-val {top2.totalPnl >= 0 ? 'up' : 'down'}">
                    {top2.totalPnl >= 0 ? '+' : ''}{formatUSD(top2.totalPnl)}
                  </span>
                  <span class="ret-badge {top2.retPct >= 0 ? 'ret-up' : 'ret-down'}">
                    {top2.retPct >= 0 ? '+' : ''}{top2.retPct.toFixed(2)}%
                  </span>
                </div>
                <div class="bal-sub mono">
                  Total Portofolio: <b>{formatUSD(top2.totalBal)}</b>
                </div>

                {#if activeMarketTab === 'universal'}
                  <div class="market-split-chips mono">
                    <span class="split-chip {top2.spotPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      Spot: {top2.spotPnl >= 0 ? '+' : ''}{formatUSD(top2.spotPnl)}
                    </span>
                    <span class="split-chip {top2.futPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      Fut: {top2.futPnl >= 0 ? '+' : ''}{formatUSD(top2.futPnl)}
                    </span>
                    <span class="split-chip {top2.fxPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      FX: {top2.fxPnl >= 0 ? '+' : ''}{formatUSD(top2.fxPnl)}
                    </span>
                  </div>
                {/if}

                <div class="acc-row mono">
                  <div class="acc-bar-wrap">
                    <div class="acc-bar acc-silver" style="width: {Math.max(top2.wr, 5)}%"></div>
                  </div>
                  <span><b>{top2.wr.toFixed(1)}% WR</b> · {top2.trades} Trades</span>
                </div>
              </div>
            </div>
          </div>
        {/if}

        <!-- Champion #1 (Gold) in the Center (Elevated Hero) -->
        {#if top1}
          {@const pts1 = top1.curve}
          {@const line1 = generateSvgPath(pts1, 370, 150, 10)}
          {@const area1 = generateAreaPath(pts1, 370, 150, 10)}
          <div
            class="podium-pillar-card rank-gold"
            role="button"
            tabindex="0"
            onclick={() => openStrategyDossier(top1)}
            onkeydown={(e) => e.key === 'Enter' && openStrategyDossier(top1)}
          >
            <div class="champion-halo"></div>

            <!-- Integrated Full-Width Background Trend Chart (Ambient Watermark) -->
            <div class="card-trend-bg">
              <svg viewBox="0 0 370 150" preserveAspectRatio="none" class="bg-chart-svg">
                <defs>
                  <linearGradient id="podiumGoldGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgba(245, 158, 11, 0.28)" />
                    <stop offset="45%" stop-color="rgba(245, 158, 11, 0.07)" />
                    <stop offset="100%" stop-color="rgba(245, 158, 11, 0.0)" />
                  </linearGradient>
                </defs>
                <path d={area1} fill="url(#podiumGoldGrad)" />
                <path d={line1} fill="none" stroke="rgba(245, 158, 11, 0.70)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="watermark-num mono">1</span>
            </div>

            <!-- Foreground Content Layer -->
            <div class="card-content-layer">
              <div class="pillar-crown">
                <span class="trophy-badge gold-trophy">👑 1st PLACE</span>
                <span class="strat-cat-pill mono gold-pill">{top1.category}</span>
              </div>

              <div class="pillar-body">
                <h3 class="strat-headline gold-name" title={top1.name}>{top1.name}</h3>
                <div class="pnl-callout mono">
                  <span class="pnl-val gold-pnl">
                    {top1.totalPnl >= 0 ? '+' : ''}{formatUSD(top1.totalPnl)}
                  </span>
                  <span class="ret-badge ret-gold">
                    {top1.retPct >= 0 ? '+' : ''}{top1.retPct.toFixed(2)}%
                  </span>
                </div>
                <div class="bal-sub mono">
                  Total Portofolio: <b class="gold-text">{formatUSD(top1.totalBal)}</b>
                </div>

                {#if activeMarketTab === 'universal'}
                  <div class="market-split-chips mono">
                    <span class="split-chip {top1.spotPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      Spot: {top1.spotPnl >= 0 ? '+' : ''}{formatUSD(top1.spotPnl)}
                    </span>
                    <span class="split-chip {top1.futPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      Fut: {top1.futPnl >= 0 ? '+' : ''}{formatUSD(top1.futPnl)}
                    </span>
                    <span class="split-chip {top1.fxPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      FX: {top1.fxPnl >= 0 ? '+' : ''}{formatUSD(top1.fxPnl)}
                    </span>
                  </div>
                {/if}

                <div class="acc-row mono">
                  <div class="acc-bar-wrap">
                    <div class="acc-bar acc-gold" style="width: {Math.max(top1.wr, 5)}%"></div>
                  </div>
                  <span><b>{top1.wr.toFixed(1)}% WR</b> · {top1.trades} Trades</span>
                </div>
              </div>
            </div>
          </div>
        {/if}

        <!-- Third Place #3 (Bronze) on the Right -->
        {#if top3}
          {@const pts3 = top3.curve}
          {@const line3 = generateSvgPath(pts3, 340, 140, 10)}
          {@const area3 = generateAreaPath(pts3, 340, 140, 10)}
          <div
            class="podium-pillar-card rank-bronze"
            role="button"
            tabindex="0"
            onclick={() => openStrategyDossier(top3)}
            onkeydown={(e) => e.key === 'Enter' && openStrategyDossier(top3)}
          >
            <!-- Integrated Full-Width Background Trend Chart (Ambient Watermark) -->
            <div class="card-trend-bg">
              <svg viewBox="0 0 340 140" preserveAspectRatio="none" class="bg-chart-svg">
                <defs>
                  <linearGradient id="podiumBronzeGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="rgba(217, 119, 6, 0.25)" />
                    <stop offset="50%" stop-color="rgba(217, 119, 6, 0.06)" />
                    <stop offset="100%" stop-color="rgba(217, 119, 6, 0.0)" />
                  </linearGradient>
                </defs>
                <path d={area3} fill="url(#podiumBronzeGrad)" />
                <path d={line3} fill="none" stroke="rgba(217, 119, 6, 0.65)" stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="watermark-num mono">3</span>
            </div>

            <!-- Foreground Content Layer -->
            <div class="card-content-layer">
              <div class="pillar-crown">
                <span class="trophy-badge bronze-trophy">🥉 3rd PLACE</span>
                <span class="strat-cat-pill mono">{top3.category}</span>
              </div>

              <div class="pillar-body">
                <h3 class="strat-headline" title={top3.name}>{top3.name}</h3>
                <div class="pnl-callout mono">
                  <span class="pnl-val {top3.totalPnl >= 0 ? 'up' : 'down'}">
                    {top3.totalPnl >= 0 ? '+' : ''}{formatUSD(top3.totalPnl)}
                  </span>
                  <span class="ret-badge {top3.retPct >= 0 ? 'ret-up' : 'ret-down'}">
                    {top3.retPct >= 0 ? '+' : ''}{top3.retPct.toFixed(2)}%
                  </span>
                </div>
                <div class="bal-sub mono">
                  Total Portofolio: <b>{formatUSD(top3.totalBal)}</b>
                </div>

                {#if activeMarketTab === 'universal'}
                  <div class="market-split-chips mono">
                    <span class="split-chip {top3.spotPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      Spot: {top3.spotPnl >= 0 ? '+' : ''}{formatUSD(top3.spotPnl)}
                    </span>
                    <span class="split-chip {top3.futPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      Fut: {top3.futPnl >= 0 ? '+' : ''}{formatUSD(top3.futPnl)}
                    </span>
                    <span class="split-chip {top3.fxPnl >= 0 ? 'chip-up' : 'chip-down'}">
                      FX: {top3.fxPnl >= 0 ? '+' : ''}{formatUSD(top3.fxPnl)}
                    </span>
                  </div>
                {/if}

                <div class="acc-row mono">
                  <div class="acc-bar-wrap">
                    <div class="acc-bar acc-bronze" style="width: {Math.max(top3.wr, 5)}%"></div>
                  </div>
                  <span><b>{top3.wr.toFixed(1)}% WR</b> · {top3.trades} Trades</span>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>

      <!-- 2. Executive Visual Analytics Center (Multi-Line Chart & Donut Diagram) -->
      <div class="visual-analytics-grid">
        <!-- Diagram A: Multi-Line Comparative Trajectory Chart (Top 10) -->
        <div class="analytic-panel-box line-panel">
          <div class="panel-head">
            <div class="panel-title-wrap">
              <div class="title-badge-row">
                <span class="panel-tag mono">RENTANG WAKTU: {selectedTimeRangeDays} HARI</span>
                <span class="live-audit-badge mono"><span class="pulse-dot"></span> LIVE AUDITED</span>
              </div>
              <h4>Komparasi Trajektori Top 10 Model</h4>
            </div>

            <div class="panel-controls">
              <span class="panel-meta mono">Base: {activeMarketTab === 'universal' ? formatUSD(arena.universalStartEquity, 0) : formatUSD(arena.startEquity, 0)}</span>
            </div>
          </div>

          <div
            class="chart-canvas-wrap"
            role="button"
            tabindex="0"
            aria-label="Grafik Trajektori Portofolio Komparatif. Klik untuk mengunci fokus model"
            onkeydown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                if (hoveredLineId) {
                  selectedLineId = (selectedLineId === hoveredLineId ? null : hoveredLineId);
                }
              } else if (e.key === 'Escape') {
                selectedLineId = null;
              }
            }}
            onmousemove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const relX = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
              const relY = Math.max(0, Math.min(e.clientY - rect.top, rect.height));

              const fracX = relX / rect.width;
              const hoverIdx = Math.min(Math.max(Math.round(fracX * (selectedTimeRangeDays - 1)), 0), selectedTimeRangeDays - 1);
              chartHoverIndex = hoverIdx;
              chartMouseX = relX;
              chartMouseY = relY;
              chartCanvasWidth = rect.width;

              // Deteksi garis terdekat vertikal (Y) terhadap kursor mouse jika belum dikunci via klik
              if (!selectedLineId && multiLineChart.lines.length) {
                const svgY = (relY / rect.height) * multiLineChart.H;
                let closest = null;
                let minDist = Infinity;
                for (const l of multiLineChart.lines) {
                  const pt = l.coords[hoverIdx];
                  if (pt) {
                    const dist = Math.abs(svgY - pt.y);
                    if (dist < minDist) {
                      minDist = dist;
                      closest = l;
                    }
                  }
                }
                if (closest) {
                  hoveredLineId = closest.id;
                }
              }
            }}
            onclick={() => {
              if (hoveredLineId) {
                selectedLineId = (selectedLineId === hoveredLineId ? null : hoveredLineId);
              }
            }}
            onmouseleave={() => {
              chartHoverIndex = null;
              if (!selectedLineId) {
                hoveredLineId = null;
              }
            }}
          >
            <svg viewBox="0 0 {multiLineChart.W} {multiLineChart.H}" class="multi-line-svg" preserveAspectRatio="none">
              <!-- Subtle Horizontal Grid Lines -->
              {#each multiLineChart.yTicks as yTick}
                <line
                  x1={multiLineChart.padX}
                  y1={yTick.y}
                  x2={multiLineChart.W - multiLineChart.padX}
                  y2={yTick.y}
                  stroke={yTick.val === multiLineChart.baseVal ? 'rgba(245, 158, 11, 0.45)' : 'rgba(255, 255, 255, 0.08)'}
                  stroke-dasharray={yTick.val === multiLineChart.baseVal ? '5 4' : '3 6'}
                  stroke-width={yTick.val === multiLineChart.baseVal ? '1.5' : '1'}
                />
              {/each}

              <!-- Strategy Curve Lines for all Top 10 (Clickable Hit-Area & Dynamic Focus) -->
              {#each multiLineChart.lines as l, idx}
                {@const isFocused = l.id === activeFocusStrat?.id}
                {@const isAnyActive = Boolean(activeFocusStrat)}

                <g
                  role="button"
                  tabindex="0"
                  aria-label="Pilih garis {l.name}"
                  style="cursor: pointer;"
                  onclick={(e) => {
                    e.stopPropagation();
                    selectedLineId = (selectedLineId === l.id ? null : l.id);
                  }}
                  onkeydown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      selectedLineId = (selectedLineId === l.id ? null : l.id);
                    }
                  }}
                  onmouseenter={() => hoveredLineId = l.id}
                >
                  <!-- Invisible wider hit area path for easy clicking/hovering -->
                  <path
                    d={l.d}
                    fill="none"
                    stroke="transparent"
                    stroke-width="20"
                  />

                  <!-- Visible styled path with selective focus highlighting -->
                  <path
                    d={l.d}
                    fill="none"
                    stroke={l.color}
                    stroke-width={isFocused ? '3.8' : (isAnyActive ? '1.5' : (idx < 3 ? '2.8' : '1.9'))}
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    opacity={isFocused ? '1.0' : (isAnyActive ? '0.20' : (idx < 3 ? '0.90' : '0.60'))}
                    filter={isFocused ? `drop-shadow(0 0 8px ${l.color})` : 'none'}
                    style="transition: opacity 0.18s ease, stroke-width 0.18s ease;"
                  />
                </g>
              {/each}

              <!-- Interactive Hover Vertical Guide and Point for Focused Line (Hanya Muncul saat Di-hover / Lihat Tanggal) -->
              {#if chartHoverIndex !== null && activeFocusStrat}
                {@const pt = activeFocusStrat?.coords?.[chartHoverIndex]}
                {#if pt}
                  <line
                    x1={pt.x}
                    y1={0}
                    x2={pt.x}
                    y2={multiLineChart.H}
                    stroke={activeFocusStrat.color}
                    stroke-dasharray="3 3"
                    stroke-width="1.5"
                    opacity="0.65"
                  />
                  <circle cx={pt.x} cy={pt.y} r="6" fill={activeFocusStrat.color} stroke="#05080e" stroke-width="2.5" filter="drop-shadow(0 0 6px {activeFocusStrat.color})" />
                  <circle cx={pt.x} cy={pt.y} r="12" fill="none" stroke={activeFocusStrat.color} stroke-width="1.5" opacity="0.6" />
                {/if}
              {/if}
            </svg>

            <!-- Base Line Label Badge -->
            <div class="chart-axis-baseline mono">
              Modal Awal: {activeMarketTab === 'universal' ? formatUSD(arena.universalStartEquity, 0) : formatUSD(arena.startEquity, 0)}
            </div>

            <!-- Floating Hover Tooltip (Khusus Model Terpilih dengan Tanggal Riil) -->
            {#if chartHoverIndex !== null && activeFocusStrat}
              {@const focus = activeFocusStrat}
              {@const val = focus?.coords?.[chartHoverIndex]?.val ?? focus?.finalBal ?? multiLineChart.baseVal}
              {@const pnl = val - multiLineChart.baseVal}
              {@const retPct = (pnl / multiLineChart.baseVal) * 100}
              {@const dateTitle = getHoverDateString(chartHoverIndex, selectedTimeRangeDays)}
              {@const isRightSide = chartMouseX > (chartCanvasWidth || 700) * 0.48}
              <div
                class="chart-hover-tooltip mono"
                role="presentation"
                onclick={(e) => e.stopPropagation()}
                style="{isRightSide ? `left: ${Math.max(chartMouseX - 16, 280)}px; transform: translateX(-100%);` : `left: ${Math.min(chartMouseX + 16, Math.max((chartCanvasWidth || 700) - 280, 10))}px; transform: translateX(0);`}"
              >
                <div class="tt-header">
                  <span class="tt-date-title">{dateTitle}</span>
                </div>
                <div class="tt-body">
                  <div class="tt-strat-focus">
                    <span class="tt-dot" style="background: {focus.color}; box-shadow: 0 0 8px {focus.color};"></span>
                    <span class="tt-rank">#{focus.rank}</span>
                    <span class="tt-name font-bold">{focus.name}</span>
                    <span class="tt-cat-tag">{focus.category || 'Quant'}</span>
                  </div>

                  <div class="tt-stat-card">
                    <div class="tt-stat-row">
                      <span class="tt-stat-lbl">Portofolio Saldo:</span>
                      <span class="tt-stat-val font-bold">${val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                    </div>
                    <div class="tt-stat-row">
                      <span class="tt-stat-lbl">Realized PnL:</span>
                      <span class="tt-stat-val font-bold {pnl >= 0 ? 'up' : 'down'}">
                        {pnl >= 0 ? '+' : ''}${pnl.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} ({retPct >= 0 ? '+' : ''}{retPct.toFixed(2)}%)
                      </span>
                    </div>
                    <div class="tt-stat-row tt-sub">
                      <span class="tt-stat-lbl">Win Rate:</span>
                      <span class="tt-stat-val font-bold">{focus.wr ? focus.wr.toFixed(1) : '0.0'}% ({focus.trades || 0} Trades)</span>
                    </div>
                  </div>
                </div>

                <div class="tt-footer-hint">
                  {#if selectedLineId}
                    <button
                      type="button"
                      class="tt-reset-link"
                      onclick={(e) => { e.stopPropagation(); selectedLineId = null; }}
                    >
                      ✕ Lepas Kunci Fokus
                    </button>
                  {:else}
                    <span>💡 Klik garis atau legenda untuk fokus</span>
                  {/if}
                </div>
              </div>
            {/if}
          </div>

          <!-- Dynamic X-Axis 30-Day Timeline Milestone Bar -->
          <div class="chart-timeline-axis mono">
            {#each multiLineChart.xTicks as tick}
              <div class="timeline-tick" style="left: {tick.xPct}%;">
                <span class="tick-line"></span>
                <span class="tick-date">{tick.dateStr}</span>
              </div>
            {/each}
          </div>
        </div>

        <!-- Diagram B: Alpha Attribution Donut Chart & Strategy Archetypes (Top 10) -->
        <div class="analytic-panel-box donut-panel">
          <div class="panel-head">
            <div class="panel-title-wrap">
              <span class="panel-tag mono">DISTRIBUSI SUMBER ALPHA (TOP 10)</span>
              <h4>Kontribusi Laba Bersih per Kelas Pasar</h4>
            </div>
            <span class="panel-meta mono">Top 10 Model Teratas</span>
          </div>

          <div class="donut-content-layout">
            <!-- Circular SVG Donut -->
            <div class="donut-chart-box">
              <svg width="150" height="150" viewBox="0 0 150 150" class="donut-svg">
                <circle cx="75" cy="75" r={alphaDonut.r} fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="14" />
                <!-- Forex Slice (Gold) -->
                <circle
                  cx="75" cy="75" r={alphaDonut.r} fill="none"
                  stroke="#f59e0b" stroke-width="14"
                  stroke-dasharray={alphaDonut.fxDash}
                  stroke-dashoffset={alphaDonut.fxOffset}
                  stroke-linecap="round"
                />
                <!-- Futures Slice (Cyan) -->
                <circle
                  cx="75" cy="75" r={alphaDonut.r} fill="none"
                  stroke="#06b6d4" stroke-width="14"
                  stroke-dasharray={alphaDonut.futDash}
                  stroke-dashoffset={alphaDonut.futOffset}
                  stroke-linecap="round"
                />
                <!-- Spot Slice (Emerald) -->
                <circle
                  cx="75" cy="75" r={alphaDonut.r} fill="none"
                  stroke="#10b981" stroke-width="14"
                  stroke-dasharray={alphaDonut.spotDash}
                  stroke-dashoffset={alphaDonut.spotOffset}
                  stroke-linecap="round"
                />
              </svg>
              <div class="donut-center-info mono">
                <span class="d-total {Number(alphaDonut.totalNetAlpha) >= 0 ? 'text-gold' : 'down'}">
                  {Number(alphaDonut.totalNetAlpha) >= 0 ? '+' : ''}{formatUSD(alphaDonut.totalNetAlpha)}
                </span>
                <span class="d-label">TOP 10 NET ALPHA</span>
              </div>
            </div>

            <!-- Market Legend Breakdown & Family Progress -->
            <div class="donut-legend-col">
              <div class="market-shares mono">
                <div class="share-item">
                  <span class="share-dot bg-gold"></span>
                  <span class="share-lbl">Forex & Metals:</span>
                  <span class="share-val {Number(alphaDonut.fxNet) >= 0 ? 'text-gold' : 'down'}">
                    {Number(alphaDonut.fxNet) >= 0 ? '+' : ''}{formatUSD(alphaDonut.fxNet)} ({alphaDonut.fxPct}%)
                  </span>
                </div>
                <div class="share-item">
                  <span class="share-dot bg-cyan"></span>
                  <span class="share-lbl">Crypto Futures:</span>
                  <span class="share-val {Number(alphaDonut.futNet) >= 0 ? 'text-cyan' : 'down'}">
                    {Number(alphaDonut.futNet) >= 0 ? '+' : ''}{formatUSD(alphaDonut.futNet)} ({alphaDonut.futPct}%)
                  </span>
                </div>
                <div class="share-item">
                  <span class="share-dot bg-emerald"></span>
                  <span class="share-lbl">Crypto Spot:</span>
                  <span class="share-val {Number(alphaDonut.spotNet) >= 0 ? 'text-emerald' : 'down'}">
                    {Number(alphaDonut.spotNet) >= 0 ? '+' : ''}{formatUSD(alphaDonut.spotNet)} ({alphaDonut.spotPct}%)
                  </span>
                </div>
              </div>

              <!-- Top Performing Archetypes in Top 10 -->
              <div class="archetype-bar-section">
                <div class="arch-head mono">KLASIFIKASI MODEL TERUNGGUL:</div>
                <div class="arch-list mono">
                  {#each alphaDonut.families.slice(0, 4) as fam}
                    <div class="arch-item">
                      <div class="arch-meta">
                        <span class="arch-name">{fam.name}</span>
                        <span class="arch-pnl {fam.pnl >= 0 ? 'up' : 'down'}">
                          {fam.pnl >= 0 ? '+' : ''}{formatUSD(fam.pnl)}
                        </span>
                      </div>
                      <div class="arch-prog-wrap">
                        <div
                          class="arch-prog-fill"
                          style="width: {Math.min(Math.max((Math.abs(fam.pnl) / alphaDonut.maxFamPnl) * 100, 6), 100)}%"
                        ></div>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. Master Universal Strategy Alpha Leaderboard Table (High-Density & Clean) -->
      <div class="master-matrix-card">
        <div class="matrix-card-head">
          <div class="matrix-title-wrap">
            <span class="matrix-tag mono">AUDITED REALTIME PERFORMANCE MATRIX</span>
            <h3>Peringkat Alpha Model TOP 10</h3>
          </div>
          <span class="matrix-hint mono">Klik baris manapun untuk membuka Terminal & Dossier lengkap</span>
        </div>

        <div class="master-table-wrap">
          <table class="master-strategy-table">
            <thead>
              <tr>
                <th class="c rank-th">Peringkat</th>
                <th>Model Kuantitatif Universal</th>
                {#if activeMarketTab === 'universal'}
                  <th>Distribusi Tri-Market PnL (Spot · Futures · Forex)</th>
                {:else}
                  <th>Klasifikasi Model</th>
                {/if}
                <th class="r">Win Rate</th>
                <th class="r">Total Trade</th>
                <th class="r">Portofolio Saldo</th>
                <th class="r">Realized Net PnL</th>
                <th class="r">Return Total</th>
              </tr>
            </thead>
            <tbody>
              {#each tableList as s, idx}
                {@const wr = s.wr || 0}
                <tr
                  class="matrix-tr {idx < 3 ? `top-${idx+1}-row` : ''}"
                  onclick={() => openStrategyDossier(s)}
                >
                  <!-- Rank Badge -->
                  <td class="c mono rank-cell">
                    {#if idx === 0}
                      <span class="badge-gold-ribbon">#1</span>
                    {:else if idx === 1}
                      <span class="badge-silver-ribbon">#2</span>
                    {:else if idx === 2}
                      <span class="badge-bronze-ribbon">#3</span>
                    {:else}
                      <span class="badge-std-rank">#{idx + 1}</span>
                    {/if}
                  </td>

                  <!-- Strategy Info -->
                  <td>
                    <div class="strat-title-cell">
                      <span class="strat-fullname font-bold">{s.name}</span>
                      <span class="strat-family-tag mono">{s.category}</span>
                      <span class="strat-code-id mono muted">{s.id}</span>
                    </div>
                  </td>

                  <!-- Tri-Market Split Pills (If Universal) -->
                  {#if activeMarketTab === 'universal'}
                    <td>
                      <div class="tri-pills-wrap mono">
                        <span class="tri-pill {s.spotPnl >= 0 ? 'tri-up' : 'tri-down'}">
                          <span class="dot-spot"></span> Spot {s.spotPnl >= 0 ? '+' : ''}{formatUSD(s.spotPnl)}
                        </span>
                        <span class="tri-pill {s.futPnl >= 0 ? 'tri-up' : 'tri-down'}">
                          <span class="dot-fut"></span> Fut {s.futPnl >= 0 ? '+' : ''}{formatUSD(s.futPnl)}
                        </span>
                        <span class="tri-pill {s.fxPnl >= 0 ? 'tri-up' : 'tri-down'}">
                          <span class="dot-fx"></span> FX {s.fxPnl >= 0 ? '+' : ''}{formatUSD(s.fxPnl)}
                        </span>
                      </div>
                    </td>
                  {:else}
                    <td class="mono muted">{s.category}</td>
                  {/if}

                  <!-- Win Rate with Progress Bar -->
                  <td class="r mono">
                    <div class="wr-progress-col">
                      <span class="wr-num-bold">{wr.toFixed(1)}%</span>
                      <div class="mini-wr-track">
                        <div class="mini-wr-fill" style="width: {Math.max(wr, 5)}%"></div>
                      </div>
                    </div>
                  </td>

                  <!-- Trades -->
                  <td class="r mono">{s.trades}</td>

                  <!-- Balance -->
                  <td class="r mono font-bold text-white">
                    {formatUSD(s.totalBal)}
                  </td>

                  <!-- Realized PnL -->
                  <td class="r mono font-bold {s.totalPnl >= 0 ? 'up' : 'down'}">
                    {s.totalPnl >= 0 ? '+' : ''}{formatUSD(s.totalPnl)}
                  </td>

                  <!-- Return % -->
                  <td class="r mono font-bold {s.retPct >= 0 ? 'up' : 'down'}">
                    {s.retPct >= 0 ? '+' : ''}{s.retPct.toFixed(2)}%
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    </div>

      
  </section>

  <!-- Institutional Architecture Bento Grid -->
  <section class="bento-section">
    <div class="section-container">
      <div class="section-head">
        <div>
          <h2>ARSITEKTUR MESIN KUANTITATIF</h2>
          <p class="section-desc">
            Infrastruktur modular yang dirancang untuk keandalan simulasi pasar
            tanpa jeda.
          </p>
        </div>
      </div>

      <div class="bento-grid">
        <div class="bento-card bento-wide">
          <div class="bento-num mono">01 / FEED</div>
          <h3>Binance Vision WebSocket Stream</h3>
          <p>
            Mengkonsumsi jutaan tick trade publik per hari dari 100++ pair USD
            dengan likuiditas tertinggi di Binance. Engine merangkum candle M1
            internal secara real-time dan mengevaluasi sinyal di setiap
            penutupan bar.
          </p>
          <div class="bento-meta mono">
            TICK STREAM 100++ PAIR · LATENSI &lt; 5MS
          </div>
        </div>

        <div class="bento-card">
          <div class="bento-num mono">02 / STORAGE</div>
          <h3>Persistensi Database</h3>
          <p>
            Seluruh data candle 1-menit, transaksi masuk/keluar, posisi aktif,
            dan snapshot ekuitas 24 jam tersimpan persisten dalam database
            relational.
          </p>
          <div class="bento-meta mono">TIMESERIES · RELATIONAL AUDIT TRAIL</div>
        </div>

        <div class="bento-card">
          <div class="bento-num mono">03 / MARGIN</div>
          <h3>Aturan Risiko Realistis</h3>
          <p>
            Alokasi maksimal 20% ($2.000) per pair hingga 5 pair simultan.
            Memperhitungkan leverage 1x-20x, biaya komisi taker 0.05%, dan
            pendanaan funding 0.01%/8 jam.
          </p>
          <div class="bento-meta mono">LEVERAGE 1x-20x · SL & TP TERJADWAL</div>
        </div>

        <div class="bento-card bento-wide">
          <div class="bento-num mono">04 / COPY-TRADE</div>
          <h3>API Copy-Trade & Ekspor Sinyal</h3>
          <p>
            Sinyal eksekusi order disiarkan secara instan melalui WebSocket
            channel publik. Dilengkapi modul API key untuk menghubungkan bot
            eksternal atau terminal eksekusi otomatis.
          </p>
          <div class="bento-meta mono">
            WEBSOCKET BROADCAST · REST API ENDPOINTS
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Institutional Footer -->
  <footer class="landing-footer">
    <div class="footer-container">
      <div class="foot-left">
        <div class="foot-title">STRATEGY ARENA</div>
        <p class="foot-desc">Platform benchmark kuantitatif mandiri.</p>
      </div>

      <div class="foot-links">
        <button class="foot-btn" onclick={() => enterTerminal("spot")}
          >Terminal Spot</button
        >
        <button class="foot-btn" onclick={() => enterTerminal("futures")}
          >Terminal Futures</button
        >
        <button class="foot-btn" onclick={() => enterTerminal("forex")}
          >Terminal Forex</button
        >
        <button class="foot-btn foot-neural" onclick={() => arena.navigate("/neural-execution")}
          >Neural Execution</button
        >
        <a href="/api/bootstrap" target="_blank" class="foot-btn"
          >API Bootstrap</a
        >
      </div>
    </div>
  </footer>
</div>

<style>
  .landing-root {
    min-height: 100vh;
    background-color: #070a0f;
    color: #f1f5f9;
    display: flex;
    flex-direction: column;
    font-family: "Inter", sans-serif;
    overflow-x: hidden;
    width: 100%;
    max-width: 100vw;
    box-sizing: border-box;
  }

  /* Header */
  .landing-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #090d14;
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .landing-nav-container {
    max-width: 1440px;
    margin: 0 auto;
    padding: 12px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .brand-title {
    font-size: 15px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
  }

  .brand-title span {
    color: #f59e0b;
  }

  .brand-sub {
    font-size: 9px;
    letter-spacing: 0.12em;
    color: #64748b;
    font-weight: 600;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }


  .nav-btn {
    padding: 7px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-neural {
        background: #151c29;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .btn-neural:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  .btn-spot {
    background: #151c29;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .btn-spot:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  .btn-futures {
    background: #151c29;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .btn-futures:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  .btn-forex {
    background: #151c29;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .btn-forex:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  /* Hamburger Menu (Mobile Only) */
  .hamburger-btn {
    display: none;
    background: #0d121c;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    color: #e2e8f0;
    padding: 6px 8px;
    cursor: pointer;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
  }

  .hamburger-btn:hover {
    background: #151d2c;
    border-color: rgba(245, 158, 11, 0.4);
    color: #f59e0b;
  }

  .hamburger-btn.active {
    background: rgba(245, 158, 11, 0.15);
    border-color: #f59e0b;
    color: #f59e0b;
  }

  /* Mobile Drawer Dropdown */
  .mobile-drawer-backdrop {
    position: fixed;
    top: 57px;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(3, 7, 18, 0.85);
    backdrop-filter: blur(10px);
    z-index: 100;
    animation: fadeIn 0.18s ease;
  }

  /* STRICTLY hide mobile drawer on Desktop/PC (width > 900px) */
  @media (min-width: 901px) {
    .mobile-drawer-backdrop {
      display: none !important;
    }
  }

  .mobile-drawer-content {
    background: #090e17;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    padding: 16px 16px 20px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
    animation: slideDown 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .drawer-header {
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .drawer-title {
    display: block;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.1em;
    color: #f59e0b;
  }

  .drawer-sub {
    display: block;
    font-size: 12px;
    color: #94a3b8;
    margin-top: 2px;
  }

  .drawer-nav-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .drawer-nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #0c121d;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 12px 14px;
    text-align: left;
    cursor: pointer;
    transition: all 0.15s ease;
    width: 100%;
    color: inherit;
    box-sizing: border-box;
  }

  .drawer-nav-item:hover,
  .drawer-nav-item:active {
    background: #151d2c;
    border-color: rgba(255, 255, 255, 0.2);
    transform: translateX(2px);
  }

  .drawer-icon {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .icon-spot {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
  }
  .dot-spot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f59e0b;
    box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
  }

  .icon-futures {
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
  }
  .dot-futures {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
  }

  .icon-forex {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
  }
  .dot-forex {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
  }

  .icon-neural {
    background: rgba(168, 85, 247, 0.15);
    border: 1px solid rgba(168, 85, 247, 0.35);
  }
  .dot-neural {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #a855f7;
    box-shadow: 0 0 8px rgba(168, 85, 247, 0.6);
  }

  .drawer-item-info {
    flex: 1;
    min-width: 0;
  }

  .item-name {
    display: block;
    font-size: 13.5px;
    font-weight: 700;
    color: #f1f5f9;
  }

  .item-desc {
    display: block;
    font-size: 11px;
    color: #64748b;
    margin-top: 2px;
  }

  .chevron-svg {
    color: #475569;
    flex-shrink: 0;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideDown {
    from { transform: translateY(-12px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  /* Hero Section */
  .hero-section {
    position: relative;
    padding: 64px 24px 84px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #030712;
    overflow: hidden;
    min-height: 680px;
    display: flex;
    align-items: center;
  }

  .hero-bg-3d {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
    overflow: hidden;
  }

  .hero-vignette-overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 2;
    background: linear-gradient(
      90deg,
      rgba(3, 7, 18, 0.96) 0%,
      rgba(3, 7, 18, 0.88) 38%,
      rgba(3, 7, 18, 0.45) 68%,
      rgba(3, 7, 18, 0.15) 100%
    );
  }

  .hero-container {
    position: relative;
    z-index: 3;
    max-width: 1440px;
    width: 100%;
    margin: 0 auto;
    pointer-events: none;
  }

  .hero-content {
    max-width: 680px;
    pointer-events: auto;
  }

  .hero-institutional-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    padding: 5px 12px;
    border-radius: 20px;
    margin-bottom: 20px;
    backdrop-filter: blur(8px);
  }

  .pulse-cyan-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 8px #38bdf8;
    animation: pulse 1.8s infinite;
  }

  .hero-eyebrow-brand {
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #f59e0b;
    margin: 0 0 4px 0;
    text-transform: uppercase;
  }

  .hero-title {
    font-size: 44px;
    font-weight: 800;
    line-height: 1.08;
    letter-spacing: -0.03em;
    color: #ffffff;
    margin: 0 0 20px 0;
  }

  .hero-desc {
    font-size: 15px;
    line-height: 1.6;
    color: #94a3b8;
    max-width: 580px;
    margin: 0 0 32px 0;
  }

  .hero-ctas {
    display: flex;
    gap: 14px;
    margin-bottom: 40px;
    flex-wrap: wrap;
  }

  .cta-secondary {
    background: #111722;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
    padding: 12px 22px;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s ease;
  }

  .cta-secondary:hover {
    border-color: rgba(255, 255, 255, 0.35);
    background: #161e2c;
    transform: translateY(-1px);
  }

  .cta-neural {
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.15) 0%, rgba(126, 34, 206, 0.08) 100%);
    border: 1px solid rgba(168, 85, 247, 0.45);
    box-shadow: 0 4px 16px rgba(168, 85, 247, 0.15);
  }

  .cta-neural:hover {
    border-color: rgba(168, 85, 247, 0.7);
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.25) 0%, rgba(126, 34, 206, 0.15) 100%);
  }


  .cta-secondary .cta-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }

  .cta-secondary .cta-sub {
    font-size: 9.5px;
    font-weight: 600;
    color: #64748b;
    margin-top: 3px;
  }

  .metrics-quad {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    padding-top: 24px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .metric-item .m-val {
    display: block;
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.02em;
  }

  .metric-item .m-lbl {
    display: block;
    font-size: 11px;
    color: #64748b;
    margin-top: 4px;
  }

  /* Podium Section */
  .podium-section {
    padding: 64px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #090d14;
  }

  .section-container {
    max-width: 1440px;
    margin: 0 auto;
  }

  .section-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 28px;
    flex-wrap: wrap;
    gap: 16px;
  }

  .section-head h2 {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
    margin: 0 0 6px 0;
  }

  .section-desc {
    font-size: 13.5px;
    color: #64748b;
    margin: 0;
  }

  /* Executive Leaderboard Section */
  .leaderboard-section {
    padding: 64px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #04070c;
  }

  .executive-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 28px;
    flex-wrap: wrap;
    gap: 16px;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .super-tag {
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.12em;
    color: #f59e0b;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .executive-head h2 {
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
    margin: 0 0 6px 0;
  }

  .section-desc {
    font-size: 13.5px;
    color: #94a3b8;
    margin: 0;
    max-width: 820px;
    line-height: 1.5;
  }

  .head-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .btn-group-toggle,
  .btn-group-limit {
    display: flex;
    background: #090e17;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 3px;
    gap: 3px;
  }

  .toggle-btn,
  .limit-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    padding: 7px 13px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .toggle-btn:hover,
  .limit-btn:hover {
    color: #ffffff;
  }

  .toggle-btn.active,
  .limit-btn.active {
    background: #1e293b;
    color: #f59e0b;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  .limit-label {
    font-size: 10px;
    font-weight: 700;
    color: #475569;
    display: flex;
    align-items: center;
    padding: 0 6px;
  }

  .live-dot-pulse {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: pulse-dot 2s infinite ease-in-out;
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.85); }
  }

  /* 1. 3D Stepped Olympic Podium Hero Stage */
  .podium-hero-stage {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    gap: 24px;
    margin-top: 16px;
    margin-bottom: 40px;
    position: relative;
    padding-top: 20px;
  }

  .podium-pillar-card {
    display: flex;
    flex-direction: column;
    width: 340px;
    min-height: 275px;
    border-radius: 16px;
    position: relative;
    cursor: pointer;
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease, border-color 0.25s ease;
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  }

  .podium-pillar-card:hover {
    transform: translateY(-6px);
  }

  /* Champion Gold #1 (Elevated) */
  .rank-gold {
    width: 375px;
    min-height: 298px;
    border: 1px solid rgba(245, 158, 11, 0.5);
    background: linear-gradient(180deg, #141b27 0%, #070a10 100%);
    transform: translateY(-16px);
    z-index: 3;
  }

  .rank-gold:hover {
    transform: translateY(-22px);
    border-color: rgba(245, 158, 11, 0.85);
  }

  .champion-halo {
    position: absolute;
    top: -60px;
    left: 50%;
    transform: translateX(-50%);
    width: 220px;
    height: 120px;
    pointer-events: none;
  }

  /* Runner Up Silver #2 */
  .rank-silver {
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: linear-gradient(180deg, #0e1420 0%, #07090f 100%);
    transform: translateY(0px);
  }

  .rank-silver:hover {
    transform: translateY(-6px);
    border-color: rgba(148, 163, 184, 0.65);
  }

  /* Third Place Bronze #3 */
  .rank-bronze {
    border: 1px solid rgba(217, 119, 6, 0.35);
    background: linear-gradient(180deg, #10121a 0%, #07080e 100%);
    transform: translateY(10px);
  }

  .rank-bronze:hover {
    transform: translateY(4px);
    border-color: rgba(217, 119, 6, 0.65);
  }

  .pillar-crown {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .trophy-badge {
    font-size: 11.5px;
    font-weight: 800;
    letter-spacing: 0.05em;
  }

  .gold-trophy {
    color: #fbbf24;
    text-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
  }

  .silver-trophy {
    color: #cbd5e1;
  }

  .bronze-trophy {
    color: #f59e0b;
  }

  .strat-cat-pill {
    font-size: 9.5px;
    padding: 2px 7px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    color: #94a3b8;
  }

  .gold-pill {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .pillar-body {
    padding: 16px 20px;
  }

  .strat-headline {
    font-size: 17px;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 8px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .gold-name {
    font-size: 19px;
  }

  .pnl-callout {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .pnl-val {
    font-size: 20px;
    font-weight: 800;
  }

  .gold-pnl {
    color: #10b981;
    font-size: 22px;
  }

  .ret-badge {
    font-size: 11px;
    font-weight: 800;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .ret-up {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
  }

  .ret-down {
    background: rgba(244, 63, 94, 0.15);
    color: #f43f5e;
  }

  .ret-gold {
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.4);
  }

  .bal-sub {
    font-size: 11.5px;
    color: #64748b;
    margin-bottom: 12px;
  }

  .bal-sub b {
    color: #cbd5e1;
  }

  .gold-text {
    color: #fef08a !important;
  }

  .market-split-chips {
    display: flex;
    gap: 6px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .split-chip {
    font-size: 10px;
    padding: 3px 6px;
    border-radius: 4px;
    background: #0d1420;
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: #94a3b8;
  }

  .chip-up {
    color: #34d399;
  }

  .chip-down {
    color: #f87171;
  }

  .acc-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    color: #64748b;
  }

  .acc-row b {
    color: #cbd5e1;
  }

  .acc-bar-wrap {
    width: 48px;
    height: 4px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 2px;
    overflow: hidden;
  }

  .acc-bar {
    height: 100%;
    border-radius: 2px;
  }

  .acc-gold {
    background: #f59e0b;
  }

  .acc-silver {
    background: #94a3b8;
  }

  .acc-bronze {
    background: #d97706;
  }

  /* Integrated Background Trend Chart in Podium Cards (Soft Ambient Watermark) */
  .card-trend-bg {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    height: 155px;
    overflow: hidden;
    pointer-events: none;
    z-index: 1;
    opacity: 0.28;
    transition: opacity 0.25s ease;
  }

  .podium-pillar-card:hover .card-trend-bg {
    opacity: 0.42;
  }

  .bg-chart-svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  .card-content-layer {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
  }

  .watermark-num {
    font-size: 110px;
    font-weight: 900;
    position: absolute;
    right: 14px;
    bottom: -15px;
    color: rgba(255, 255, 255, 0.04);
    user-select: none;
    pointer-events: none;
    line-height: 1;
    transition: color 0.25s ease;
  }

  .podium-pillar-card:hover .watermark-num {
    color: rgba(255, 255, 255, 0.08);
  }

  .card-footer-action {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px 14px;
    font-size: 10px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.05em;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    margin-top: 6px;
    transition: color 0.15s ease;
  }

  .action-arrow {
    font-size: 13px;
    transition: transform 0.15s ease;
  }


  /* 2. Visual Analytics Center (Multi-Line & Donut) */
  .visual-analytics-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    gap: 20px;
    margin-bottom: 32px;
  }

  .analytic-panel-box {
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    padding-bottom: 12px;
    margin-bottom: 14px;
    gap: 16px;
  }

  .title-badge-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
  }

  .panel-tag {
    font-size: 9.5px;
    font-weight: 800;
    color: #f59e0b;
    letter-spacing: 0.1em;
    display: inline-block;
  }

  .live-audit-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #10b981;
    font-size: 9px;
    font-weight: 800;
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: 0.06em;
  }

  .pulse-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 6px #10b981;
    animation: pulseGlow 1.8s infinite;
  }

  @keyframes pulseGlow {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.85); }
  }

  .panel-head h4 {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
  }

  .panel-controls {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .timeframe-selector {
    display: flex;
    align-items: center;
    background: #090e18;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 2px;
    gap: 2px;
  }

  .tf-btn {
    background: transparent;
    border: 1px solid transparent;
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .tf-btn:hover {
    color: #cbd5e1;
    background: rgba(255, 255, 255, 0.04);
  }

  .tf-btn.active {
    background: #172235;
    color: #f59e0b;
    border-color: rgba(245, 158, 11, 0.4);
    box-shadow: 0 0 8px rgba(245, 158, 11, 0.15);
  }

  .panel-meta {
    font-size: 11px;
    color: #64748b;
    font-weight: 600;
    white-space: nowrap;
  }

  .chart-canvas-wrap {
    width: 100%;
    height: 230px;
    position: relative;
    background: #06090e;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.04);
    overflow: hidden;
  }

  .multi-line-svg {
    width: 100%;
    height: 100%;
  }

  .chart-axis-baseline {
    position: absolute;
    bottom: 8px;
    right: 12px;
    font-size: 10px;
    color: #475569;
    font-weight: 600;
    background: rgba(6, 9, 14, 0.7);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .chart-hover-tooltip {
    position: absolute;
    top: 10px;
    width: 275px;
    box-sizing: border-box;
    background: rgba(8, 12, 22, 0.96);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(245, 158, 11, 0.5);
    border-radius: 8px;
    padding: 10px 14px;
    pointer-events: auto;
    z-index: 10;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.7);
  }

  .tt-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 6px;
    margin-bottom: 8px;
  }

  .tt-date-title {
    font-size: 11.5px;
    font-weight: 800;
    color: #f59e0b;
    letter-spacing: 0.05em;
  }

  .tt-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .tt-strat-focus {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 4px;
  }

  .tt-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .tt-rank {
    font-weight: 800;
    color: #94a3b8;
    font-size: 11px;
    flex-shrink: 0;
  }

  .tt-name {
    color: #ffffff;
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
    min-width: 0;
  }

  .tt-cat-tag {
    font-size: 9px;
    padding: 1px 6px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 3px;
    color: #94a3b8;
    margin-left: auto;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .tt-stat-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    padding: 6px 10px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tt-stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 11px;
    white-space: nowrap;
    gap: 8px;
  }

  .tt-stat-lbl {
    font-size: 10px;
    color: #94a3b8;
    white-space: nowrap;
    flex-shrink: 0;
  }


  .tt-stat-row.tt-sub {
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    padding-top: 4px;
    margin-top: 2px;
    font-size: 10px;
    color: #64748b;
  }

  .tt-footer-hint {
    font-size: 9px;
    color: #64748b;
    margin-top: 6px;
    text-align: center;
  }

  .tt-reset-link {
    background: transparent;
    border: none;
    color: #f59e0b;
    font-size: 9.5px;
    font-weight: 700;
    cursor: pointer;
    text-decoration: underline;
    padding: 0;
  }

  .tt-reset-link:hover {
    color: #fbbf24;
  }

  .chart-timeline-axis {
    position: relative;
    width: 100%;
    height: 38px;
    margin-top: 6px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }

  .timeline-tick {
    position: absolute;
    transform: translateX(-50%);
    text-align: center;
    white-space: nowrap;
  }

  .tick-line {
    display: block;
    width: 1px;
    height: 5px;
    background: rgba(255, 255, 255, 0.25);
    margin: 0 auto 3px;
  }

  .tick-day {
    display: block;
    font-size: 10px;
    font-weight: 700;
    color: #cbd5e1;
    line-height: 1.1;
  }

  .tick-date {
    display: block;
    font-size: 9px;
    color: #64748b;
    line-height: 1.1;
  }

  .chart-legend-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 14px;
  }

  .legend-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #0d1422;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 11px;
    cursor: pointer;
    color: inherit;
    transition: all 0.15s ease;
  }

  .legend-pill:hover {
    border-color: rgba(255, 255, 255, 0.25);
    transform: translateY(-1px);
  }

  .legend-pill.active-focus {
    transform: translateY(-2px);
    background: #141f33;
  }

  .legend-reset-btn {
    background: #162032;
    color: #cbd5e1;
    border: 1px solid rgba(255, 255, 255, 0.15);
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .legend-reset-btn:hover {
    background: #1e2c45;
    color: #ffffff;
    border-color: rgba(245, 158, 11, 0.5);
  }

  .color-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .leg-rank {
    font-weight: 800;
    color: #94a3b8;
  }

  .leg-name {
    color: #ffffff;
    font-weight: 600;
  }

  .leg-val {
    font-weight: 700;
  }

  /* Donut Section */
  .donut-content-layout {
    display: flex;
    align-items: center;
    gap: 24px;
    margin-top: 10px;
  }

  .donut-chart-box {
    position: relative;
    width: 150px;
    height: 150px;
    flex-shrink: 0;
  }

  .donut-svg {
    transform: rotate(-90deg);
  }

  .donut-center-info {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
  }

  .d-total {
    display: block;
    font-size: 14px;
    font-weight: 800;
  }

  .d-label {
    display: block;
    font-size: 8.5px;
    color: #64748b;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .donut-legend-col {
    flex: 1;
    min-width: 0;
  }

  .market-shares {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 14px;
  }

  .share-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
  }

  .share-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .bg-gold { background: #f59e0b; }
  .bg-cyan { background: #06b6d4; }
  .bg-emerald { background: #10b981; }
  .text-cyan { color: #06b6d4; }
  .text-emerald { color: #10b981; }

  .share-lbl {
    color: #94a3b8;
  }

  .share-val {
    font-weight: 700;
    margin-left: auto;
  }

  .archetype-bar-section {
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding-top: 10px;
  }

  .arch-head {
    font-size: 9px;
    color: #64748b;
    font-weight: 800;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }

  .arch-list {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .arch-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .arch-meta {
    display: flex;
    justify-content: space-between;
    font-size: 10.5px;
  }

  .arch-name {
    color: #cbd5e1;
  }

  .arch-prog-wrap {
    width: 100%;
    height: 3px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 2px;
    overflow: hidden;
  }

  .arch-prog-fill {
    height: 100%;
    background: #f59e0b;
    border-radius: 2px;
  }

  /* 3. Master Universal Strategy Matrix Table */
  .master-matrix-card {
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 28px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  }

  .matrix-card-head {
    padding: 16px 22px;
    background: #0d1422;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }

  .matrix-tag {
    font-size: 9.5px;
    font-weight: 800;
    color: #f59e0b;
    letter-spacing: 0.1em;
    display: block;
    margin-bottom: 2px;
  }

  .matrix-title-wrap h3 {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
  }

  .matrix-hint {
    font-size: 11px;
    color: #64748b;
  }

  .master-table-wrap {
    width: 100%;
    overflow-x: auto;
  }

  .master-strategy-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
  }

  .master-strategy-table th {
    padding: 12px 18px;
    background: #0a0f18;
    color: #64748b;
    font-weight: 700;
    font-size: 10.5px;
    letter-spacing: 0.06em;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    text-align: left;
    white-space: nowrap;
  }

  .master-strategy-table th.r { text-align: right; }
  .master-strategy-table th.c { text-align: center; }

  .matrix-tr {
    cursor: pointer;
    transition: background 0.15s ease;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }

  .matrix-tr:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  .matrix-tr td {
    padding: 12px 18px;
    vertical-align: middle;
  }

  .matrix-tr td.r { text-align: right; }
  .matrix-tr td.c { text-align: center; }

  .top-1-row {
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.08) 0%, transparent 60%);
  }

  .top-2-row {
    background: linear-gradient(90deg, rgba(148, 163, 184, 0.05) 0%, transparent 60%);
  }

  .top-3-row {
    background: linear-gradient(90deg, rgba(217, 119, 6, 0.05) 0%, transparent 60%);
  }

  .badge-gold-ribbon {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.4);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 800;
    font-size: 11px;
  }

  .badge-silver-ribbon {
    background: rgba(148, 163, 184, 0.15);
    color: #e2e8f0;
    border: 1px solid rgba(148, 163, 184, 0.3);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 800;
    font-size: 11px;
  }

  .badge-bronze-ribbon {
    background: rgba(217, 119, 6, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(217, 119, 6, 0.3);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 800;
    font-size: 11px;
  }

  .badge-std-rank {
    color: #64748b;
    font-weight: 700;
    font-size: 12px;
  }

  .strat-title-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
  }

  .strat-fullname {
    font-size: 13.5px;
    color: #ffffff;
    white-space: nowrap;
  }

  .strat-family-tag {
    font-size: 9.5px;
    padding: 2px 6px;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.06);
    color: #94a3b8;
    white-space: nowrap;
  }

  .strat-code-id {
    font-size: 10px;
  }

  .tri-pills-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tri-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 4px;
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.06);
    white-space: nowrap;
  }

  .dot-spot { width: 5px; height: 5px; border-radius: 50%; background: #10b981; }
  .dot-fut { width: 5px; height: 5px; border-radius: 50%; background: #06b6d4; }
  .dot-fx { width: 5px; height: 5px; border-radius: 50%; background: #f59e0b; }

  .tri-up { color: #34d399; }
  .tri-down { color: #f87171; }

  .wr-progress-col {
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: flex-end;
  }

  .wr-num-bold {
    font-weight: 700;
    color: #e2e8f0;
  }

  .mini-wr-track {
    width: 36px;
    height: 4px;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 2px;
    overflow: hidden;
  }

  .mini-wr-fill {
    height: 100%;
    background: #10b981;
    border-radius: 2px;
  }

  .open-strat-btn {
    padding: 4px 10px;
    background: #111827;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #cbd5e1;
    border-radius: 5px;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .open-strat-btn:hover {
    background: #f59e0b;
    color: #04070c;
    border-color: #f59e0b;
  }

  /* 4. Executive Analyst Summary Strip */
  .executive-summary-strip {
    margin-top: 28px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
  }

  .summary-card {
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    padding: 16px 18px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  }

  .s-icon {
    font-size: 24px;
    line-height: 1;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 10px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .s-content {
    flex: 1;
  }

  .s-label {
    font-size: 9.5px;
    font-weight: 800;
    color: #64748b;
    letter-spacing: 0.1em;
    display: block;
  }

  .s-value {
    font-size: 17px;
    font-weight: 800;
    margin: 3px 0 5px 0;
  }

  .s-desc {
    font-size: 11.5px;
    color: #94a3b8;
    margin: 0;
    line-height: 1.5;
  }

  .text-white { color: #ffffff; }
  .text-gold { color: #f59e0b; }
  .font-bold { font-weight: 700; }
  .muted { color: #64748b; }
  .up { color: #10b981; }
  .down { color: #f43f5e; }

  @media (max-width: 1080px) {
    .podium-hero-stage {
      flex-direction: column;
      align-items: center;
    }
    .rank-gold {
      transform: none;
      order: -1;
      width: 100%;
      max-width: 380px;
    }
    .rank-silver, .rank-bronze {
      width: 100%;
      max-width: 380px;
    }
    .visual-analytics-grid {
      grid-template-columns: 1fr;
    }
  }

  /* Bento Architecture Section */
  .bento-section {
    padding: 64px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .bento-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
  }

  .bento-card {
    background: #090d14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .bento-wide {
    grid-column: span 2;
  }

  .bento-num {
    font-size: 11px;
    font-weight: 700;
    color: #f59e0b;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
  }

  .bento-card h3 {
    font-size: 17px;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 10px 0;
  }

  .bento-card p {
    font-size: 13.5px;
    line-height: 1.6;
    color: #94a3b8;
    margin: 0 0 20px 0;
  }

  .bento-meta {
    font-size: 10px;
    color: #475569;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  /* Footer */
  .landing-footer {
    padding: 36px 24px;
    background: #05080c;
  }

  .footer-container {
    max-width: 1440px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
  }

  .foot-title {
    font-size: 13px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.04em;
  }

  .foot-desc {
    font-size: 12px;
    color: #64748b;
    margin: 4px 0 0 0;
  }

  .foot-links {
    display: flex;
    gap: 12px;
  }

  .foot-btn {
    background: none;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 11.5px;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.15s ease;
  }

  .foot-btn:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  @media (max-width: 1024px) {
    .hero-container {
      grid-template-columns: 1fr;
    }
    .podium-grid {
      grid-template-columns: 1fr;
    }
    .bento-grid {
      grid-template-columns: 1fr;
    }
    .bento-wide {
      grid-column: span 1;
    }
  }

  @media (max-width: 900px) {
    .landing-nav-container {
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      padding: 10px 16px;
    }
    .desktop-nav {
      display: none !important;
    }
    .hamburger-btn {
      display: flex;
    }
  }

  @media (max-width: 768px) {
    .hero-section {
      padding: 32px 14px 44px;
      min-height: auto;
    }
    .hero-eyebrow-brand {
      font-size: 20px;
    }
    .hero-title {
      font-size: 26px;
      line-height: 1.15;
      margin-bottom: 12px;
    }
    .hero-desc {
      font-size: 12.5px;
      margin-bottom: 20px;
    }
    .hero-ctas {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      margin-bottom: 24px;
    }
    .metrics-quad {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      padding-top: 14px;
    }
    .metric-item .m-val {
      font-size: 17px;
    }
    .podium-section {
      padding: 32px 14px;
    }
    .executive-head {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 16px;
    }
    .executive-head h2 {
      font-size: 18px;
    }
    .section-desc {
      font-size: 12px;
    }
    .head-controls {
      width: 100%;
    }
    .btn-group-toggle {
      width: 100%;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 4px;
      box-sizing: border-box;
    }
    .toggle-btn {
      text-align: center;
      padding: 7px 6px;
      font-size: 10.5px;
      width: 100%;
      box-sizing: border-box;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .podium-pillar-card,
    .rank-gold,
    .rank-silver,
    .rank-bronze {
      width: 100% !important;
      max-width: 100% !important;
      box-sizing: border-box;
    }
    .champion-halo {
      display: none;
    }
    .master-table-wrap {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      width: 100%;
    }
    .master-strategy-table {
      min-width: 640px;
    }
    .landing-footer {
      padding: 24px 14px;
    }
    .footer-container {
      flex-direction: column;
      align-items: flex-start;
      gap: 16px;
    }
    .foot-links {
      width: 100%;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }
    .foot-btn {
      text-align: center;
    }
  }

  @media (max-width: 480px) {
    .hero-eyebrow-brand {
      font-size: 16px;
    }
    .hero-title {
      font-size: 23px;
    }
    .executive-head h2 {
      font-size: 17px;
    }
    .brand-title {
      font-size: 13.5px;
    }
  }
</style>
