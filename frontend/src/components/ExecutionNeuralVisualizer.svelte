<script>
  import { onMount, onDestroy } from 'svelte';
  import { arena } from '../lib/store.svelte.js';
  import { STRATEGIES_88, FALLBACK_PAIRS_128 } from '../lib/strategies_data.js';

  let { activeTrade = null, onSelectPair = null, onClearTrade = null, onNewTrade = null } = $props();

  // Filter & Search State
  let pairCategory = $state('all'); // 'all', 'crypto', 'forex'
  let pairSearch = $state('');
  let selectedSymbol = $state(null);
  let selectedStrategyId = $state(null);

  // Active Symbol resolution: from active trade prop or manual selection
  let activeSymbol = $derived.by(() => {
    if (activeTrade && activeTrade.symbol) return activeTrade.symbol;
    return selectedSymbol;
  });

  // Geometry Setup for the 128 Input Nodes (4 columns - Spaced & Enlarged)
  // Col 0: Crypto #1 (32 nodes, x = 95)
  // Col 1: Crypto #2 (32 nodes, x = 195)
  // Col 2: Crypto #3 (36 nodes, x = 295)
  // Col 3: MT5 Forex & Metals (28 nodes, x = 395)
  const inputColX = [95, 195, 295, 395];
  const colYStart = 115;
  const colYEnd = 1235;
  const colYHeight = colYEnd - colYStart;

  // Split pairs into the 4 columns
  let inputCols = $derived.by(() => {
    let list = (arena.pairs && arena.pairs.length >= 100) ? arena.pairs : FALLBACK_PAIRS_128;
    const crypto = list.filter(p => p.category === 'crypto' || (!p.symbol.startsWith('XAU') && !p.symbol.startsWith('XAG') && !p.symbol.startsWith('XTI') && p.symbol.endsWith('USDT')));
    const forex = list.filter(p => p.category === 'forex' || (p.symbol.length === 6 && !p.symbol.endsWith('USDT') && !p.symbol.endsWith('USDC')) || p.symbol === 'XAUUSD' || p.symbol === 'XAGUSD' || p.symbol === 'XTIUSD');

    const cSlice = crypto.length >= 100 ? crypto : FALLBACK_PAIRS_128.filter(p => p.category === 'crypto');
    const fSlice = forex.length >= 28 ? forex : FALLBACK_PAIRS_128.filter(p => p.category === 'forex');

    return [
      cSlice.slice(0, 32),
      cSlice.slice(32, 64),
      cSlice.slice(64, 100),
      fSlice.slice(0, 28)
    ];
  });

  // Complete list of all 128 nodes with exact coordinates and metadata
  let all128Nodes = $derived.by(() => {
    const cols = inputCols;
    const nodes = [];
    const q = pairSearch.toUpperCase().trim();

    cols.forEach((colPairs, colIdx) => {
      const count = colPairs.length;
      const x = inputColX[colIdx];
      const isForexCol = (colIdx === 3);

      colPairs.forEach((p, rowIdx) => {
        const y = colYStart + (rowIdx / Math.max(count - 1, 1)) * colYHeight;
        const sym = p.symbol || '';
        const base = p.base || sym.replace('USDT', '').replace('USD', '') || sym;
        const isMatched = activeSymbol ? (activeSymbol === sym) : false;
        const isSearchHit = q ? (sym.includes(q) || base.includes(q)) : false;

        let isDimmed = false;
        if (pairCategory === 'crypto' && isForexCol) isDimmed = true;
        if (pairCategory === 'forex' && !isForexCol) isDimmed = true;
        if (q && !isSearchHit) isDimmed = true;

        nodes.push({
          id: `in_${colIdx}_${rowIdx}`,
          symbol: sym,
          base: base.slice(0, 5),
          name: p.name || sym,
          category: isForexCol ? 'forex' : 'crypto',
          x,
          y,
          col: colIdx,
          row: rowIdx,
          r: isForexCol ? 16.5 : (colIdx === 2 ? 13.8 : 15.0),
          isActive: isMatched,
          isSearchHit,
          isDimmed,
          price: arena.prices[sym]?.price ?? arena.prices[sym] ?? null
        });
      });
    });

    return nodes;
  });

  // Active Input Node
  let activeInputNode = $derived.by(() => {
    if (!activeSymbol) return null;
    return all128Nodes.find(n => n.symbol === activeSymbol) || null;
  });

  // -------------------------------------------------------------
  // Layer 2: All 88 Universal Quantitative Strategies in Native Circles
  // Digunakan untuk SEMUA PASAR (Spot, Futures, Forex)!
  // 3 Kolom seimbang & diperlebar: x = [660, 840, 1020]
  // -------------------------------------------------------------
  const stratColX = [660, 840, 1020];

  let all88StrategyNodes = $derived.by(() => {
    const all = STRATEGIES_88; // 88 strategi universal
    const cols = [
      all.slice(0, 30),  // 30
      all.slice(30, 59), // 29
      all.slice(59, 88), // 29
    ];

    const nodes = [];

    cols.forEach((colStrats, colIdx) => {
      const count = colStrats.length;
      const x = stratColX[colIdx];

      colStrats.forEach((s, rowIdx) => {
        const y = colYStart + (rowIdx / Math.max(count - 1, 1)) * colYHeight;
        nodes.push({
          id: `strat_${colIdx}_${rowIdx}`,
          stratId: s.id,
          name: s.name,
          family: s.family,
          code: s.code,
          is_forex: s.is_forex,
          x,
          y,
          r: colIdx === 0 ? 16.5 : 17.0,
          col: colIdx,
          row: rowIdx,
        });
      });
    });

    return nodes;
  });

  // -------------------------------------------------------------
  // Layer 3: Execution Engines · Tri-Market Output (5 nodes, x = 1380)
  // -------------------------------------------------------------
  const outputNodes = [
    { id: 'out_fut_l',  label: 'FUT·L',  sub: 'FUTURES',   tag: '20x LEV',    x: 1380, y: 175,  R: 46, type: 'output-long',  isCryptoOnly: true, desc: 'Binance Futures Long Position (1-20x)' },
    { id: 'out_fx_buy', label: 'FX·BUY', sub: 'MT5 DIRECT', tag: 'LOT SIZING', x: 1380, y: 440,  R: 46, type: 'output-forex', isForexOnly: true,  desc: 'MetaTrader 5 Direct Buy Order' },
    { id: 'out_spot',   label: 'SPOT',   sub: 'CRYPTO',    tag: '1x SPOT',    x: 1380, y: 705,  R: 46, type: 'output-spot',  isCryptoOnly: true, desc: 'Binance Spot Execution (Tanpa Leverage)' },
    { id: 'out_fx_sel', label: 'FX·SEL', sub: 'MT5 DIRECT', tag: 'LOT SIZING', x: 1380, y: 970,  R: 46, type: 'output-forex', isForexOnly: true,  desc: 'MetaTrader 5 Direct Sell Order' },
    { id: 'out_fut_s',  label: 'FUT·S',  sub: 'FUTURES',   tag: '20x LEV',    x: 1380, y: 1225, R: 46, type: 'output-short', isCryptoOnly: true, desc: 'Binance Futures Short Position (1-20x)' },
  ];

  // -------------------------------------------------------------
  // Background Synapses
  // -------------------------------------------------------------
  const backgroundSynapses = $derived.by(() => {
    const list = [];

    // 1. Input -> Strategy: each pair connects to 2 closest strategies
    all128Nodes.forEach(p => {
      const sorted = [...all88StrategyNodes].sort((a, b) => Math.abs(a.y - p.y) - Math.abs(b.y - p.y));
      sorted.slice(0, 2).forEach(s => {
        list.push({
          id: `${p.id}->${s.id}`,
          x1: p.x, y1: p.y, x2: s.x, y2: s.y,
          color: p.category === 'forex' ? '#10b981' : '#06b6d4',
          opacity: 0.08
        });
      });
    });

    // 2. Strategy -> Output: each strategy connects to 2 closest output engines
    all88StrategyNodes.forEach(s => {
      const sorted = [...outputNodes].sort((a, b) => Math.abs(a.y - s.y) - Math.abs(b.y - s.y));
      sorted.slice(0, 2).forEach(o => {
        list.push({
          id: `${s.id}->${o.id}`,
          x1: s.x, y1: s.y, x2: o.x, y2: o.y,
          color: o.isForexOnly ? '#10b981' : (o.type === 'output-spot' ? '#f59e0b' : '#38bdf8'),
          opacity: 0.10
        });
      });
    });

    return list;
  });

  // -------------------------------------------------------------
  // ROUTE LOGIC 1: Exact Audit Route (when clicked from Audit Table)
  // Direct Pair -> Strategy -> Execution Engine
  // -------------------------------------------------------------
  let activeAuditRoute = $derived.by(() => {
    if (!activeTrade) return null;
    const sym = (activeTrade.symbol || '').toUpperCase();
    const strat = (activeTrade.strategy || activeTrade.strategy_name || '').toLowerCase();
    const mode = (activeTrade.mode || (sym.endsWith('USDT') ? 'spot' : 'forex')).toLowerCase();
    const side = activeTrade.side ?? (activeTrade.side_label === 'SHORT' ? -1 : 1);

    // 1. Exact Input Pair Node
    let pNode = all128Nodes.find(n => n.symbol === sym);
    if (!pNode) pNode = all128Nodes.find(n => sym.includes(n.base)) || all128Nodes[0];

    // 2. Exact Strategy Node from 88 strategies
    let sNode = all88StrategyNodes.find(s => s.stratId.toLowerCase() === strat || s.name.toLowerCase() === strat);
    if (!sNode) {
      sNode = all88StrategyNodes.find(s => strat.includes(s.stratId.toLowerCase()) || s.stratId.toLowerCase().includes(strat));
    }
    if (!sNode) {
      sNode = all88StrategyNodes[0];
    }

    // 3. Exact Output Engine (Forex Long -> FX BUY, Forex Short -> FX SEL)
    let oNode;
    if (mode === 'forex') {
      oNode = (side === 1 || activeTrade.side_label === 'LONG')
        ? outputNodes.find(o => o.id === 'out_fx_buy')
        : outputNodes.find(o => o.id === 'out_fx_sel');
    } else if (mode === 'futures') {
      oNode = (side === 1 || activeTrade.side_label === 'LONG')
        ? outputNodes.find(o => o.id === 'out_fut_l')
        : outputNodes.find(o => o.id === 'out_fut_s');
    } else {
      oNode = outputNodes.find(o => o.id === 'out_spot');
    }

    // 2 direct continuous segments
    const segments = [
      { id: `${pNode.id}->${sNode.id}`, x1: pNode.x, y1: pNode.y, x2: sNode.x, y2: sNode.y },
      { id: `${sNode.id}->${oNode.id}`, x1: sNode.x, y1: sNode.y, x2: oNode.x, y2: oNode.y },
    ];

    const activeNodeIds = [pNode.id, sNode.id, oNode.id];

    return {
      pNode, sNode, oNode,
      segments,
      activeNodeIds,
      trade: activeTrade
    };
  });

  // -------------------------------------------------------------
  // ROUTE LOGIC 2: Direct Pair Click (Multi-Path Active Tree)
  // Direct Pair -> ALL 88 Strategies -> Output Engines
  // Sesuai arsitektur kuantitatif universal: Semua 88 strategi
  // dapat mengeksekusi pair ini dan menyala bersamaan!
  // -------------------------------------------------------------
  let activePairRoutes = $derived.by(() => {
    if (activeTrade) return null; // Prioritize audit trade if provided
    if (!selectedSymbol) return null;

    const pNode = all128Nodes.find(n => n.symbol === selectedSymbol);
    if (!pNode) return null;

    const isForex = (pNode.category === 'forex');

    // Seluruh 88 strategi kuantitatif universal terhubung ke pair ini!
    const selectedStrats = all88StrategyNodes;

    // Active Output Engine nodes:
    // Forex -> FX·BUY & FX·SEL
    // Crypto -> SPOT, FUT·L, FUT·S
    const activeOutputIds = isForex
      ? ['out_fx_buy', 'out_fx_sel']
      : ['out_spot', 'out_fut_l', 'out_fut_s'];

    const fanLines = [];
    const activeOutputs = outputNodes.filter(o => activeOutputIds.includes(o.id));

    // 1. Jalur dari Pair ke Seluruh 88 Strategi
    selectedStrats.forEach((s) => {
      fanLines.push({
        x1: pNode.x,
        y1: pNode.y,
        x2: s.x,
        y2: s.y,
        color: isForex ? '#10b981' : '#38bdf8',
        width: 1.8,
        opacity: 0.55,
        id: `${pNode.id}->${s.id}`
      });
    });

    // 2. Jalur dari Seluruh 88 Strategi ke Output Engines
    selectedStrats.forEach((s, sIdx) => {
      const targetOut = activeOutputs[sIdx % activeOutputs.length];
      if (targetOut) {
        fanLines.push({
          x1: s.x,
          y1: s.y,
          x2: targetOut.x,
          y2: targetOut.y,
          color: targetOut.isForexOnly ? '#10b981' : (targetOut.type === 'output-spot' ? '#f59e0b' : '#38bdf8'),
          width: 2.2,
          opacity: 0.65,
          id: `${s.id}->${targetOut.id}`
        });
      }
    });

    // SELURUH 88 STRATEGI AKTIF MENYALA!
    const activeStratIds = selectedStrats.map(s => s.id);
    const activeNodeIds = [
      pNode.id,
      ...activeStratIds,
      ...activeOutputIds
    ];

    return {
      pNode,
      isForex,
      fanLines,
      activeNodeIds,
      activeOutputIds
    };
  });

  // -------------------------------------------------------------
  // ROUTE LOGIC 3: Direct Strategy Click (Multi-Market Fan Tree)
  // ALL 128 Input Pairs -> Selected Strategy -> Execution Engines
  // Sesuai arsitektur universal: Seluruh 128 pair mengalir ke strategi ini
  // dan seluruh 128 pair menyala bersamaan!
  // -------------------------------------------------------------
  let activeStrategyRoutes = $derived.by(() => {
    if (activeTrade) return null;
    if (selectedSymbol) return null;
    if (!selectedStrategyId) return null;

    const sNode = all88StrategyNodes.find(s => s.stratId === selectedStrategyId || s.id === selectedStrategyId);
    if (!sNode) return null;

    // Seluruh 128 pair multi-asset (100 Crypto + 28 Forex) mengalir ke strategi ini!
    const inputPairs = all128Nodes;

    // Target output: strategi universal menghubungkan ke seluruh pasar (Crypto & Forex)
    const targetOutputs = outputNodes;

    // 1. Seluruh 128 Pair -> Strategi
    const inputLines = inputPairs.map(p => ({
      id: `${p.id}->${sNode.id}`,
      x1: p.x,
      y1: p.y,
      x2: sNode.x,
      y2: sNode.y,
      color: p.category === 'forex' ? '#10b981' : '#38bdf8',
      width: 1.8,
      opacity: 0.55
    }));

    // 2. Strategi -> Seluruh 5 Execution Engines
    const outputLines = targetOutputs.map(o => ({
      id: `${sNode.id}->${o.id}`,
      x1: sNode.x,
      y1: sNode.y,
      x2: o.x,
      y2: o.y,
      color: o.isForexOnly ? '#10b981' : (o.type === 'output-spot' ? '#f59e0b' : '#38bdf8'),
      width: 3.5,
      opacity: 0.95
    }));

    // SELURUH 128 PAIR AKTIF MENYALA!
    const activeInputIds = inputPairs.map(p => p.id);
    const activeOutputIds = targetOutputs.map(o => o.id);
    const activeNodeIds = [
      sNode.id,
      ...activeInputIds,
      ...activeOutputIds
    ];

    return {
      sNode,
      inputLines,
      outputLines,
      activeNodeIds,
      activeOutputIds,
      activeInputIds
    };
  });

  // -------------------------------------------------------------
  // REAL-TIME NEW TRADE OPENING ENGINE
  // Animasi HANYA AKTIF saat ada trade baru yang terbuka!
  // Menampilkan: PAIR APA · STRATEGY APA · POSISINYA APA
  // Di-render via Hardware-Accelerated 2D Canvas (Zero-Lag, 60-120 FPS)
  // -------------------------------------------------------------
  // Canvas state
  let canvasElem = $state(null);
  let activePulses = []; // Non-reactive plain JS array (menghindari reactive thrashing)
  let auditLaserProgress = 0;
  let animFrameId = null;

  // Active newly opened trade
  let activeNewTradeEvent = $state(null);
  let activeNewTradeTimer = null;
  let recentOpenedTrades = $state([]);

  // State keys for deduplication
  let knownPositionKeys = new Set();
  let knownEventKeys = new Set();
  let isDetectionReady = false;

  function fireTradeRoutePulses(trade) {
    if (!trade || !trade.symbol) return;
    if (!all128Nodes.length || !all88StrategyNodes.length) return;

    const sym = (trade.symbol || '').toUpperCase();
    const strat = (trade.strategy || trade.strategy_name || '').toLowerCase();
    const mode = (trade.mode || (sym.endsWith('USDT') ? 'spot' : 'forex')).toLowerCase();
    const isLong = (trade.side === 1 || trade.side_label === 'LONG' || (trade.message && trade.message.includes('LONG')));

    let inNode = all128Nodes.find(n => n.symbol === sym) || all128Nodes.find(n => sym.includes(n.base)) || all128Nodes[0];
    let sNode = all88StrategyNodes.find(s => s.stratId.toLowerCase() === strat || s.name.toLowerCase() === strat);
    if (!sNode) sNode = all88StrategyNodes.find(s => strat.includes(s.stratId.toLowerCase()) || s.stratId.toLowerCase().includes(strat));
    if (!sNode) sNode = all88StrategyNodes[0];

    let oNode;
    if (mode === 'forex') {
      oNode = isLong ? outputNodes.find(o => o.id === 'out_fx_buy') : outputNodes.find(o => o.id === 'out_fx_sel');
    } else if (mode === 'futures') {
      oNode = isLong ? outputNodes.find(o => o.id === 'out_fut_l') : outputNodes.find(o => o.id === 'out_fut_s');
    } else {
      oNode = outputNodes.find(o => o.id === 'out_spot');
    }

    const routeNodes = [inNode, sNode, oNode];
    const color = isLong ? '#10b981' : '#f43f5e'; // Emerald untuk LONG/BUY, Rose untuk SHORT/SELL

    // Tepat 1 butir dot pulse per 1 trade entry yang terbuka
    const pulse = {
      id: Date.now() + Math.random(),
      nodes: routeNodes,
      color,
      isLong,
      step: 0,
      t: 0
    };
    activePulses.push(pulse);
    if (activePulses.length > 10) {
      activePulses = activePulses.slice(-10);
    }
  }

  function handleNewTradeOpened(trade, shouldFire = true) {
    if (!trade || !trade.symbol) return;

    // Cari info lengkap strategi dari katalog 88
    const rawStrat = (trade.strategy || trade.strategy_name || '').toLowerCase();
    const stratObj = STRATEGIES_88.find(s => s.id.toLowerCase() === rawStrat || s.name.toLowerCase() === rawStrat) || {
      id: trade.strategy || 'quant',
      name: trade.strategy_name || trade.strategy || 'Quantitative Strategy',
      code: (trade.strategy || 'QUANT').slice(0, 4).toUpperCase(),
      family: 'Quantitative'
    };

    const isLong = (trade.side === 1 || trade.side_label === 'LONG' || (trade.message && trade.message.includes('LONG')));
    const sideLabel = isLong ? 'LONG' : 'SHORT';

    const enriched = {
      ...trade,
      strategy_name: stratObj.name,
      strategy_code: stratObj.code,
      strategy_family: stratObj.family,
      side_label: sideLabel,
      isLong,
      openedAt: trade.opened_at || Date.now()
    };

    activeNewTradeEvent = enriched;

    // Update antrean trade terbaru
    const filtered = recentOpenedTrades.filter(t => !(t.symbol === enriched.symbol && t.strategy === enriched.strategy && t.mode === enriched.mode));
    recentOpenedTrades = [enriched, ...filtered.slice(0, 7)];

    if (shouldFire) {
      fireTradeRoutePulses(enriched);
      if (onNewTrade) onNewTrade(enriched);
    }

    if (activeNewTradeTimer) clearTimeout(activeNewTradeTimer);
    activeNewTradeTimer = setTimeout(() => {
      // route tetap aktif sebagai penanda trade terakhir
    }, 10000);
  }

  // Monitor live positions & events dari ketiga engine (Spot, Futures, Forex)
  $effect(() => {
    const currentPositions = [
      ...(arena.spot?.positions || []).map(p => ({ ...p, mode: 'spot' })),
      ...(arena.futures?.positions || []).map(p => ({ ...p, mode: 'futures' })),
      ...(arena.forex?.positions || []).map(p => ({ ...p, mode: 'forex' }))
    ];

    const currentEvents = [
      ...(arena.spot?.events || []).map(e => ({ ...e, mode: 'spot' })),
      ...(arena.futures?.events || []).map(e => ({ ...e, mode: 'futures' })),
      ...(arena.forex?.events || []).map(e => ({ ...e, mode: 'forex' }))
    ];

    if (!isDetectionReady) {
      if (currentPositions.length > 0 || currentEvents.length > 0) {
        currentPositions.forEach(p => {
          knownPositionKeys.add(`${p.mode}_${p.strategy}_${p.symbol}_${p.opened_at}`);
        });
        currentEvents.forEach(e => {
          knownEventKeys.add(`${e.mode}_${e.symbol}_${e.ts}_${e.kind}`);
        });
        isDetectionReady = true;

        // Tampilkan trade terbuka terbaru secara pasif di awal (tanpa alarm)
        if (currentPositions.length > 0) {
          const sorted = [...currentPositions].sort((a, b) => (b.opened_at || 0) - (a.opened_at || 0));
          if (sorted[0]) {
            handleNewTradeOpened(sorted[0], false);
          }
        }
      }
      return;
    }

    // Deteksi Trade Baru Terbuka dari Event Realtime 'entry'
    for (const e of currentEvents) {
      if (e.kind === 'entry') {
        const key = `${e.mode}_${e.symbol}_${e.ts}`;
        if (!knownEventKeys.has(key)) {
          knownEventKeys.add(key);
          const strat = (e.strats && e.strats[0]) || '';
          const isShort = (e.message || '').includes('SHORT') || (e.message || '').includes('SELL');
          handleNewTradeOpened({
            mode: e.mode,
            symbol: e.symbol,
            strategy: strat,
            side: isShort ? -1 : 1,
            opened_at: e.ts,
            message: e.message
          }, true);
          break;
        }
      }
    }

    // Deteksi Trade Baru Terbuka dari Posisi Aktif (hanya jika belum tercatat di event)
    for (const p of currentPositions) {
      const key = `${p.mode}_${p.strategy}_${p.symbol}_${p.opened_at}`;
      if (!knownPositionKeys.has(key)) {
        knownPositionKeys.add(key);
        const eventKey = `${p.mode}_${p.symbol}_${p.opened_at}`;
        if (!knownEventKeys.has(eventKey)) {
          knownEventKeys.add(eventKey);
          handleNewTradeOpened(p, true);
          break;
        }
      }
    }
  });

  // Tembak animasi otomatis jika user klik baris trade di Tabel Audit Riwayat
  $effect(() => {
    if (activeTrade) {
      fireTradeRoutePulses(activeTrade);
    }
  });

  onMount(() => {
    // 60-120 FPS Loop berjalan via Hardware-Accelerated 2D Canvas Context
    // 0ms lag, zero Svelte DOM reactivity overhead!
    function renderFrame() {
      animFrameId = requestAnimationFrame(renderFrame);

      if (!canvasElem) return;
      const ctx = canvasElem.getContext('2d');
      if (!ctx) return;

      const hasAudit = Boolean(activeAuditRoute && activeAuditRoute.segments.length > 0);
      const hasPulses = activePulses.length > 0;

      // Ketika Pair atau Strategi diklik: HANYA garis dan lingkaran terhubung yang menyala!
      // Dot pulse HANYA aktif saat ada event trade baru terbuka / audit aktif
      if (!hasAudit && !hasPulses) {
        ctx.clearRect(0, 0, 1560, 1280);
        return;
      }

      ctx.clearRect(0, 0, 1560, 1280);

      // 1. Audit Route Laser Pulse (gold traveling particle)
      if (hasAudit) {
        auditLaserProgress = (auditLaserProgress + 0.016) % 1;
        const segs = activeAuditRoute.segments;
        const totalSegs = segs.length;
        const scaled = auditLaserProgress * totalSegs;
        const segIdx = Math.min(totalSegs - 1, Math.floor(scaled));
        const t = scaled - segIdx;
        const seg = segs[segIdx];
        if (seg) {
          const ax = seg.x1 + (seg.x2 - seg.x1) * t;
          const ay = seg.y1 + (seg.y2 - seg.y1) * t;

          ctx.save();
          // Outer soft gold aura
          ctx.fillStyle = '#fbbf24';
          ctx.globalAlpha = 0.28;
          ctx.beginPath();
          ctx.arc(ax, ay, 14, 0, Math.PI * 2);
          ctx.fill();

          // Core bright gold particle
          ctx.globalAlpha = 1.0;
          ctx.fillStyle = '#ffffff';
          ctx.strokeStyle = '#fbbf24';
          ctx.lineWidth = 2.8;
          ctx.beginPath();
          ctx.arc(ax, ay, 6.0, 0, Math.PI * 2);
          ctx.fill();
          ctx.stroke();
          ctx.restore();
        }
      }

      // 2. Real-Time Trade Pulses (Zero-Lag 120 FPS high performance loop)
      if (hasPulses) {
        for (let i = 0; i < activePulses.length; i++) {
          const p = activePulses[i];
          p.t += 0.022;
          if (p.t >= 1) {
            p.t = 0;
            p.step += 1;
          }

          if (p.step < 2) {
            const nFrom = p.nodes[p.step];
            const nTo = p.nodes[p.step + 1];
            if (nFrom && nTo) {
              const px = nFrom.x + (nTo.x - nFrom.x) * p.t;
              const py = nFrom.y + (nTo.y - nFrom.y) * p.t;

              ctx.save();
              // Outer atmospheric aura
              ctx.fillStyle = p.color;
              ctx.globalAlpha = 0.25;
              ctx.beginPath();
              ctx.arc(px, py, 14, 0, Math.PI * 2);
              ctx.fill();

              // Intermediate vibrant halo
              ctx.globalAlpha = 0.85;
              ctx.beginPath();
              ctx.arc(px, py, 7.0, 0, Math.PI * 2);
              ctx.fill();

              // White-hot core
              ctx.globalAlpha = 1.0;
              ctx.fillStyle = '#ffffff';
              ctx.beginPath();
              ctx.arc(px, py, 3.2, 0, Math.PI * 2);
              ctx.fill();
              ctx.restore();
            }
          }
        }

        activePulses = activePulses.filter(p => p.step < 2);
      }
    }

    renderFrame();

    return () => {
      if (activeNewTradeTimer) clearTimeout(activeNewTradeTimer);
      if (animFrameId) cancelAnimationFrame(animFrameId);
    };
  });

  // Hovered Node Inspection for HUD
  let hoveredNode = $state(null);

  function handlePairSelect(sym) {
    if (selectedSymbol === sym) {
      selectedSymbol = null;
    } else {
      selectedSymbol = sym;
      selectedStrategyId = null;
    }
    if (onClearTrade) onClearTrade();
    if (onSelectPair) onSelectPair(selectedSymbol);
  }

  function getStratColor(family) {
    return '#ffffff';
  }

  function handleStrategyClick(s) {
    const id = s.stratId || s.id;
    if (selectedStrategyId === id) {
      selectedStrategyId = null;
    } else {
      selectedStrategyId = id;
      selectedSymbol = null;
      if (onClearTrade) onClearTrade();
    }
    hoveredNode = s;
  }
</script>

<div class="execution-nn-box">
  <!-- Top Control Bar -->
  <div class="nn-top-controls mono">
    <div class="controls-left">
      <span class="live-pulse"></span>
      <span class="title-bold">MULTI-ASSET NEURAL NETWORK</span>
    </div>

    <div class="controls-right">
      <!-- Filter highlight buttons -->
      <div class="category-tabs">
        <button
          type="button"
          class="cat-btn {pairCategory === 'all' ? 'active' : ''}"
          onclick={() => pairCategory = 'all'}
        >
          Semua
        </button>
        <button
          type="button"
          class="cat-btn {pairCategory === 'crypto' ? 'active text-cyan' : ''}"
          onclick={() => pairCategory = 'crypto'}
        >
          Crypto
        </button>
        <button
          type="button"
          class="cat-btn {pairCategory === 'forex' ? 'active text-emerald' : ''}"
          onclick={() => pairCategory = 'forex'}
        >
          Forex & Metals
        </button>
      </div>

      <!-- Quick Search to highlight node -->
      <div class="search-pair-box">
        <input
          type="text"
          placeholder="Cari & Sorot Pair (XAU, EUR, BTC, SOXLB)..."
          bind:value={pairSearch}
          class="pair-search-input mono"
        />
        {#if pairSearch}
          <button type="button" class="btn-clear-search" onclick={() => pairSearch = ''}>✕</button>
        {/if}
      </div>
    </div>
  </div>

  <!-- Main Responsive Stage: SVG Base + Hardware-Accelerated Canvas Overlay -->
  <div class="svg-stage">
    <svg viewBox="0 0 1560 1280" preserveAspectRatio="xMidYMid meet" class="nn-svg">
      <defs>
        <!-- Arrowhead Markers -->
        <marker id="arrow-blue" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38bdf8" opacity="0.6"/>
        </marker>
        <marker id="arrow-cyan" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#06b6d4" opacity="0.6"/>
        </marker>
        <marker id="arrow-green" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10b981" opacity="0.7"/>
        </marker>

        <!-- Drop Shadows & Glow Filters for static active rings -->
        <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="0" stdDeviation="6" flood-color="#fbbf24" flood-opacity="0.95"/>
        </filter>
        <filter id="glow-cyan" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#38bdf8" flood-opacity="0.7"/>
        </filter>
        <filter id="glow-emerald" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#10b981" flood-opacity="0.85"/>
        </filter>
        <filter id="glow-white" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#ffffff" flood-opacity="0.9"/>
        </filter>
        <filter id="glow-rose" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="0" stdDeviation="5" flood-color="#f43f5e" flood-opacity="0.85"/>
        </filter>
      </defs>

      <!-- 1. Column Titles & Structure Brackets -->
      <!-- Multi-Asset Input Layer Header (128 Circles) -->
      <text x="245" y="38" text-anchor="middle" class="svg-col-title">Multi-Asset Input Layer</text>
      <text x="245" y="66" text-anchor="middle" class="svg-col-counter mono">32 + 32 + 36 + 28 = TOTAL 128 LINGKARAN</text>

      <text x="95" y="92" text-anchor="middle" class="svg-micro-title mono">CRYPTO 1</text>
      <text x="195" y="92" text-anchor="middle" class="svg-micro-title mono">CRYPTO 2</text>
      <text x="295" y="92" text-anchor="middle" class="svg-micro-title mono">CRYPTO 3</text>
      <text x="395" y="92" text-anchor="middle" class="svg-micro-title mono text-emerald font-bold">FX / METALS</text>

      <!-- Quantitative Strategy Layer Header (88 Circles - Universal across all markets) -->
      <path 
        d="M 590,56 L 590,40 L 835,40 L 840,28 L 845,40 L 1090,40 L 1090,56" 
        fill="none" 
        stroke="#64748b" 
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <text x="840" y="24" text-anchor="middle" class="svg-col-title">Deep Quantitative Strategy Layer</text>
      <text x="840" y="66" text-anchor="middle" class="svg-col-counter mono text-cyan">30 + 29 + 29 = TOTAL 88 STRATEGI (SEMUA PASAR)</text>

      <text x="660" y="92" text-anchor="middle" class="svg-micro-title mono">QUANT 1</text>
      <text x="840" y="92" text-anchor="middle" class="svg-micro-title mono">QUANT 2</text>
      <text x="1020" y="92" text-anchor="middle" class="svg-micro-title mono">QUANT 3</text>

      <!-- Execution Output Header -->
      <text x="1380" y="50" text-anchor="middle" class="svg-col-title">Execution Engines</text>
      <text x="1380" y="70" text-anchor="middle" class="svg-col-sub mono">Tri-Market Output</text>

      <!-- 2. Dense Background Synapses (Clean & Fanned) -->
      <g class="background-synapses-group">
        {#each backgroundSynapses as syn (syn.id)}
          <line
            x1={syn.x1}
            y1={syn.y1}
            x2={syn.x2}
            y2={syn.y2}
            stroke={syn.color}
            stroke-width="0.8"
            stroke-opacity={syn.opacity}
          />
        {/each}
      </g>

      <!-- 3. ACTIVE PAIR ROUTES (When Pair is clicked directly) -->
      {#if activePairRoutes}
        <g class="active-pair-routes-group">
          {#each activePairRoutes.fanLines as line (line.id)}
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={line.color || (activePairRoutes.isForex ? '#10b981' : '#38bdf8')}
              stroke-width={line.width || 1.5}
              stroke-opacity={line.opacity || 0.40}
              stroke-linecap="round"
            />
          {/each}
        </g>
      {/if}

      <!-- 4. ACTIVE STRATEGY ROUTES (When Strategy is clicked directly) -->
      {#if activeStrategyRoutes}
        <g class="active-strategy-routes-group">
          <!-- Incoming Pair -> Strategy Lines (Seluruh 128 Pair) -->
          {#each activeStrategyRoutes.inputLines as line (line.id)}
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={line.color}
              stroke-width={line.width || 1.5}
              stroke-opacity={line.opacity || 0.40}
              stroke-linecap="round"
            />
          {/each}
          <!-- Outgoing Strategy -> Engine Lines (5 Engines) -->
          {#each activeStrategyRoutes.outputLines as line (line.id)}
            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={line.color}
              stroke-width={line.width || 3.5}
              stroke-opacity={line.opacity || 0.95}
              stroke-linecap="round"
              filter="url(#glow-cyan)"
            />
          {/each}
        </g>
      {/if}

      <!-- 5. EXACT AUDIT ROUTE (When clicked from Riwayat Audit Lengkap) -->
      <!-- Smooth, continuous, unbroken, physically exact -->
      {#if activeAuditRoute}
        <g class="active-audit-route-group">
          <!-- Background Glow Path -->
          {#each activeAuditRoute.segments as seg (seg.id)}
            <line
              x1={seg.x1}
              y1={seg.y1}
              x2={seg.x2}
              y2={seg.y2}
              stroke="#fbbf24"
              stroke-width="4.2"
              stroke-linecap="round"
              filter="url(#glow-gold)"
            />
            <line
              x1={seg.x1}
              y1={seg.y1}
              x2={seg.x2}
              y2={seg.y2}
              stroke="#ffffff"
              stroke-width="1.8"
              stroke-linecap="round"
              opacity="0.95"
            />
          {/each}
        </g>
      {/if}

      <!-- 6. ALL 128 INPUT PAIR NODES -->
      <g class="input-nodes-group">
        {#each all128Nodes as n (n.id)}
          {@const isAuditActive = Boolean(activeAuditRoute && activeAuditRoute.activeNodeIds.includes(n.id))}
          {@const isPairActive = Boolean(activePairRoutes && activePairRoutes.activeNodeIds.includes(n.id))}
          {@const isStrategyActive = Boolean(activeStrategyRoutes && activeStrategyRoutes.activeNodeIds.includes(n.id))}
          {@const isNodeActive = isAuditActive || isPairActive || isStrategyActive || n.isActive}
          {@const isPrimaryPair = Boolean(selectedSymbol && n.symbol === selectedSymbol)}
          {@const isNodeHovered = Boolean(hoveredNode && hoveredNode.id === n.id)}
          {@const isForex = n.category === 'forex'}

          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <g
            class="input-node-elem"
            role="button"
            tabindex="0"
            class:node-active={isNodeActive}
            class:node-hovered={isNodeHovered}
            class:node-dimmed={n.isDimmed && !isNodeActive && !isNodeHovered}
            onmouseenter={() => (hoveredNode = n)}
            onmouseleave={() => { if (hoveredNode && hoveredNode.id === n.id) hoveredNode = null; }}
            onclick={() => handlePairSelect(n.symbol)}
            onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handlePairSelect(n.symbol); }}
            cursor="pointer"
          >
            <!-- Outer Glow Ring for Active Node (Saat Audit / Pair / Strategy diklik) -->
            {#if isNodeActive}
              <circle
                cx={n.x}
                cy={n.y}
                r={n.r + (isPrimaryPair ? 6.5 : 4.5)}
                fill="none"
                stroke={isAuditActive ? '#fbbf24' : (isPrimaryPair ? '#ffffff' : (isForex ? '#10b981' : '#38bdf8'))}
                stroke-width={isAuditActive || isPrimaryPair ? 3.5 : 2.0}
                filter={isAuditActive ? 'url(#glow-gold)' : (isPrimaryPair ? (isForex ? 'url(#glow-emerald)' : 'url(#glow-cyan)') : undefined)}
                stroke-opacity={isPrimaryPair ? 1 : 0.85}
              />
            {/if}

            <!-- Main Neuron Circle -->
            <circle
              cx={n.x}
              cy={n.y}
              r={n.r}
              fill={isNodeActive ? (isAuditActive ? 'rgba(251, 191, 36, 0.25)' : (isPrimaryPair ? (isForex ? 'rgba(16, 185, 129, 0.45)' : 'rgba(56, 189, 248, 0.45)') : (isForex ? 'rgba(16, 185, 129, 0.22)' : 'rgba(56, 189, 248, 0.20)'))) : isNodeHovered ? '#ffffff' : (isForex ? 'rgba(16, 185, 129, 0.08)' : 'rgba(56, 189, 248, 0.06)')}
              stroke={isNodeActive ? (isAuditActive ? '#fbbf24' : (isPrimaryPair ? '#ffffff' : (isForex ? '#10b981' : '#38bdf8'))) : isNodeHovered ? '#ffffff' : (isForex ? '#10b981' : '#38bdf8')}
              stroke-width={isNodeActive ? (isPrimaryPair ? 3.2 : 2.2) : (isForex ? 2.0 : 1.6)}
            />

            <!-- Base Symbol Text inside Circle -->
            <text
              x={n.x}
              y={n.y + 3.8}
              text-anchor="middle"
              class="input-sym mono font-bold"
              font-size={n.base.length >= 5 ? '8.0' : (n.base.length >= 4 ? '9.2' : '10.5')}
              fill={isNodeActive ? '#ffffff' : (isForex ? '#34d399' : '#e2e8f0')}
              font-weight="800"
            >
              {n.base}
            </text>
          </g>
        {/each}
      </g>

      <!-- 7. ALL 88 STRATEGY NODES (In 3 Columns, Universal for all markets) -->
      <g class="strategy-nodes-group">
        {#each all88StrategyNodes as s (s.id)}
          {@const isAuditActive = Boolean(activeAuditRoute && activeAuditRoute.activeNodeIds.includes(s.id))}
          {@const isPairActive = Boolean(activePairRoutes && activePairRoutes.activeNodeIds.includes(s.id))}
          {@const isStrategyActive = Boolean(activeStrategyRoutes && activeStrategyRoutes.activeNodeIds.includes(s.id))}
          {@const isNodeActive = isAuditActive || isPairActive || isStrategyActive}
          {@const isPrimaryStrat = Boolean(selectedStrategyId && (s.id === selectedStrategyId || s.stratId === selectedStrategyId))}
          {@const isNodeHovered = Boolean(hoveredNode && hoveredNode.id === s.id)}
          {@const baseColor = getStratColor(s.family)}

          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <g
            class="strategy-node-elem"
            role="button"
            tabindex="0"
            class:node-active={isNodeActive}
            class:node-hovered={isNodeHovered}
            onmouseenter={() => (hoveredNode = s)}
            onmouseleave={() => { if (hoveredNode && hoveredNode.id === s.id) hoveredNode = null; }}
            onclick={() => handleStrategyClick(s)}
            onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleStrategyClick(s); }}
            cursor="pointer"
          >
            <!-- Outer Glow Halo (Hanya saat Audit / Pair / Strategy diklik) -->
            {#if isNodeActive}
              <circle
                cx={s.x}
                cy={s.y}
                r={s.r + (isPrimaryStrat ? 6.5 : 4.5)}
                fill="none"
                stroke={isAuditActive ? '#fbbf24' : '#ffffff'}
                stroke-width={isAuditActive || isPrimaryStrat ? 3.5 : 2.0}
                filter={isAuditActive ? 'url(#glow-gold)' : (isPrimaryStrat ? 'url(#glow-white)' : undefined)}
                stroke-opacity={isPrimaryStrat ? 1 : 0.85}
              />
            {/if}

            <!-- Main Strategy Circle (Semua Lingkaran Putih Seragam) -->
            <circle
              cx={s.x}
              cy={s.y}
              r={s.r}
              fill={isNodeActive ? (isAuditActive ? 'rgba(251, 191, 36, 0.32)' : (isPrimaryStrat ? 'rgba(255, 255, 255, 0.35)' : 'rgba(255, 255, 255, 0.18)')) : isNodeHovered ? 'rgba(255, 255, 255, 0.25)' : 'rgba(255, 255, 255, 0.06)'}
              stroke={isAuditActive ? '#fbbf24' : '#ffffff'}
              stroke-width={isNodeActive ? (isPrimaryStrat ? 3.2 : 2.2) : 1.8}
              stroke-opacity={isNodeActive ? 1.0 : (isNodeHovered ? 1.0 : 0.85)}
            />

            <!-- Short Code Text inside Circle -->
            <text
              x={s.x}
              y={s.y + 4.0}
              text-anchor="middle"
              class="strategy-code mono font-bold"
              font-size={s.code.length >= 5 ? '8.5' : (s.code.length >= 4 ? '9.8' : '11.0')}
              fill="#ffffff"
              font-weight="800"
            >
              {s.code}
            </text>
          </g>
        {/each}
      </g>

      <!-- 8. EXECUTION ENGINES · TRI-MARKET OUTPUT (Layer 3) -->
      <g class="output-group">
        {#each outputNodes as o}
          {@const isAuditActive = Boolean(activeAuditRoute && activeAuditRoute.activeNodeIds.includes(o.id))}
          {@const isPairActive = Boolean(activePairRoutes && activePairRoutes.activeOutputIds.includes(o.id))}
          {@const isStrategyActive = Boolean(activeStrategyRoutes && activeStrategyRoutes.activeOutputIds.includes(o.id))}
          {@const isNodeActive = isAuditActive || isPairActive || isStrategyActive}
          {@const isNodeDimmed = Boolean((activePairRoutes && !activePairRoutes.activeOutputIds.includes(o.id)) || (activeStrategyRoutes && !activeStrategyRoutes.activeOutputIds.includes(o.id)))}
          {@const isNodeHovered = Boolean(hoveredNode && hoveredNode.id === o.id)}
          {@const isForex = o.isForexOnly}

          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <g
            class="output-node-elem"
            role="button"
            tabindex="0"
            class:node-active={isNodeActive}
            class:node-hovered={isNodeHovered}
            class:node-dimmed={isNodeDimmed}
            onmouseenter={() => (hoveredNode = o)}
            onmouseleave={() => { if (hoveredNode && hoveredNode.id === o.id) hoveredNode = null; }}
            cursor="pointer"
          >
            {#if isNodeActive}
              <circle
                cx={o.x}
                cy={o.y}
                r={o.R + 10}
                fill="none"
                stroke={isAuditActive ? '#fbbf24' : (isForex ? '#10b981' : (o.id === 'out_spot' ? '#f43f5e' : '#f59e0b'))}
                stroke-width="3.8"
                filter={isAuditActive ? 'url(#glow-gold)' : (isForex ? 'url(#glow-emerald)' : (o.id === 'out_spot' ? 'url(#glow-rose)' : 'url(#glow-gold)'))}
              />
            {/if}

            <circle
              cx={o.x}
              cy={o.y}
              r={o.R}
              fill={isNodeActive ? (isAuditActive ? 'rgba(251, 191, 36, 0.28)' : (isForex ? 'rgba(16, 185, 129, 0.25)' : (o.id === 'out_spot' ? 'rgba(244, 63, 94, 0.25)' : 'rgba(245, 158, 11, 0.22)'))) : (isForex ? 'rgba(16, 185, 129, 0.12)' : (o.id === 'out_spot' ? 'rgba(244, 63, 94, 0.12)' : 'rgba(245, 158, 11, 0.10)'))}
              stroke={isNodeActive ? (isAuditActive ? '#fbbf24' : (isForex ? '#10b981' : (o.id === 'out_spot' ? '#f43f5e' : '#f59e0b'))) : isNodeHovered ? '#ffffff' : (isForex ? '#10b981' : (o.id === 'out_spot' ? '#f43f5e' : '#f59e0b'))}
              stroke-width={isNodeActive ? 3.8 : 2.6}
            />

            <text x={o.x} y={o.y + 5.5} text-anchor="middle" class="node-label mono font-bold" font-size="14.5" fill={isNodeActive ? '#ffffff' : (isForex ? '#34d399' : (o.id === 'out_spot' ? '#f43f5e' : '#fbbf24'))} font-weight="800">
              {o.label}
            </text>
            <text x={o.x} y={o.y + o.R + 18} text-anchor="middle" class="node-sub mono" fill="#94a3b8" font-size="11.5" font-weight="700">
              {o.sub}
            </text>
          </g>
        {/each}
      </g>
    </svg>

    <!-- Dedicated Hardware-Accelerated 2D Canvas for Zero-Lag Pulses & Laser Particles -->
    <canvas
      bind:this={canvasElem}
      width="1560"
      height="1280"
      class="pulse-canvas"
    ></canvas>

    <!-- Floating HUD Tooltip when hovering any Node -->
    {#if hoveredNode}
      <div 
        class="floating-hud mono"
        style="left: {Math.min(85, Math.max(10, (hoveredNode.x / 1560) * 100))}%; top: {Math.max(5, (hoveredNode.y / 1280) * 100)}%;"
      >
        {#if hoveredNode.symbol}
          <!-- Input Pair Node Tooltip -->
          <div class="hud-header">
            <span class="hud-cat-tag {hoveredNode.category}">
              {hoveredNode.category === 'forex' ? 'FOREX & METALS' : 'CRYPTO SPOT / FUT'}
            </span>
            <span class="hud-symbol">{hoveredNode.symbol}</span>
          </div>
          <div class="hud-name">{hoveredNode.name}</div>
          <div class="hud-meta">
            {#if hoveredNode.price}
              <span class="hud-price">${Number(hoveredNode.price).toFixed(2)}</span>
            {/if}
            <span class="hud-action">Klik untuk aktifkan jalur seluruh pasar ➔</span>
          </div>
        {:else if hoveredNode.stratId}
          <!-- Quantitative Strategy Node Tooltip -->
          <div class="hud-header">
            <span class="hud-cat-tag crypto">QUANT MODEL</span>
            <span class="hud-symbol">{hoveredNode.code}</span>
          </div>
          <div class="hud-name">{hoveredNode.name}</div>
          <div class="hud-desc">{hoveredNode.family} Family · Multi-Market (Spot, Futures, Forex)</div>
          <div class="hud-meta">
            <span class="hud-action">Model Kuantitatif Universal</span>
          </div>
        {:else}
          <!-- Universal / Risk / Output Node Tooltip -->
          <div class="hud-header">
            <span class="hud-cat-tag crypto">PIPELINE NODE</span>
            <span class="hud-symbol">{hoveredNode.label}</span>
          </div>
          <div class="hud-name">{hoveredNode.sub}</div>
          <div class="hud-desc">{hoveredNode.desc}</div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Footer Legend -->
  <div class="nn-footer-legend mono">
    <div class="legend-item">
      <span class="legend-dot dot-cyan"></span>
      <span>INPUT CRYPTO</span>
    </div>
    <div class="legend-item">
      <span class="legend-dot dot-emerald"></span>
      <span>INPUT FOREX</span>
    </div>
    <div class="legend-item">
      <span class="legend-dot dot-white"></span>
      <span>QUANT STRATEGIES (88)</span>
    </div>
    <div class="legend-item">
      <span class="legend-dot dot-amber"></span>
      <span>OUTPUT ENGINES (SPOT, FUTURES & FOREX)</span>
    </div>
  </div>
</div>

<style>
  .execution-nn-box {
    background: #080c14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
  }

  .nn-top-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    margin-bottom: 8px;
  }

  .controls-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .live-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: blink 1.5s infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .title-bold {
    font-size: 12.5px;
    font-weight: 800;
    color: #e2e8f0;
    letter-spacing: 0.05em;
  }

  .pair-counter-pill {
    font-size: 10px;
    font-weight: 800;
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.35);
    padding: 2px 8px;
    border-radius: 4px;
  }

  .controls-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .category-tabs {
    display: flex;
    align-items: center;
    gap: 4px;
    background: #04070d;
    padding: 2px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .cat-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 10.5px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .cat-btn:hover {
    color: #ffffff;
  }

  .cat-btn.active {
    background: #151e30;
    color: #ffffff;
    box-shadow: 0 0 8px rgba(0, 0, 0, 0.4);
  }

  .search-pair-box {
    position: relative;
    display: flex;
    align-items: center;
  }

  .pair-search-input {
    background: #04070d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
    font-size: 10.5px;
    padding: 5px 24px 5px 10px;
    border-radius: 5px;
    width: 210px;
    transition: all 0.15s ease;
  }

  .pair-search-input:focus {
    outline: none;
    border-color: #38bdf8;
    background: #0b1220;
    width: 240px;
  }

  .btn-clear-search {
    position: absolute;
    right: 6px;
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 10px;
    cursor: pointer;
  }

  .btn-clear-search:hover {
    color: #ffffff;
  }

  .active-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(251, 191, 36, 0.15);
    border: 1px solid rgba(251, 191, 36, 0.4);
    color: #fbbf24;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 10px;
  }

  .active-badge.badge-audit {
    background: rgba(245, 158, 11, 0.22);
    border-color: #f59e0b;
    box-shadow: 0 0 10px rgba(245, 158, 11, 0.35);
  }

  .active-badge.badge-strategy {
    background: rgba(56, 189, 248, 0.20);
    border-color: #38bdf8;
    color: #38bdf8;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
  }

  .active-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #fbbf24;
    box-shadow: 0 0 6px #fbbf24;
  }

  .dot-gold {
    background: #f59e0b;
    box-shadow: 0 0 8px #f59e0b;
  }

  .dot-cyan {
    background: #38bdf8;
    box-shadow: 0 0 8px #38bdf8;
  }

  .dot-white {
    background: #ffffff;
    box-shadow: 0 0 8px #ffffff;
  }

  .clear-btn {
    background: transparent;
    border: none;
    color: #fbbf24;
    cursor: pointer;
    font-size: 9px;
    padding: 0 2px;
  }

  /* Main SVG Stage */
  .svg-stage {
    position: relative;
    width: 100%;
    margin: 8px 0;
    border-radius: 8px;
    background: radial-gradient(circle at 15% 50%, rgba(56, 189, 248, 0.04) 0%, transparent 60%),
                radial-gradient(circle at 85% 50%, rgba(245, 158, 11, 0.04) 0%, transparent 60%);
    overflow: hidden;
  }

  .nn-svg {
    width: 100%;
    height: auto;
    display: block;
    user-select: none;
  }

  .pulse-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 5;
  }

  .svg-col-title {
    font-family: inherit;
    font-size: 15px;
    font-weight: 800;
    fill: #f1f5f9;
    letter-spacing: 0.03em;
  }

  .svg-col-sub {
    font-size: 11px;
    fill: #94a3b8;
    letter-spacing: 0.02em;
  }

  .svg-col-counter {
    font-size: 11px;
    font-weight: 800;
    fill: #f59e0b;
    letter-spacing: 0.05em;
  }

  .svg-micro-title {
    font-size: 9.5px;
    font-weight: 800;
    fill: #64748b;
    letter-spacing: 0.06em;
  }

  .text-emerald {
    fill: #10b981 !important;
    color: #10b981 !important;
  }

  .text-cyan {
    color: #38bdf8 !important;
    fill: #38bdf8 !important;
  }

  /* Node Hover & Dim Styles */
  .input-node-elem,
  .strategy-node-elem,
  .output-node-elem {
    transition: transform 0.15s ease, opacity 0.15s ease;
  }

  .node-dimmed {
    opacity: 0.20 !important;
  }

  .node-hovered {
    opacity: 1.0 !important;
  }

  /* Floating HUD Tooltip */
  .floating-hud {
    position: absolute;
    pointer-events: none;
    transform: translate(-50%, -120%);
    background: #090e17;
    border: 1px solid rgba(56, 189, 248, 0.4);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.7), 0 0 12px rgba(56, 189, 248, 0.2);
    border-radius: 6px;
    padding: 8px 12px;
    z-index: 50;
    min-width: 170px;
    white-space: nowrap;
    animation: fadeIn 0.15s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translate(-50%, -110%); }
    to { opacity: 1; transform: translate(-50%, -120%); }
  }

  .hud-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .hud-cat-tag {
    font-size: 8px;
    font-weight: 800;
    padding: 1px 4px;
    border-radius: 3px;
  }

  .hud-cat-tag.forex {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
  }

  .hud-cat-tag.crypto {
    background: rgba(56, 189, 248, 0.2);
    color: #38bdf8;
  }

  .hud-symbol {
    font-size: 11px;
    font-weight: 800;
    color: #ffffff;
  }

  .hud-name {
    font-size: 9.5px;
    color: #cbd5e1;
    margin-bottom: 4px;
  }

  .hud-desc {
    font-size: 8.5px;
    color: #94a3b8;
    margin-bottom: 4px;
  }

  .hud-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 9px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 4px;
  }

  .hud-price {
    font-weight: 800;
    color: #fbbf24;
  }

  .hud-action {
    color: #38bdf8;
    font-size: 8.5px;
  }

  /* Footer Legend */
  .nn-footer-legend {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
    padding-top: 14px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    font-size: 10px;
    color: #94a3b8;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .dot-cyan {
    background: #38bdf8;
    box-shadow: 0 0 6px rgba(56, 189, 248, 0.6);
  }

  .dot-emerald {
    background: #10b981;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
  }

  .dot-teal {
    background: #0ea5e9;
    box-shadow: 0 0 6px rgba(14, 165, 233, 0.6);
  }

  .dot-amber {
    background: #f59e0b;
    box-shadow: 0 0 6px rgba(245, 158, 11, 0.6);
  }

  /* Recent Opened Trades Feed Pills */

  /* Recent Opened Trades Queue */
  .recent-trades-feed {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 10px;
    margin-bottom: 12px;
    background: rgba(0, 0, 0, 0.25);
    border-radius: 6px;
    overflow-x: auto;
  }

  .feed-label {
    font-size: 9.5px;
    color: #64748b;
    white-space: nowrap;
    font-weight: 700;
  }

  .feed-pills-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: nowrap;
  }

  .feed-pill-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 10px;
    color: #cbd5e1;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s ease;
  }

  .feed-pill-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    transform: translateY(-1px);
  }


  .feed-pill-btn.active-pill {
    background: rgba(56, 189, 248, 0.2);
    border-color: #38bdf8;
    color: #ffffff;
  }

  .pill-mode {
    font-size: 8.5px;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.06);
    padding: 1px 4px;
    border-radius: 3px;
  }
</style>
