<script>
  import { onMount, onDestroy } from 'svelte';
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD } from '../lib/formatters.js';

  // Live Multi-Asset Ticks from Store (Crypto + Forex & Metals)
  let btcPrice = $derived(arena.prices['BTCUSDT']?.price ?? arena.prices['BTCUSDT'] ?? 67840);
  let ethPrice = $derived(arena.prices['ETHUSDT']?.price ?? arena.prices['ETHUSDT'] ?? 3485);
  let solPrice = $derived(arena.prices['SOLUSDT']?.price ?? arena.prices['SOLUSDT'] ?? 182.5);

  let xauPrice = $derived(arena.prices['XAUUSD']?.price ?? arena.prices['XAUUSD'] ?? 4048.45);
  let eurPrice = $derived(arena.prices['EURUSD']?.price ?? arena.prices['EURUSD'] ?? 1.11324);
  let oilPrice = $derived(arena.prices['XTIUSD']?.price ?? arena.prices['XTIUSD'] ?? 105.69);

  // Neural Network Architecture Data
  // Radius of each neuron circle
  const R = 18;
  const ARROW_OFFSET = 3;

  // Unified Multi-Asset Neural Architecture (Crypto + Forex + Metals running concurrently)
  const layers = [
    {
      id: 'input',
      name: 'Multi-Asset Feed Layer',
      x: 80,
      nodes: [
        { id: 'in_0', label: 'BTC', sub: 'CRYPTO', val: () => `$${formatUSD(btcPrice).replace('$', '')}`, desc: 'Bitcoin Live WebSocket Tick (Binance Futures/Spot)', type: 'input' },
        { id: 'in_1', label: 'ETH', sub: 'CRYPTO', val: () => `$${formatUSD(ethPrice).replace('$', '')}`, desc: 'Ethereum Live WebSocket Tick (Binance)', type: 'input' },
        { id: 'in_2', label: 'XAU', sub: 'METALS', val: () => `$${Number(xauPrice).toFixed(2)}`, desc: 'Spot Gold / US Dollar (MetaTrader 5 Headway Live Feed)', type: 'input' },
        { id: 'in_3', label: 'EUR', sub: 'FOREX', val: () => `${Number(eurPrice).toFixed(5)}`, desc: 'Euro / US Dollar Major Pair (MT5 Live Feed)', type: 'input' },
        { id: 'in_4', label: 'OIL', sub: 'ENERGY', val: () => `$${Number(oilPrice).toFixed(2)}`, desc: 'WTI Crude Oil vs USD (MT5 Commodity Feed)', type: 'input' },
        { id: 'in_5', label: 'VOL', sub: 'DEPTH', val: () => 'OrderBook', desc: 'Real-Time Order Book Volume & Market Depth', type: 'input' },
        { id: 'in_6', label: 'SPR', sub: 'PIPS', val: () => 'Dynamic', desc: 'MT5 Broker Real-Time Bid/Ask Dynamic Spread', type: 'input' },
      ],
      yCoords: [84, 140, 196, 252, 308, 364, 420],
      stroke: '#38bdf8',
      fill: 'rgba(56, 189, 248, 0.08)',
      glow: '#38bdf8',
    },
    {
      id: 'h1',
      name: 'Hidden Layer 1 · Signal & Feature Extractors',
      x: 275,
      nodes: [
        { id: 'h1_0', label: 'SMC', sub: 'OB', desc: 'SMC Institutional Order Block Mitigation Algorithm' },
        { id: 'h1_1', label: 'ICT', sub: 'FVG', desc: 'ICT Fair Value Gap Imbalance Retest Model' },
        { id: 'h1_2', label: 'EMA', sub: 'Stack', desc: 'Multi-Timeframe EMA 9/21/50 Trend Alignment' },
        { id: 'h1_3', label: 'MACD', sub: 'Mom', desc: 'MACD Histogram & Momentum Divergence Engine' },
        { id: 'h1_4', label: 'SWP', sub: 'BOS', desc: 'Liquidity Sweep & Market Structure Shift (MSS/BOS)' },
        { id: 'h1_5', label: 'VSA', sub: 'Vol', desc: 'Volume Spread Analysis & Stopping Volume Absorption' },
        { id: 'h1_6', label: 'ATR', sub: 'Sqze', desc: 'Bollinger/Keltner Volatility Squeeze & Channel Break' },
      ],
      yCoords: [84, 140, 196, 252, 308, 364, 420],
      stroke: '#06b6d4',
      fill: 'rgba(6, 182, 212, 0.08)',
      glow: '#06b6d4',
    },
    {
      id: 'h3',
      name: 'Hidden Layer 2 · Risk & Capital Allocation',
      x: 475,
      nodes: [
        { id: 'h3_0', label: 'NORM', sub: 'Z-Scr', desc: 'Statistical Z-Score Price Normalization' },
        { id: 'h3_1', label: 'RISK', sub: '2% SL', desc: 'Strict 2% Equity Portfolio Risk Controller ($200 Max SL)' },
        { id: 'h3_2', label: 'BAL', sub: 'Balance', desc: 'Realized Clean Balance & Live MTM Tracking' },
        { id: 'h3_3', label: 'FUND', sub: '8h Fee', desc: 'Crypto Futures 8-Hour Funding Rate Simulator' },
        { id: 'h3_4', label: 'LEVR', sub: '20x Cap', desc: 'Crypto Futures Leverage Multiplier Control (1-20x)' },
        { id: 'h3_5', label: 'LOT', sub: 'Direct', desc: 'MetaTrader 5 Direct Standard Lot Sizing (Tanpa Leverage Kripto)' },
        { id: 'h3_6', label: 'SPRD', sub: '0-Slipp', desc: 'Live Headway Broker Dynamic Bid/Ask Spread Filter' },
      ],
      yCoords: [84, 140, 196, 252, 308, 364, 420],
      stroke: '#10b981',
      fill: 'rgba(16, 185, 129, 0.08)',
      glow: '#10b981',
    },
    {
      id: 'output',
      name: 'Execution Engines · Tri-Market Output',
      x: 670,
      nodes: [
        { id: 'out_0', label: 'FUT·L', sub: 'FUTURES', tag: '20x LEV', desc: 'Binance Futures Long Position (Leverage 1-20x)', type: 'output-long' },
        { id: 'out_1', label: 'SPOT', sub: 'CRYPTO', tag: '1x SPOT', desc: 'Binance Spot Execution (Long-Only, Tanpa Leverage)', type: 'output-spot' },
        { id: 'out_2', label: 'FX·BUY', sub: 'MT5 DIRECT', tag: 'LOT SIZING', desc: 'MetaTrader 5 Direct Buy Order (Spread Riil, Non-Crypto)', type: 'output-forex' },
        { id: 'out_3', label: 'FX·SEL', sub: 'MT5 DIRECT', tag: 'LOT SIZING', desc: 'MetaTrader 5 Direct Sell Order (Spread Riil, Non-Crypto)', type: 'output-forex' },
        { id: 'out_4', label: 'FUT·S', sub: 'FUTURES', tag: '20x LEV', desc: 'Binance Futures Short Position (Leverage 1-20x)', type: 'output-short' },
      ],
      yCoords: [140, 196, 252, 308, 364],
      stroke: '#f59e0b',
      fill: 'rgba(245, 158, 11, 0.08)',
      glow: '#f59e0b',
    },
  ];

  // Precompute clean edge-to-edge synapse lines between consecutive layers
  const synapses = [];
  for (let l = 0; l < layers.length - 1; l++) {
    const l1 = layers[l];
    const l2 = layers[l + 1];

    for (let i = 0; i < l1.nodes.length; i++) {
      const x1 = l1.x;
      const y1 = l1.yCoords[i];

      for (let j = 0; j < l2.nodes.length; j++) {
        const x2 = l2.x;
        const y2 = l2.yCoords[j];

        // Edge clipping math: line starts at circle 1 perimeter and ends at circle 2 perimeter
        const dx = x2 - x1;
        const dy = y2 - y1;
        const dist = Math.hypot(dx, dy);
        const ux = dx / dist;
        const uy = dy / dist;

        const sx = x1 + ux * R;
        const sy = y1 + uy * R;
        const ex = x2 - ux * (R + ARROW_OFFSET);
        const ey = y2 - uy * (R + ARROW_OFFSET);

        synapses.push({
          id: `${l1.nodes[i].id}->${l2.nodes[j].id}`,
          fromId: l1.nodes[i].id,
          toId: l2.nodes[j].id,
          sx,
          sy,
          ex,
          ey,
          layerIdx: l,
        });
      }
    }
  }

  // Active hover inspection
  let hoveredNodeId = $state(null);
  let hoveredNodeInfo = $derived.by(() => {
    if (!hoveredNodeId) return null;
    for (const l of layers) {
      for (let i = 0; i < l.nodes.length; i++) {
        const n = l.nodes[i];
        if (n.id === hoveredNodeId) {
          return {
            layer: l.name,
            label: n.label,
            sub: n.sub,
            desc: n.desc ?? n.val?.() ?? 'Active Neural Node',
          };
        }
      }
    }
    return null;
  });

  // Animated Inference Pulses traveling across random paths from Input to Output
  let activePulses = $state([]);
  let pulseTimer = null;

  onMount(() => {
    // Generate a new flowing pulse wave every 500ms
    pulseTimer = setInterval(() => {
      // Pick random nodes in each layer to form an active multi-asset signal chain
      const n0 = Math.floor(Math.random() * layers[0].nodes.length);
      const n1 = Math.floor(Math.random() * layers[1].nodes.length);
      const n2 = Math.floor(Math.random() * layers[2].nodes.length);
      const n3 = Math.floor(Math.random() * layers[3].nodes.length);

      const chain = [
        `in_${n0}->h1_${n1}`,
        `h1_${n1}->h3_${n2}`,
        `h3_${n2}->out_${n3}`,
      ];

      // Multi-asset pulse colors: cyan (crypto), emerald (forex), amber (futures), purple (arbitrage)
      const colors = ['#38bdf8', '#10b981', '#f59e0b', '#a855f7'];
      const chosenColor = colors[Math.floor(Math.random() * colors.length)];

      const newPulse = {
        id: Date.now() + Math.random(),
        chain,
        color: chosenColor,
        step: 0,
        t: 0,
      };

      activePulses = [...activePulses.slice(-7), newPulse];
    }, 550);

    // 60FPS animation loop for pulse particle movement
    let animFrame;
    function updatePulses() {
      animFrame = requestAnimationFrame(updatePulses);
      activePulses = activePulses
        .map((p) => {
          p.t += 0.038;
          if (p.t >= 1) {
            p.t = 0;
            p.step += 1;
          }
          return p;
        })
        .filter((p) => p.step < p.chain.length);
    }
    updatePulses();

    return () => {
      if (pulseTimer) clearInterval(pulseTimer);
      if (animFrame) cancelAnimationFrame(animFrame);
    };
  });
</script>

<div class="nn-panel">
  <!-- Top Panel Header -->
  <div class="panel-top-bar">
    <div class="top-title">
      <span class="live-pulse-dot"></span>
      <span class="mono header-tag">STRATEGY ARENA · UNIFIED MULTI-ASSET NEURAL NETWORK</span>
    </div>
  </div>

  <!-- Main Responsive SVG Canvas -->
  <div class="svg-container">
    <svg viewBox="0 0 760 480" preserveAspectRatio="xMidYMid meet" class="nn-svg">
      <defs>
        <!-- Arrowhead Markers matching each layer color -->
        <marker id="arrow-blue" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38bdf8" opacity="0.6"/>
        </marker>
        <marker id="arrow-cyan" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#06b6d4" opacity="0.6"/>
        </marker>
        <marker id="arrow-teal" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#0ea5e9" opacity="0.6"/>
        </marker>
        <marker id="arrow-green" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10b981" opacity="0.7"/>
        </marker>

        <!-- Node glow filters -->
        <filter id="glow-blue" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#38bdf8" flood-opacity="0.5"/>
        </filter>
        <filter id="glow-gold" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#f59e0b" flood-opacity="0.6"/>
        </filter>
        <filter id="glow-emerald" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#10b981" flood-opacity="0.6"/>
        </filter>
      </defs>

      <!-- 1. DIAGRAM TITLES & BRACKETS -->

      <!-- Column Title: Input layer -->
      <text x="80" y="48" text-anchor="middle" class="svg-col-title">Multi-Asset Input</text>

      <!-- Bracket above Multiple hidden layers (x = 275 to x = 475) -->
      <path 
        d="M 275,54 L 275,40 L 367,40 L 375,32 L 383,40 L 475,40 L 475,54" 
        fill="none" 
        stroke="#64748b" 
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <text x="375" y="28" text-anchor="middle" class="svg-col-title">Deep Quantitative Neural Layers (88 Models · SMC / ICT / Trend)</text>

      <!-- Column Title: Output layer -->
      <text x="670" y="48" text-anchor="middle" class="svg-col-title">Execution Engines</text>

      <!-- 2. SYNAPSE CONNECTIONS (Directed arrows between all layers) -->
      <g class="synapse-group">
        {#each synapses as syn (syn.id)}
          {@const isConnected = hoveredNodeId && (syn.fromId === hoveredNodeId || syn.toId === hoveredNodeId)}
          {@const markerName = syn.layerIdx === 0 ? 'arrow-blue' : syn.layerIdx === 1 ? 'arrow-cyan' : 'arrow-green'}
          <line
            x1={syn.sx}
            y1={syn.sy}
            x2={syn.ex}
            y2={syn.ey}
            class="synapse-line"
            class:synapse-active={isConnected}
            stroke={isConnected ? '#f59e0b' : syn.layerIdx === 0 ? '#38bdf8' : syn.layerIdx === 1 ? '#06b6d4' : '#10b981'}
            stroke-width={isConnected ? 2.2 : 0.95}
            stroke-opacity={isConnected ? 0.95 : 0.22}
            marker-end="url(#{markerName})"
          />
        {/each}
      </g>

      <!-- 3. ANIMATED FEED-FORWARD INFERENCE PULSES -->
      <g class="pulses-group">
        {#each activePulses as pulse (pulse.id)}
          {@const currentSynId = pulse.chain[pulse.step]}
          {@const syn = synapses.find(s => s.id === currentSynId)}
          {#if syn}
            {@const px = syn.sx + (syn.ex - syn.sx) * pulse.t}
            {@const py = syn.sy + (syn.ey - syn.sy) * pulse.t}
            <circle cx={px} cy={py} r="3.2" fill={pulse.color} filter="url(#glow-gold)" opacity="0.95"/>
          {/if}
        {/each}
      </g>

      <!-- 4. NEURON CIRCLE NODES -->
      {#each layers as layer}
        <g class="layer-group">
          {#each layer.nodes as node, idx}
            {@const ny = layer.yCoords[idx]}
            {@const isHovered = hoveredNodeId === node.id}
            {@const isForexNode = node.type === 'output-forex' || node.label === 'XAU' || node.label === 'EUR' || node.label === 'OIL' || node.label === 'SPR' || node.label === 'LOT' || node.label === 'SMC' || node.label === 'ICT'}
            
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <g 
              class="node-group" 
              class:node-hovered={isHovered}
              onmouseenter={() => (hoveredNodeId = node.id)}
              onmouseleave={() => (hoveredNodeId = null)}
              cursor="pointer"
            >
              <!-- Outer glowing aura on hover -->
              {#if isHovered}
                <circle cx={layer.x} cy={ny} r={R + 5} fill="none" stroke={isForexNode ? '#10b981' : '#f59e0b'} stroke-width="2" opacity="0.8"/>
              {/if}

              <!-- Main Neuron Ring -->
              <circle
                cx={layer.x}
                cy={ny}
                r={R}
                fill={layer.id === 'output' ? (node.type === 'output-forex' ? 'rgba(16, 185, 129, 0.14)' : 'rgba(245, 158, 11, 0.12)') : layer.id === 'input' ? 'rgba(56, 189, 248, 0.1)' : 'rgba(6, 182, 212, 0.08)'}
                stroke={isHovered ? '#ffffff' : (node.type === 'output-forex' ? '#10b981' : layer.stroke)}
                stroke-width="2.5"
                class="neuron-circle"
              />

              <!-- Inner Center Dot / Code Symbol -->
              <text 
                x={layer.x} 
                y={ny + 3.5} 
                text-anchor="middle" 
                class="node-label mono"
                font-size={node.label.length >= 5 ? '8.5' : (node.label.length >= 4 ? '9' : '10')}
                fill={layer.id === 'output' ? (node.type === 'output-forex' ? '#34d399' : '#fbbf24') : '#ffffff'}
              >
                {node.label}
              </text>
            </g>
          {/each}
        </g>
      {/each}
    </svg>
  </div>

  <!-- Bottom Institutional Telemetry Footer & Node Inspector -->
  <div class="panel-bottom-bar">
    {#if hoveredNodeInfo}
      <div class="inspector-active mono">
        <span class="ins-layer">{hoveredNodeInfo.layer}</span>
        <span class="ins-dot">·</span>
        <span class="ins-name">{hoveredNodeInfo.label} ({hoveredNodeInfo.sub})</span>
        <span class="ins-dot">·</span>
        <span class="ins-desc">{hoveredNodeInfo.desc}</span>
      </div>
    {:else}
      <div class="legend-strip mono">
        <div class="l-item">
          <span class="l-dot dot-blue"></span>
          <span>INPUT (100+ PAIRS)</span>
        </div>
        <div class="l-item">
          <span class="l-dot dot-cyan"></span>
          <span>HIDDEN (80+ QUANTS)</span>
        </div>
        <div class="l-item">
          <span class="l-dot dot-gold"></span>
          <span>OUTPUT (CRYPTO SPOT, FUTURES & MT5 DIRECT)</span>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .nn-panel {
    background: #06090e;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 18px 20px 14px 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.55);
    height: 100%;
    min-height: 520px;
    position: relative;
    overflow: hidden;
  }

  /* Top Bar */
  .panel-top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .top-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .live-pulse-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  .header-tag {
    font-size: 11px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: 0.05em;
  }

  /* SVG Container */
  .svg-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 6px 0;
  }

  .nn-svg {
    width: 100%;
    height: auto;
    max-height: 440px;
    display: block;
    user-select: none;
  }

  .svg-col-title {
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 11px;
    font-weight: 700;
    fill: #94a3b8;
    letter-spacing: 0.02em;
  }

  /* Node Typography & Effects */
  .neuron-circle {
    transition: transform 0.15s ease, stroke 0.15s ease;
  }

  .node-label {
    font-weight: 800;
    pointer-events: none;
    letter-spacing: 0.02em;
  }

  .synapse-line {
    transition: stroke-opacity 0.15s ease, stroke-width 0.15s ease;
  }

  .synapse-active {
    stroke-opacity: 1 !important;
  }

  /* Bottom Legend / Inspector */
  .panel-bottom-bar {
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 28px;
  }

  .legend-strip {
    display: flex;
    gap: 16px;
    font-size: 9.5px;
    color: #64748b;
    font-weight: 600;
    letter-spacing: 0.04em;
    flex-wrap: wrap;
    justify-content: center;
  }

  .l-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .l-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .dot-blue {
    background: #38bdf8;
    box-shadow: 0 0 6px #38bdf8;
  }

  .dot-cyan {
    background: #06b6d4;
    box-shadow: 0 0 6px #06b6d4;
  }

  .dot-gold {
    background: #f59e0b;
    box-shadow: 0 0 6px #f59e0b;
  }

  .inspector-active {
    font-size: 11px;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 6px;
    animation: fadeIn 0.15s ease;
  }

  .ins-layer {
    color: #38bdf8;
    font-weight: 700;
  }

  .ins-name {
    color: #f59e0b;
    font-weight: 800;
  }

  .ins-desc {
    color: #94a3b8;
  }

  .ins-dot {
    color: #475569;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(2px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
