<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD, formatPercent, formatPrice, calculateForexPnl } from '../lib/formatters.js';
  import { getStrategyCategory, getRuleText } from '../lib/constants.js';
  import StrategyDetailModal from './StrategyDetailModal.svelte';

  let strategy = $derived(arena.selectedStrategy);
  let detailModalOpen = $state(false);
  let positions = $derived.by(() => {
    if (!strategy) return [];
    const all = arena.allActivePositions;
    return all.filter((p) => p.strategy === strategy.id);
  });
  let canvasRef = $state(null);

  // 24h Historical Equity Curve State
  let curveHistory = $state([]);
  let lastLoadedSid = $state(null);
  let lastLoadedMode = $state(null);
  let loadingHistory = $state(false);

  async function fetch24hCurve(sid, mode) {
    if (!sid) return;
    loadingHistory = true;
    try {
      const res = await fetch(`/api/strategy/${sid}?mode=${mode}&hours=24`);
      if (res.ok) {
        const json = await res.json();
        if (json.curve && Array.isArray(json.curve)) {
          curveHistory = json.curve;
          lastLoadedSid = sid;
          lastLoadedMode = mode;
        }
      }
    } catch (e) {
      console.error('Failed to load 24h curve for', sid, e);
    } finally {
      loadingHistory = false;
    }
  }

  // Fetch 24h data whenever strategy or mode changes
  $effect(() => {
    const sid = strategy?.id;
    const mode = arena.mode;
    if (sid && (sid !== lastLoadedSid || mode !== lastLoadedMode)) {
      curveHistory = [];
      fetch24hCurve(sid, mode);
    }
  });

  // Effective 24h curve combining history with live balance tick
  let effective24hData = $derived.by(() => {
    const strat = strategy;
    if (!strat) return [];
    const now = Date.now();
    const liveBal = strat.balance ?? strat.cash ?? strat.equity ?? 1000;

    let pts = [...curveHistory];
    if (pts.length === 0) {
      return [
        { ts: now - 3600 * 1000, equity: 1000 },
        { ts: now, equity: liveBal },
      ];
    }

    const lastPt = pts[pts.length - 1];
    if (Math.abs(now - lastPt.ts) > 4000 || Math.abs(liveBal - lastPt.equity) > 0.01) {
      pts.push({ ts: now, equity: liveBal });
    }
    return pts;
  });

  // Compute rank and total based on balance
  let allAccounts = $derived(arena.activeAccounts);
  let rank = $derived.by(() => {
    if (!strategy) return 1;
    const sorted = [...allAccounts].sort((a, b) => (b.balance ?? b.cash ?? b.equity ?? 0) - (a.balance ?? a.cash ?? a.equity ?? 0));
    const idx = sorted.findIndex((a) => a.id === strategy.id);
    return idx >= 0 ? idx + 1 : 1;
  });

  let returnPct = $derived(strategy?.returnPct ?? 0);
  let isPositive = $derived(returnPct >= 0);

  // Profit factor calculation
  let profitFactor = $derived.by(() => {
    if (!strategy) return '—';
    if (strategy.gross_loss > 0) {
      return (strategy.gross_win / strategy.gross_loss).toFixed(2);
    }
    if (strategy.gross_win > 0) return '∞';
    return '—';
  });

  // Draw Interactive 24-Hour Equity Chart on Canvas
  $effect(() => {
    if (canvasRef) {
      renderChart(canvasRef, effective24hData, strategy);
    }
  });

  // Re-render on window resize
  $effect(() => {
    if (!canvasRef) return;
    const onResize = () => {
      renderChart(canvasRef, effective24hData, strategy);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  });

  function renderChart(cv, rawPts, strat) {
    if (!cv) return;
    const ctx = cv.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth || 400;
    const h = cv.clientHeight || 190;

    cv.width = w * dpr;
    cv.height = h * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const padL = 60;
    const padR = 16;
    const padT = 20;
    const padB = 28;
    const pw = w - padL - padR;
    const ph = h - padT - padB;

    if (pw <= 0 || ph <= 0) return;

    const now = Date.now();
    const windowMs = 24 * 3600 * 1000;

    // Normalize points array
    let pts = (rawPts || [])
      .map((p) => ({
        ts: typeof p.ts === 'number' ? p.ts : now,
        equity: typeof p.equity === 'number' ? p.equity : (typeof p === 'number' ? p : 1000),
      }))
      .sort((a, b) => a.ts - b.ts);

    if (pts.length === 0) {
      const eq = strat?.equity ?? 1000;
      pts = [
        { ts: now - 3600 * 1000, equity: 1000 },
        { ts: now, equity: eq },
      ];
    }

    const latestTs = pts[pts.length - 1].ts;
    const endTs = Math.max(now, latestTs);
    const earliestDataTs = pts[0].ts;

    // Rentang waktu chart: maksimal 24 jam terakhir.
    // Jika simulasi baru berjalan < 24 jam, mulai dari waktu awal transaksi agar tidak ada garis datar kosong buatan.
    const startTs = Math.max(endTs - windowMs, earliestDataTs);
    const spanMs = Math.max(endTs - startTs, 60000);

    // Filter titik dalam jendela rentang aktif
    pts = pts.filter((p) => p.ts >= startTs);

    if (pts.length === 0) {
      const eq = strat?.equity ?? 1000;
      pts = [{ ts: startTs, equity: eq }, { ts: endTs, equity: eq }];
    }

    // Determine Y range (include $1,000 baseline with padding)
    const equities = pts.map((p) => p.equity);
    let minV = Math.min(...equities, 995);
    let maxV = Math.max(...equities, 1005);

    const vSpan = maxV - minV || 50;
    minV = minV - vSpan * 0.08;
    maxV = maxV + vSpan * 0.08;
    const range = maxV - minV;

    const X = (ts) => padL + Math.max(0, Math.min(1, (ts - startTs) / spanMs)) * pw;
    const Y = (v) => padT + ph - ((v - minV) / range) * ph;

    // Y-Axis Dollar Labels & Grid Lines
    const yTicks = 4;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.fillStyle = '#475569';

    for (let i = 0; i < yTicks; i++) {
      const val = minV + (range / (yTicks - 1)) * i;
      const y = Y(val);
      ctx.fillText('$' + Math.round(val).toLocaleString('en-US'), padL - 8, y);

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(padL, y);
      ctx.lineTo(padL + pw, y);
      ctx.stroke();
    }

    // Baseline at Modal Awal $1,000
    const y10k = Y(1000);
    if (y10k >= padT && y10k <= padT + ph) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.16)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padL, y10k);
      ctx.lineTo(padL + pw, y10k);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#64748b';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'bottom';
      ctx.font = '9.5px Inter, sans-serif';
      ctx.fillText('modal awal $1.000', padL + 6, y10k - 5);
    }

    // Top watermark / 24H timeframe badge
    const hoursElapsed = Math.round(spanMs / 3600000);
    const badgeText = spanMs >= windowMs - 60000 ? 'RENTANG 24 JAM' : `RENTANG ${hoursElapsed || 1} JAM (SEJAK AKTIF)`;
    ctx.font = '9.5px "JetBrains Mono", monospace';
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'bottom';
    ctx.fillText(badgeText, padL + pw, padT - 4);

    // X-Axis Vertical Grid Lines & Time Labels (clean HH:mm, no overlapping text)
    const xIntervals = pw < 300 ? 2 : 4;
    ctx.textBaseline = 'top';
    ctx.font = '10px "JetBrains Mono", monospace';

    for (let i = 0; i <= xIntervals; i++) {
      const ratio = i / xIntervals;
      const t = startTs + spanMs * ratio;
      const x = padL + ratio * pw;

      // Vertical subtle grid line
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, padT);
      ctx.lineTo(x, padT + ph);
      ctx.stroke();

      // Axis Tick Mark at bottom
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.18)';
      ctx.beginPath();
      ctx.moveTo(x, padT + ph);
      ctx.lineTo(x, padT + ph + 4);
      ctx.stroke();

      // Format Time HH:mm
      const dt = new Date(t);
      const hh = String(dt.getHours()).padStart(2, '0');
      const mm = String(dt.getMinutes()).padStart(2, '0');
      const timeStr = `${hh}:${mm}`;

      if (i === 0) {
        ctx.textAlign = 'left';
      } else if (i === xIntervals) {
        ctx.textAlign = 'right';
      } else {
        ctx.textAlign = 'center';
      }

      ctx.fillStyle = '#64748b';
      ctx.fillText(timeStr, x, padT + ph + 7);
    }

    // Curve Line
    const latestEq = pts[pts.length - 1].equity;
    const isUp = latestEq >= 1000;
    const lineColor = isUp ? '#10b981' : '#f43f5e';
    const areaGrad = ctx.createLinearGradient(0, padT, 0, padT + ph);
    areaGrad.addColorStop(0, isUp ? 'rgba(16, 185, 129, 0.22)' : 'rgba(244, 63, 94, 0.22)');
    areaGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.beginPath();
    pts.forEach((p, i) => {
      const x = X(p.ts);
      const y = Y(p.equity);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
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
    ctx.arc(lastX, lastY, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.shadowColor = lineColor;
    ctx.shadowBlur = 8;
    ctx.fill();
    ctx.shadowBlur = 0;
  }
</script>

{#if strategy}
  <section class="panel detail" id="dossier">
    <!-- Dossier Header -->
    <div class="dos-head">
      <div class="dos-left">
        <div class="dos-title">
          <h2>{strategy.name}</h2>
          <span class="chip mono">#{rank}/{allAccounts.length}</span>
          <span class="chip badge-category">
            {#if arena.mode === 'forex' || strategy.mode === 'forex'}
              {(strategy.family || getStrategyCategory(strategy.id)).toUpperCase()} · MT5 DIRECT
            {:else if arena.mode === 'futures'}
              {(strategy.family || getStrategyCategory(strategy.id)).toUpperCase()} · {strategy.leverage || 1}x
            {:else}
              {(strategy.family || getStrategyCategory(strategy.id)).toUpperCase()}
            {/if}
          </span>
          {#if strategy.refillCount > 0}
            <span class="chip-mc">MC {strategy.refillCount}x</span>
          {/if}
        </div>
        <p class="rule">{getRuleText(strategy)}</p>
      </div>

      <div class="dos-actions">
        <div class="dos-eq">
          <b class="mono {isPositive ? 'up' : 'down'}">{formatUSD(strategy.balance ?? strategy.cash ?? strategy.equity)}</b>
          <span>BALANCE BERSIH · {positions.length > 0 ? `${positions.length} POSISI TERBUKA` : '0 POSISI TERBUKA'}</span>
        </div>
      </div>
    </div>

    <!-- Dossier Body: Chart + 6 KPIs -->
    <div class="dos-body">
      <div class="chartwrap">
        <canvas bind:this={canvasRef} id="eqChart"></canvas>
      </div>

      <div class="kpis">
        <div class="kpi-box">
          <span>RETURN</span>
          <b class="mono {isPositive ? 'up' : 'down'}">{formatPercent(strategy.returnPct)}</b>
        </div>
        <div class="kpi-box">
          <span>WIN RATE</span>
          <b class="mono">
            {strategy.trades > 0 ? `${((strategy.wins / strategy.trades) * 100).toFixed(1)}%` : '—'}
          </b>
        </div>
        <div class="kpi-box">
          <span>MAX DD</span>
          <b class="mono">{((strategy.max_dd || 0) * 100).toFixed(2)}%</b>
        </div>
        <div class="kpi-box">
          <span>TRADE</span>
          <b class="mono">{strategy.trades || 0}</b>
        </div>
        <div class="kpi-box">
          <span>PROFIT FACTOR</span>
          <b class="mono">{profitFactor}</b>
        </div>
        <div class="kpi-box">
          <span>TERBUKA</span>
          <b class="mono">{positions.length}</b>
        </div>
      </div>
    </div>
   <button class="btn-open-detail mono" onclick={() => (detailModalOpen = true)}>
          <svg class="btn-icon-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
          <span>ANALISIS & HISTORI TRADE LENGKAP</span>
        </button>
    <!-- Active Positions Table for this Selected Strategy -->
    <div class="pos-list">
      <div class="pos-list-bar">
        <div class="pos-list-title">
          <span>POSISI AKTIF STRATEGI</span>
          <span class="count-pill">{positions.length} pair</span>
        </div>
      </div>

      {#if positions.length === 0}
        <div class="empty-state">
          <svg class="empty-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
          </svg>
          <span>Strategi ini sedang menunggu sinyal entry berikutnya (flat).</span>
        </div>
      {:else}
        <div class="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Pair</th>
                <th>Arah</th>
                <th>{arena.mode === 'forex' ? 'Lot' : 'Lev'}</th>
                <th class="r">Entry</th>
                <th class="r">Mark</th>
                <th class="r">uPnL</th>
                <th class="r">Risiko / Margin</th>
                <th class="r">Stop</th>
                <th class="r">Target</th>
              </tr>
            </thead>
            <tbody>
              {#each positions as p (p.strategy + '_' + p.symbol)}
                {@const currentMark = arena.prices[p.symbol] ?? p.mark ?? p.entry}
                {@const sideSign = (p.side === 'LONG' || p.side === 1) ? 1 : -1}
                {@const isPosForex = arena.mode === 'forex' || p.mode === 'forex' || p.lot != null}
                {@const liveUpnl = isPosForex
                  ? calculateForexPnl(p.symbol, p.entry, currentMark, p.side, p.lot || 0.10, arena.prices)
                  : (p.qty > 0 && currentMark > 0 ? (currentMark - p.entry) * p.qty * sideSign : (p.upnl ?? 0))}
                {@const isUp = liveUpnl >= 0}
                <tr>
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
                  <td class="r mono">{formatPrice(currentMark)}</td>
                  <td class="r mono font-bold {isUp ? 'up' : 'down'}">
                    {formatUSD(liveUpnl)}
                  </td>
                  <td class="r mono muted">{formatUSD(p.margin)}</td>
                  <td class="r mono muted">{p.stop ? formatPrice(p.stop) : '—'}</td>
                  <td class="r mono muted">{p.target ? formatPrice(p.target) : '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </section>

  <StrategyDetailModal
    bind:isOpen={detailModalOpen}
    {strategy}
    {rank}
    totalStrategies={allAccounts.length}
    openPositionsCount={positions.length}
  />
{/if}

<style>
  .detail {
    background: #090d14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    height: 100%;
    min-height: 0;
  }

  .dos-head {
    display: flex;
    gap: 14px;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-wrap: wrap;
    align-items: flex-start;
  }

  .dos-left {
    flex: 1;
    min-width: 260px;
  }

  .dos-title {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .dos-title h2 {
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.02em;
  }

  .chip {
    font-size: 10.5px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 4px;
    background: #151c29;
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.07);
  }

  .badge-category {
    background: rgba(245, 158, 11, 0.12);
    color: #f59e0b;
    border-color: rgba(245, 158, 11, 0.3);
  }

  .chip-mc {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(244, 63, 94, 0.2);
    color: #f43f5e;
    border: 1px solid rgba(244, 63, 94, 0.4);
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

  .rule {
    margin: 6px 0 0;
    font-size: 11.8px;
    color: #94a3b8;
    line-height: 1.5;
    max-width: 68ch;
  }

  .dos-actions {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }

  .dos-eq {
    text-align: right;
  }

  .btn-open-detail {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #f59e0b;
    padding: 7px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
  }

  .btn-open-detail:hover {
    background: #f59e0b;
    color: #080c14;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(245, 158, 11, 0.25);
  }

  .dos-eq b {
    display: block;
    font-size: 21px;
    font-weight: 700;
    letter-spacing: -0.03em;
  }

  .dos-eq span {
    font-size: 10.5px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
  }

  .dos-body {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    gap: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .chartwrap {
    padding: 10px 8px 6px;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    min-width: 0;
  }

  #eqChart {
    display: block;
    width: 100%;
    height: 190px;
  }

  .kpis {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    padding: 14px;
    align-content: center;
  }

  .kpi-box span {
    display: block;
    font-size: 9.5px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    font-weight: 700;
  }

  .kpi-box b {
    display: block;
    font-size: 14.5px;
    margin-top: 3px;
    font-weight: 700;
    color: #f1f5f9;
  }

  .pos-list {
    display: flex;
    flex-direction: column;
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
  }

  .pos-list-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    background: #06090e;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    flex-shrink: 0;
  }

  .pos-list-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #94a3b8;
    text-transform: uppercase;
  }

  .count-pill {
    font-size: 10px;
    color: #64748b;
    background: #111722;
    padding: 1px 6px;
    border-radius: 3px;
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
    padding: 6px 12px;
    font-weight: 700;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    z-index: 2;
  }

  td {
    padding: 6px 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    white-space: nowrap;
    color: #e2e8f0;
  }

  tr:hover td {
    background: rgba(255, 255, 255, 0.03);
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
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 30px;
    color: #64748b;
    font-size: 12px;
  }

  .empty-svg {
    color: #64748b;
    opacity: 0.8;
  }

  @media (max-width: 900px) {
    .dos-body {
      grid-template-columns: minmax(0, 1fr);
    }
    .chartwrap {
      border-right: 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
  }
</style>
