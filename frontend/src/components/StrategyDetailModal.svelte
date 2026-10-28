<script>
  import { onMount } from 'svelte';
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent, formatPrice } from '../lib/formatters.js';
  import { getStrategyCategory, getRuleText } from '../lib/constants.js';

  let {
    strategy,
    rank = 1,
    totalStrategies = 53,
    openPositionsCount = 0,
    isOpen = $bindable(false)
  } = $props();

  let activeTab = $state('chart'); // 'chart', 'stats', 'trades'
  let selectedHours = $state(24); // 24, 72, 168, 720, 2160
  let loadingData = $state(false);

  // Strategy detailed data fetched from API
  let detailData = $state(null);
  let curvePoints = $state([]);
  let closedTrades = $state([]);

  // Trade History Filter State
  let tradeFilter = $state('all'); // 'all', 'win', 'loss'
  let tradeSearch = $state('');

  // Canvas ref for large chart
  let chartCanvas = $state(null);
  let crosshair = $state({ active: false, x: 0, y: 0, dataPoint: null });

  async function fetchDetail(sid, mode, hours) {
    if (!sid) return;
    loadingData = true;
    try {
      const res = await fetch(`/api/strategy/${sid}?mode=${mode}&hours=${hours}`);
      if (res.ok) {
        const json = await res.json();
        detailData = json;
        curvePoints = json.curve || [];
        closedTrades = json.trades || [];
      }
    } catch (e) {
      console.error('Failed to fetch detailed strategy stats:', e);
    } finally {
      loadingData = false;
    }
  }

  let lastLoadedSid = $state(null);
  let lastLoadedMode = $state(null);
  let lastLoadedHours = $state(null);

  // Reload ONLY when modal opens with a new strategy, mode, or timeframe
  $effect(() => {
    if (!isOpen) {
      lastLoadedSid = null;
      lastLoadedMode = null;
      lastLoadedHours = null;
      return;
    }
    const sid = strategy?.id;
    const mode = arena.mode;
    const hours = selectedHours;
    if (!sid) return;

    if (sid !== lastLoadedSid || mode !== lastLoadedMode || hours !== lastLoadedHours) {
      lastLoadedSid = sid;
      lastLoadedMode = mode;
      lastLoadedHours = hours;
      currentPage = 1;
      fetchDetail(sid, mode, hours);
    }
  });

  // Effective curve combining history with live equity
  let effectiveCurve = $derived.by(() => {
    const strat = strategy;
    if (!strat) return [];
    const now = Date.now();
    const liveBal = strat.balance ?? strat.cash ?? strat.equity ?? 10000;

    let pts = [...curvePoints];
    if (pts.length === 0) {
      return [
        { ts: now - selectedHours * 3600 * 1000, equity: 10000 },
        { ts: now, equity: liveBal },
      ];
    }

    const lastPt = pts[pts.length - 1];
    if (Math.abs(now - lastPt.ts) > 3000 || Math.abs(liveBal - lastPt.equity) > 0.01) {
      pts.push({ ts: now, equity: liveBal });
    }
    return pts;
  });

  // Filtered trades list
  let filteredTrades = $derived.by(() => {
    return closedTrades.filter((t) => {
      // Filter by win/loss
      if (tradeFilter === 'win' && t.pnl <= 0) return false;
      if (tradeFilter === 'loss' && t.pnl > 0) return false;

      // Filter by search query
      if (tradeSearch.trim()) {
        const q = tradeSearch.trim().toUpperCase();
        if (!t.symbol?.toUpperCase().includes(q) && !t.reason?.toUpperCase().includes(q)) {
          return false;
        }
      }
      return true;
    });
  });

  // Table Pagination State
  let pageSize = $state(50); // 25, 50, 100, or 'all'
  let currentPage = $state(1);
  let tableWrapEl = $state(null);

  let totalPages = $derived.by(() => {
    if (pageSize === 'all' || !filteredTrades.length) return 1;
    return Math.max(1, Math.ceil(filteredTrades.length / pageSize));
  });

  let paginatedTrades = $derived.by(() => {
    if (pageSize === 'all') return filteredTrades;
    const start = (currentPage - 1) * pageSize;
    return filteredTrades.slice(start, start + pageSize);
  });

  function setFilter(f) {
    tradeFilter = f;
    currentPage = 1;
    if (tableWrapEl) {
      tableWrapEl.scrollTop = 0;
    }
  }

  function setPageSize(sz) {
    pageSize = sz;
    currentPage = 1;
    if (tableWrapEl) {
      tableWrapEl.scrollTop = 0;
    }
  }

  function goToPage(p) {
    const target = Math.max(1, Math.min(totalPages, p));
    currentPage = target;
    if (tableWrapEl) {
      tableWrapEl.scrollTop = 0;
    }
  }

  // Generate visible page numbers for pagination bar (e.g. [1, 2, 3, 4, 5, '...', total])
  let visiblePages = $derived.by(() => {
    const total = totalPages;
    const curr = currentPage;
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }
    if (curr <= 4) {
      return [1, 2, 3, 4, 5, '...', total];
    } else if (curr >= total - 3) {
      return [1, '...', total - 4, total - 3, total - 2, total - 1, total];
    } else {
      return [1, '...', curr - 1, curr, curr + 1, '...', total];
    }
  });

  // Synchronized Trade Counts (prioritize API aggregate counts, then closedTrades, then strategy account)
  let totalTradesCount = $derived.by(() => {
    if (detailData?.trade_counts?.total != null) return detailData.trade_counts.total;
    if (closedTrades.length > 0) return closedTrades.length;
    return strategy?.trades || 0;
  });

  let totalWinsCount = $derived.by(() => {
    if (detailData?.trade_counts?.wins != null) return detailData.trade_counts.wins;
    if (closedTrades.length > 0) return closedTrades.filter((t) => t.pnl > 0).length;
    return strategy?.wins || 0;
  });

  let totalLossesCount = $derived.by(() => {
    if (detailData?.trade_counts?.losses != null) return detailData.trade_counts.losses;
    if (closedTrades.length > 0) return closedTrades.filter((t) => t.pnl <= 0).length;
    return Math.max(0, totalTradesCount - totalWinsCount);
  });

  // Deep Quant Statistics Computations
  let deepStats = $derived.by(() => {
    const strat = strategy;
    if (!strat) return {};

    const trades = closedTrades;
    const totalTrades = totalTradesCount;
    const wins = totalWinsCount;
    const losses = totalLossesCount;
    const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;

    const grossWin = trades.length > 0
      ? trades.filter((t) => t.pnl > 0).reduce((s, t) => s + t.pnl, 0)
      : (strat.gross_win ?? 0);
    const grossLoss = trades.length > 0
      ? Math.abs(trades.filter((t) => t.pnl < 0).reduce((s, t) => s + t.pnl, 0))
      : (strat.gross_loss ?? 0);
    const profitFactor = grossLoss > 0 ? (grossWin / grossLoss).toFixed(2) : (grossWin > 0 ? '∞' : '—');

    const netProfit = (strat.equity ?? 10000) - 10000;
    const avgTrade = totalTrades > 0 ? netProfit / totalTrades : 0;
    const avgWin = wins > 0 ? grossWin / wins : 0;
    const avgLoss = losses > 0 ? grossLoss / losses : 0;
    const payoffRatio = avgLoss > 0 ? (avgWin / avgLoss).toFixed(2) : '—';

    // Estimated Sharpe and Sortino ratio
    let sharpe = '—';
    let sortino = '—';
    if (curvePoints.length > 10) {
      const returns = [];
      for (let i = 1; i < curvePoints.length; i++) {
        const prev = curvePoints[i - 1].equity || 10000;
        const curr = curvePoints[i].equity || 10000;
        returns.push((curr - prev) / prev);
      }
      const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
      const variance = returns.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / returns.length;
      const stdDev = Math.sqrt(variance);

      const downsideReturns = returns.filter((r) => r < 0);
      const downsideVariance = downsideReturns.length > 0 
        ? downsideReturns.reduce((a, b) => a + Math.pow(b, 2), 0) / downsideReturns.length 
        : 0;
      const downsideStdDev = Math.sqrt(downsideVariance);

      if (stdDev > 0) {
        sharpe = ((mean / stdDev) * Math.sqrt(365 * 24)).toFixed(2);
      }
      if (downsideStdDev > 0) {
        sortino = ((mean / downsideStdDev) * Math.sqrt(365 * 24)).toFixed(2);
      }
    }

    return {
      totalTrades,
      wins,
      losses,
      winRate: winRate.toFixed(1) + '%',
      netProfit,
      grossWin,
      grossLoss,
      profitFactor,
      avgTrade,
      avgWin,
      avgLoss,
      payoffRatio,
      maxDD: (strat.max_dd || 0) * 100,
      maxDDAmount: ((strat.max_dd || 0) * 10000),
      sharpe,
      sortino,
      refillCount: strat.refillCount || 0,
      feeRate: arena.mode === 'forex' ? '0.01% (Spread)' : (arena.mode === 'futures' ? '0.04% - 0.05%' : '0.04%'),
      leverage: strat.leverage || 1,
    };
  });

  // Render large interactive chart on canvas with crosshair
  $effect(() => {
    if (activeTab === 'chart' && chartCanvas) {
      renderLargeChart(chartCanvas, effectiveCurve, strategy, crosshair);
    }
  });

  function renderLargeChart(cv, rawPts, strat, ch) {
    if (!cv) return;
    const ctx = cv.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth || 700;
    const h = cv.clientHeight || 340;

    cv.width = w * dpr;
    cv.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const padL = 72;
    const padR = 24;
    const padT = 24;
    const padB = 34;
    const pw = w - padL - padR;
    const ph = h - padT - padB;

    if (pw <= 0 || ph <= 0) return;

    const now = Date.now();
    const windowMs = selectedHours * 3600 * 1000;

    let pts = (rawPts || [])
      .map((p) => ({
        ts: typeof p.ts === 'number' ? p.ts : now,
        equity: typeof p.equity === 'number' ? p.equity : 10000,
      }))
      .sort((a, b) => a.ts - b.ts);

    if (pts.length === 0) {
      const eq = strat?.equity ?? 10000;
      pts = [{ ts: now - windowMs, equity: 10000 }, { ts: now, equity: eq }];
    }

    const latestTs = pts[pts.length - 1].ts;
    const endTs = Math.max(now, latestTs);
    const earliestTs = pts[0].ts;
    const startTs = Math.max(endTs - windowMs, earliestTs);
    const spanMs = Math.max(endTs - startTs, 60000);

    pts = pts.filter((p) => p.ts >= startTs);
    if (pts.length === 0) {
      const eq = strat?.equity ?? 10000;
      pts = [{ ts: startTs, equity: eq }, { ts: endTs, equity: eq }];
    }

    // Determine Y range (include $10,000 baseline)
    const equities = pts.map((p) => p.equity);
    let minV = Math.min(...equities, 9950);
    let maxV = Math.max(...equities, 10050);

    const vSpan = maxV - minV || 50;
    minV = minV - vSpan * 0.08;
    maxV = maxV + vSpan * 0.08;
    const range = maxV - minV;

    const X = (ts) => padL + Math.max(0, Math.min(1, (ts - startTs) / spanMs)) * pw;
    const Y = (v) => padT + ph - ((v - minV) / range) * ph;

    // Y-Axis Dollar Labels & Grid Lines
    const yTicks = 5;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.font = '11px "JetBrains Mono", monospace';
    ctx.fillStyle = '#64748b';

    for (let i = 0; i < yTicks; i++) {
      const val = minV + (range / (yTicks - 1)) * i;
      const y = Y(val);
      ctx.fillText('$' + Math.round(val).toLocaleString('en-US'), padL - 10, y);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + pw, y);
      ctx.stroke();
    }

    // Baseline at Modal Awal $10,000
    const y10k = Y(10000);
    if (y10k >= padT && y10k <= padT + ph) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padL, y10k);
      ctx.lineTo(padL + pw, y10k);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#94a3b8';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'bottom';
      ctx.font = '10px Inter, sans-serif';
      ctx.fillText('MODAL AWAL $10.000', padL + 8, y10k - 5);
    }

    // X-Axis Vertical Lines & Date/Time Ticks
    const xIntervals = 5;
    ctx.textBaseline = 'top';
    ctx.font = '10px "JetBrains Mono", monospace';

    for (let i = 0; i <= xIntervals; i++) {
      const ratio = i / xIntervals;
      const t = startTs + spanMs * ratio;
      const x = padL + ratio * pw;

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, padT);
      ctx.lineTo(x, padT + ph);
      ctx.stroke();

      const dt = new Date(t);
      const day = dt.getDate();
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
      const mon = monthNames[dt.getMonth()];
      const hh = String(dt.getHours()).padStart(2, '0');
      const mm = String(dt.getMinutes()).padStart(2, '0');
      const timeStr = selectedHours > 24 ? `${day} ${mon} ${hh}:${mm}` : `${hh}:${mm}`;

      if (i === 0) ctx.textAlign = 'left';
      else if (i === xIntervals) ctx.textAlign = 'right';
      else ctx.textAlign = 'center';

      ctx.fillStyle = '#64748b';
      ctx.fillText(timeStr, x, padT + ph + 8);
    }

    // Equity Curve Line
    const latestEq = pts[pts.length - 1].equity;
    const isUp = latestEq >= 10000;
    const lineColor = isUp ? '#10b981' : '#f43f5e';
    const areaGrad = ctx.createLinearGradient(0, padT, 0, padT + ph);
    areaGrad.addColorStop(0, isUp ? 'rgba(16, 185, 129, 0.28)' : 'rgba(244, 63, 94, 0.28)');
    areaGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.beginPath();
    pts.forEach((p, i) => {
      const x = X(p.ts);
      const y = Y(p.equity);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2.5;
    ctx.lineJoin = 'round';
    ctx.stroke();

    // Area Fill
    const lastX = X(pts[pts.length - 1].ts);
    ctx.lineTo(lastX, padT + ph);
    ctx.lineTo(padL, padT + ph);
    ctx.closePath();
    ctx.fillStyle = areaGrad;
    ctx.fill();

    // Glowing Endpoint Dot
    const lastY = Y(latestEq);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.shadowColor = lineColor;
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;

    // Interactive Crosshair & Tooltip
    if (ch.active && ch.dataPoint) {
      const cx = X(ch.dataPoint.ts);
      const cy = Y(ch.dataPoint.equity);

      // Vertical line
      ctx.strokeStyle = 'rgba(245, 158, 11, 0.7)';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(cx, padT);
      ctx.lineTo(cx, padT + ph);
      ctx.stroke();

      // Horizontal line
      ctx.beginPath();
      ctx.moveTo(padL, cy);
      ctx.lineTo(padL + pw, cy);
      ctx.stroke();
      ctx.setLineDash([]);

      // Intersection Dot
      ctx.beginPath();
      ctx.arc(cx, cy, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#f59e0b';
      ctx.shadowColor = '#f59e0b';
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Tooltip Card Floating
      const dt = new Date(ch.dataPoint.ts);
      const dtStr = dt.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'medium' });
      const eqVal = ch.dataPoint.equity;
      const diff = eqVal - 10000;
      const pct = (diff / 10000) * 100;

      const ttipW = 180;
      const ttipH = 64;
      let ttipX = cx + 12;
      let ttipY = cy - 32;
      if (ttipX + ttipW > padL + pw) ttipX = cx - ttipW - 12;
      if (ttipY < padT) ttipY = padT + 10;

      ctx.fillStyle = 'rgba(6, 9, 14, 0.95)';
      ctx.strokeStyle = 'rgba(245, 158, 11, 0.5)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.roundRect(ttipX, ttipY, ttipW, ttipH, 6);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.textAlign = 'left';
      ctx.fillText(dtStr, ttipX + 10, ttipY + 18);

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 13px "JetBrains Mono", monospace';
      ctx.fillText(`$${formatUSD(eqVal).replace('$', '')}`, ttipX + 10, ttipY + 38);

      ctx.fillStyle = diff >= 0 ? '#10b981' : '#f43f5e';
      ctx.font = '10.5px "JetBrains Mono", monospace';
      ctx.fillText(`${diff >= 0 ? '+' : ''}${formatUSD(diff)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`, ttipX + 10, ttipY + 54);
    }
  }

  function handleChartMouseMove(e) {
    if (!chartCanvas || effectiveCurve.length === 0) return;
    const rect = chartCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const padL = 72;
    const padR = 24;
    const pw = rect.width - padL - padR;

    if (x >= padL && x <= padL + pw) {
      const ratio = (x - padL) / pw;
      const pts = effectiveCurve;
      const idx = Math.min(pts.length - 1, Math.max(0, Math.round(ratio * (pts.length - 1))));
      crosshair = {
        active: true,
        x,
        y,
        dataPoint: pts[idx],
      };
    } else {
      crosshair = { active: false, x: 0, y: 0, dataPoint: null };
    }
  }

  function handleChartMouseLeave() {
    crosshair = { active: false, x: 0, y: 0, dataPoint: null };
  }

  function formatDuration(openedAt, closedAt) {
    if (!openedAt || !closedAt) return '—';
    const ms = closedAt - openedAt;
    const sec = Math.floor(ms / 1000);
    if (sec < 60) return `${sec}d`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}m ${sec % 60}d`;
    const hrs = Math.floor(min / 60);
    return `${hrs}j ${min % 60}m`;
  }
</script>

{#if isOpen && strategy}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="modal-backdrop" onclick={() => (isOpen = false)}>
    <div class="modal-dialog" onclick={(e) => e.stopPropagation()}>
      <!-- Header -->
      <div class="modal-header">
        <div class="m-left">
          <div class="title-row">
            <h2>{strategy.name}</h2>
            <span class="chip mono">#{rank}/{totalStrategies}</span>
            <span class="chip badge-category mono">
              {#if arena.mode === 'forex' || strategy.mode === 'forex'}
                {(strategy.family || getStrategyCategory(strategy.id)).toUpperCase()} · MT5 DIRECT
              {:else if arena.mode === 'futures'}
                {(strategy.family || getStrategyCategory(strategy.id)).toUpperCase()} · {strategy.leverage || 1}x
              {:else}
                {(strategy.family || getStrategyCategory(strategy.id)).toUpperCase()}
              {/if}
            </span>
            {#if strategy.refillCount > 0}
              <span class="chip-mc mono">MC {strategy.refillCount}x</span>
            {/if}
          </div>
          <p class="rule-text">{getRuleText(strategy)}</p>
        </div>

        <div class="m-right">
          <div class="eq-badge">
            <span class="eq-val mono {(strategy.balance ?? strategy.cash ?? strategy.equity) >= 10000 ? 'up' : 'down'}">
              {formatUSD(strategy.balance ?? strategy.cash ?? strategy.equity)}
            </span>
            <span class="eq-sub mono">
              {formatPercent(strategy.returnPct)} · BALANCE BERSIH · {arena.mode === 'forex' ? 'FOREX MT5 DIRECT' : (arena.mode === 'futures' ? `FUTURES ${strategy.leverage || 1}X` : 'SPOT 1X')} · {openPositionsCount} POSISI TERBUKA
            </span>
          </div>
          <button class="m-close" onclick={() => (isOpen = false)} aria-label="Tutup Modal">×</button>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="modal-tabs">
        <button 
          class="tab-btn mono" 
          class:active={activeTab === 'chart'} 
          onclick={() => (activeTab = 'chart')}
        >
          <svg class="tab-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
            <polyline points="16 7 22 7 22 13"></polyline>
          </svg>
          <span>GRAFIK & TREN LENGKAP ({selectedHours}J)</span>
        </button>
        <button 
          class="tab-btn mono" 
          class:active={activeTab === 'stats'} 
          onclick={() => (activeTab = 'stats')}
        >
          <svg class="tab-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="9"></rect>
            <rect x="14" y="3" width="7" height="5"></rect>
            <rect x="14" y="12" width="7" height="9"></rect>
            <rect x="3" y="16" width="7" height="5"></rect>
          </svg>
          <span>STATISTIK & METRIK QUANT</span>
        </button>
        <button 
          class="tab-btn mono" 
          class:active={activeTab === 'trades'} 
          onclick={() => (activeTab = 'trades')}
        >
          <svg class="tab-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
          </svg>
          <span>RIWAYAT TRADE LENGKAP ({totalTradesCount})</span>
        </button>
      </div>

      <!-- TAB 1: EXTENDED CHART (> 24H) -->
      {#if activeTab === 'chart'}
        <div class="tab-pane">
          <!-- Timeframe Selector Bar -->
          <div class="timeframe-bar">
            <div class="tf-left">
              <span class="tf-label mono">PILIH RENTANG WAKTU:</span>
              <div class="tf-buttons">
                {#each [
                  { label: '24 JAM', h: 24 },
                  { label: '3 HARI', h: 72 },
                  { label: '7 HARI', h: 168 },
                  { label: '30 HARI', h: 720 },
                  { label: 'SEMUA', h: 2160 }
                ] as tf}
                  <button
                    class="tf-btn mono"
                    class:active={selectedHours === tf.h}
                    onclick={() => (selectedHours = tf.h)}
                  >
                    {tf.label}
                  </button>
                {/each}
              </div>
            </div>
          </div>

          <!-- Large High-Res Canvas -->
          <div class="large-chart-wrapper">
            <canvas 
              bind:this={chartCanvas} 
              onmousemove={handleChartMouseMove}
              onmouseleave={handleChartMouseLeave}
            ></canvas>
          </div>

          <div class="chart-legend-row mono">
            <div class="c-leg">
              <span class="leg-dash">---</span>
              <span>Garis Putus-Putus: Modal Awal $10.000</span>
            </div>
            <div class="c-leg">
              <span class="leg-dot dot-live"></span>
              <span>Titik Terakhir: Mark-to-Market Realtime</span>
            </div>
            <div class="c-leg info-leg">
              <svg class="info-svg" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>Arahkan kursor ke grafik untuk inspeksi crosshair & nilai historis</span>
            </div>
          </div>
        </div>
      {/if}

      <!-- TAB 2: DEEP PERFORMANCE METRICS -->
      {#if activeTab === 'stats'}
        <div class="tab-pane">
          <div class="stats-bento">
            <!-- Box 1: Return & PnL -->
            <div class="stat-card">
              <span class="s-label mono">NET PnL / RETURN</span>
              <b class="s-val mono {deepStats.netProfit >= 0 ? 'up' : 'down'}">
                {deepStats.netProfit >= 0 ? '+' : ''}{formatUSD(deepStats.netProfit)}
              </b>
              <span class="s-sub mono">{formatPercent(strategy.returnPct)} dari modal $10.000</span>
            </div>

            <!-- Box 2: Win Rate -->
            <div class="stat-card">
              <span class="s-label mono">WIN RATE</span>
              <b class="s-val mono">{deepStats.winRate}</b>
              <span class="s-sub mono">{deepStats.wins} Menang / {deepStats.losses} Kalah</span>
            </div>

            <!-- Box 3: Profit Factor -->
            <div class="stat-card">
              <span class="s-label mono">PROFIT FACTOR</span>
              <b class="s-val mono text-amber">{deepStats.profitFactor}</b>
              <span class="s-sub mono">Gross Win / Gross Loss</span>
            </div>

            <!-- Box 4: Max Drawdown -->
            <div class="stat-card">
              <span class="s-label mono">MAX DRAWDOWN</span>
              <b class="s-val mono down">{deepStats.maxDD.toFixed(2)}%</b>
              <span class="s-sub mono">Penurunan Maks: -${deepStats.maxDDAmount.toFixed(0)}</span>
            </div>

            <!-- Box 5: Gross Profit -->
            <div class="stat-card">
              <span class="s-label mono">GROSS PROFIT</span>
              <b class="s-val mono up">+{formatUSD(deepStats.grossWin)}</b>
              <span class="s-sub mono">Akumulasi Trade Profit</span>
            </div>

            <!-- Box 6: Gross Loss -->
            <div class="stat-card">
              <span class="s-label mono">GROSS LOSS</span>
              <b class="s-val mono down">-{formatUSD(deepStats.grossLoss)}</b>
              <span class="s-sub mono">Akumulasi Trade Loss</span>
            </div>

            <!-- Box 7: Average Trade -->
            <div class="stat-card">
              <span class="s-label mono">RATA-RATA PnL / TRADE</span>
              <b class="s-val mono {deepStats.avgTrade >= 0 ? 'up' : 'down'}">
                {deepStats.avgTrade >= 0 ? '+' : ''}{formatUSD(deepStats.avgTrade)}
              </b>
              <span class="s-sub mono">Ekspektasi Matematis Rata-rata</span>
            </div>

            <!-- Box 8: Payoff Ratio -->
            <div class="stat-card">
              <span class="s-label mono">PAYOFF RATIO (AVG WIN / LOSS)</span>
              <b class="s-val mono text-cyan">{deepStats.payoffRatio}x</b>
              <span class="s-sub mono">Avg Win: ${deepStats.avgWin.toFixed(1)} | Avg Loss: ${deepStats.avgLoss.toFixed(1)}</span>
            </div>

            <!-- Box 9: Sharpe Ratio -->
            <div class="stat-card">
              <span class="s-label mono">SHARPE RATIO (EST.)</span>
              <b class="s-val mono">{deepStats.sharpe}</b>
              <span class="s-sub mono">Risk-Adjusted Return Tahunan</span>
            </div>

            <!-- Box 10: Sortino Ratio -->
            <div class="stat-card">
              <span class="s-label mono">SORTINO RATIO (EST.)</span>
              <b class="s-val mono">{deepStats.sortino}</b>
              <span class="s-sub mono">Downside Volatility Adjusted</span>
            </div>

            <!-- Box 11: Leverage & Engine -->
            <div class="stat-card">
              <span class="s-label mono">{arena.mode === 'forex' ? 'EXECUTION & SPREAD' : 'LEVERAGE & MARGIN'}</span>
              <b class="s-val mono">{arena.mode === 'forex' ? 'MT5 Direct' : `${deepStats.leverage}x`}</b>
              <span class="s-sub mono">{arena.mode === 'forex' ? 'MetaTrader 5 Direct (Live Headway Feed)' : (arena.mode === 'futures' ? 'Binance Futures (Funding 8h)' : 'Binance Spot (No-Loan)')}</span>
            </div>

            <!-- Box 12: Margin Call Counter -->
            <div class="stat-card">
              <span class="s-label mono">MARGIN CALL STATUS</span>
              <b class="s-val mono {deepStats.refillCount > 0 ? 'down' : 'up'}">
                {deepStats.refillCount === 0 ? 'SEHAT (0 MC)' : `${deepStats.refillCount}x TERKENA MC`}
              </b>
              <span class="s-sub mono">{deepStats.refillCount > 0 ? 'Modal di-refill otomatis ke $10.000' : 'Belum pernah mengalami likuidasi total'}</span>
            </div>
          </div>
        </div>
      {/if}

      <!-- TAB 3: COMPLETE CLOSED TRADES HISTORY -->
      {#if activeTab === 'trades'}
        <div class="tab-pane">
          <!-- Filter & Search Toolbar -->
          <div class="trades-toolbar">
            <div class="filter-group">
              <button 
                class="tb-btn mono" 
                class:active={tradeFilter === 'all'} 
                onclick={() => setFilter('all')}
              >
                SEMUA ({totalTradesCount})
              </button>
              <button 
                class="tb-btn win-btn mono" 
                class:active={tradeFilter === 'win'} 
                onclick={() => setFilter('win')}
              >
                WIN ({totalWinsCount})
              </button>
              <button 
                class="tb-btn loss-btn mono" 
                class:active={tradeFilter === 'loss'} 
                onclick={() => setFilter('loss')}
              >
                LOSS ({totalLossesCount})
              </button>
            </div>

            <div class="search-box">
              <input 
                type="text" 
                placeholder="Cari pair (misal: BTC, PEPE, SOL)..." 
                bind:value={tradeSearch}
                oninput={() => { currentPage = 1; if (tableWrapEl) tableWrapEl.scrollTop = 0; }}
                class="mono"
              />
            </div>
          </div>

          <!-- Trades Table with Pagination -->
          {#if filteredTrades.length === 0}
            <div class="empty-trades">
              <span>Tidak ada riwayat trade yang cocok dengan filter yang dipilih.</span>
            </div>
          {:else}
            <div class="trades-table-wrap" bind:this={tableWrapEl}>
              <table class="trades-table">
                <thead>
                  <tr>
                    <th>Waktu Closed</th>
                    <th>Durasi</th>
                    <th>Pair</th>
                    <th>Arah</th>
                    <th>{arena.mode === 'forex' ? 'Lot' : 'Lev'}</th>
                    <th class="r">Entry Price</th>
                    <th class="r">Exit Price</th>
                    <th class="r">Realized PnL</th>
                    <th>Alasan Exit</th>
                    <th class="r">Ekuitas Setelah Trade</th>
                  </tr>
                </thead>
                <tbody>
                  {#each paginatedTrades as tr (tr.closed_at + '_' + tr.symbol + '_' + tr.pnl)}
                    {@const isWin = tr.pnl >= 0}
                    <tr>
                      <td class="mono date-cell">
                        {new Date(tr.closed_at).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'medium' })}
                      </td>
                      <td class="mono muted-cell">
                        {formatDuration(tr.opened_at, tr.closed_at)}
                      </td>
                      <td class="pair-cell mono">
                        <b>{tr.symbol}</b>
                      </td>
                      <td>
                        <span class="side-pill mono {tr.side === 1 || tr.side === 'LONG' || tr.side === 'BUY' ? 'long' : 'short'}">
                          {tr.side === 1 || tr.side === 'LONG' || tr.side === 'BUY' ? 'LONG' : 'SHORT'}
                        </span>
                      </td>
                      <td class="mono muted-cell">
                        {#if arena.mode === 'forex'}
                          {((tr.lot != null && Number(tr.lot) > 0) ? `${Number(tr.lot).toFixed(2)} Lot` : (tr.qty >= 1000 ? `${(tr.qty / 100000).toFixed(2)} Lot` : `${Number(tr.qty || 0.10).toFixed(2)} Lot`))}
                        {:else}
                          {tr.leverage || 1}x
                        {/if}
                      </td>
                      <td class="r mono">{formatPrice(tr.entry)}</td>
                      <td class="r mono">{formatPrice(tr.exit)}</td>
                      <td class="r mono {isWin ? 'up' : 'down'}">
                        <b>{isWin ? '+' : ''}{formatUSD(tr.pnl)}</b>
                      </td>
                      <td>
                        <span class="reason-tag mono">{tr.reason || 'flip'}</span>
                      </td>
                      <td class="r mono text-slate">
                        {tr.equity_after ? formatUSD(tr.equity_after) : '—'}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>

            <!-- Institutional Pagination Controls Bar -->
            <div class="pagination-bar mono">
              <div class="pg-info">
                Menampilkan 
                <b class="text-white">
                  {filteredTrades.length === 0 ? 0 : (pageSize === 'all' ? 1 : (currentPage - 1) * pageSize + 1)}–{pageSize === 'all' ? filteredTrades.length : Math.min(currentPage * pageSize, filteredTrades.length)}
                </b> 
                dari <b class="text-white">{filteredTrades.length}</b> transaksi
              </div>

              {#if totalPages > 1}
                <div class="pg-controls">
                  <button 
                    type="button" 
                    class="pg-btn pg-nav" 
                    disabled={currentPage === 1}
                    onclick={() => goToPage(1)}
                    title="Halaman Pertama"
                  >
                    «
                  </button>
                  <button 
                    type="button" 
                    class="pg-btn pg-nav" 
                    disabled={currentPage === 1}
                    onclick={() => goToPage(currentPage - 1)}
                    title="Halaman Sebelumnya"
                  >
                    ‹ Prev
                  </button>

                  <div class="pg-pages">
                    {#each visiblePages as p}
                      {#if p === '...'}
                        <span class="pg-ellipsis">…</span>
                      {:else}
                        <button 
                          type="button" 
                          class="pg-btn pg-num" 
                          class:active={currentPage === p}
                          onclick={() => goToPage(p)}
                        >
                          {p}
                        </button>
                      {/if}
                    {/each}
                  </div>

                  <button 
                    type="button" 
                    class="pg-btn pg-nav" 
                    disabled={currentPage === totalPages}
                    onclick={() => goToPage(currentPage + 1)}
                    title="Halaman Berikutnya"
                  >
                    Next ›
                  </button>
                  <button 
                    type="button" 
                    class="pg-btn pg-nav" 
                    disabled={currentPage === totalPages}
                    onclick={() => goToPage(totalPages)}
                    title="Halaman Terakhir"
                  >
                    »
                  </button>
                </div>
              {/if}

              <div class="pg-size-selector">
                <span class="pg-size-lbl">Baris per hal:</span>
                <div class="pg-size-pills">
                  {#each [25, 50, 100, 'all'] as sz}
                    <button 
                      type="button" 
                      class="pg-size-btn" 
                      class:active={pageSize === sz}
                      onclick={() => setPageSize(sz)}
                    >
                      {sz === 'all' ? 'Semua' : sz}
                    </button>
                  {/each}
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(3, 6, 11, 0.85);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }

  .modal-dialog {
    background: #090d16;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    width: 100%;
    max-width: 1100px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
    overflow: hidden;
  }

  /* Header */
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 20px 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #0b111e;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .title-row h2 {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    margin: 0;
    letter-spacing: -0.01em;
  }

  .chip {
    font-size: 11px;
    font-weight: 700;
    background: rgba(255, 255, 255, 0.06);
    color: #94a3b8;
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .badge-category {
    background: rgba(245, 158, 11, 0.12);
    color: #f59e0b;
    border-color: rgba(245, 158, 11, 0.25);
  }

  .chip-mc {
    font-size: 11px;
    font-weight: 700;
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .rule-text {
    font-size: 12px;
    color: #94a3b8;
    margin: 6px 0 0 0;
  }

  .m-right {
    display: flex;
    align-items: center;
    gap: 18px;
  }

  .eq-badge {
    text-align: right;
  }

  .eq-val {
    font-size: 22px;
    font-weight: 800;
    display: block;
    letter-spacing: -0.02em;
  }

  .eq-sub {
    font-size: 10.5px;
    color: #64748b;
    display: block;
    margin-top: 2px;
  }

  .m-close {
    background: none;
    border: none;
    font-size: 28px;
    color: #64748b;
    cursor: pointer;
    line-height: 1;
    padding: 0 4px;
    transition: color 0.15s;
  }

  .m-close:hover {
    color: #ffffff;
  }

  /* Modal Tabs */
  .modal-tabs {
    display: flex;
    background: #080c14;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 0 16px;
  }

  .tab-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: #94a3b8;
    padding: 12px 18px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
    letter-spacing: 0.03em;
  }

  .tab-svg {
    opacity: 0.7;
    transition: all 0.15s;
  }

  .tab-btn:hover {
    color: #ffffff;
  }

  .tab-btn:hover .tab-svg {
    opacity: 1;
    color: #ffffff;
  }

  .tab-btn.active {
    color: #f59e0b;
    border-bottom-color: #f59e0b;
  }

  .tab-btn.active .tab-svg {
    opacity: 1;
    color: #f59e0b;
  }

  /* Tab Pane Content */
  .tab-pane {
    padding: 20px 24px;
    overflow-y: auto;
    max-height: calc(90vh - 150px);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* Timeframe Bar */
  .timeframe-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #070a12;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px 12px;
  }

  .tf-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .tf-label {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
  }

  .tf-buttons {
    display: flex;
    gap: 6px;
  }

  .tf-btn {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #94a3b8;
    padding: 5px 12px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s;
  }

  .tf-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.1);
  }

  .tf-btn.active {
    background: #f59e0b;
    color: #05080f;
    border-color: #f59e0b;
  }

  /* Large Chart Wrapper */
  .large-chart-wrapper {
    background: #070a12;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    height: 340px;
    position: relative;
    overflow: hidden;
  }

  .large-chart-wrapper canvas {
    width: 100%;
    height: 100%;
    display: block;
    cursor: crosshair;
  }

  .chart-legend-row {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: #64748b;
    padding: 0 4px;
    flex-wrap: wrap;
    gap: 10px;
  }

  .c-leg {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .leg-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .dot-live {
    background: #10b981;
    box-shadow: 0 0 6px #10b981;
  }

  /* Stats Bento Grid */
  .stats-bento {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }

  .stat-card {
    background: #070a12;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .s-label {
    font-size: 10px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.04em;
  }

  .s-val {
    font-size: 17px;
    font-weight: 800;
    color: #ffffff;
    margin: 2px 0;
  }

  .s-sub {
    font-size: 10.5px;
    color: #64748b;
  }

  /* Trades Toolbar */
  .trades-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .filter-group {
    display: flex;
    gap: 8px;
  }

  .tb-btn {
    background: #070a12;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #94a3b8;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }

  .tb-btn.active {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  .win-btn.active {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border-color: rgba(16, 185, 129, 0.3);
  }

  .loss-btn.active {
    background: rgba(244, 63, 94, 0.15);
    color: #f43f5e;
    border-color: rgba(244, 63, 94, 0.3);
  }

  .search-box input {
    background: #070a12;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #ffffff;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 11px;
    width: 240px;
    outline: none;
  }

  .search-box input:focus {
    border-color: #f59e0b;
  }

  /* Trades Table Wrap with Sticky Header and Stable Scrollbar */
  .trades-table-wrap {
    background: #070a12;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    overflow-x: auto;
    max-height: 480px;
    overflow-y: auto;
    scrollbar-gutter: stable;
  }

  .pagination-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    padding: 10px 14px;
    background: #070a12;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    font-size: 11px;
    color: #94a3b8;
    margin-top: 4px;
  }

  .pg-info {
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
  }

  .text-white {
    color: #e2e8f0;
  }

  .pg-controls {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .pg-pages {
    display: flex;
    align-items: center;
    gap: 3px;
  }

  .pg-btn {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
    padding: 4px 9px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .pg-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.09);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.2);
  }

  .pg-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .pg-num.active {
    background: #f59e0b;
    color: #04080f;
    font-weight: 800;
    border-color: #f59e0b;
  }

  .pg-ellipsis {
    color: #64748b;
    padding: 0 4px;
    font-size: 11px;
  }

  .pg-size-selector {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .pg-size-lbl {
    color: #64748b;
    font-size: 10.5px;
  }

  .pg-size-pills {
    display: flex;
    gap: 3px;
  }

  .pg-size-btn {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #94a3b8;
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 10.5px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .pg-size-btn:hover {
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.2);
  }

  .pg-size-btn.active {
    background: rgba(245, 158, 11, 0.15);
    border-color: rgba(245, 158, 11, 0.4);
    color: #f59e0b;
    font-weight: 700;
  }

  .trades-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
  }

  .trades-table th {
    position: sticky;
    top: 0;
    z-index: 5;
    background: #090e17;
    color: #64748b;
    font-weight: 700;
    padding: 9px 12px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 10.5px;
    letter-spacing: 0.03em;
  }

  .trades-table td {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    color: #cbd5e1;
  }

  .trades-table tr:hover td {
    background: rgba(255, 255, 255, 0.02);
  }

  .date-cell {
    color: #94a3b8;
    white-space: nowrap;
  }

  .muted-cell {
    color: #64748b;
  }

  .pair-cell {
    color: #ffffff;
  }

  .side-pill {
    font-size: 9.5px;
    font-weight: 800;
    padding: 2px 6px;
    border-radius: 3px;
  }

  .side-pill.long {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
  }

  .side-pill.short {
    background: rgba(244, 63, 94, 0.15);
    color: #f43f5e;
  }

  .reason-tag {
    font-size: 10px;
    color: #64748b;
    background: rgba(255, 255, 255, 0.04);
    padding: 2px 6px;
    border-radius: 3px;
  }

  .text-slate {
    color: #64748b;
  }

  .empty-trades {
    padding: 40px;
    text-align: center;
    color: #64748b;
    font-size: 12px;
    background: #070a12;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  /* Utility Colors */
  .up { color: #10b981; }
  .down { color: #f43f5e; }
  .text-amber { color: #f59e0b; }
  .text-cyan { color: #38bdf8; }
  .r { text-align: right; }

  @media (max-width: 900px) {
    .stats-bento {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @keyframes blink {
    50% { opacity: 0.4; }
  }
</style>
