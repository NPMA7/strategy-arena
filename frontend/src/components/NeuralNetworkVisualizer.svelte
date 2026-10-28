<script>
  import { onMount, onDestroy } from 'svelte';
  import { arena } from '../lib/store.svelte.js';
  import { formatUSD } from '../lib/formatters.js';

  // Live Binance WebSocket tick references
  let btcPrice = $derived(arena.prices['BTCUSDT']?.price ?? 67840);
  let ethPrice = $derived(arena.prices['ETHUSDT']?.price ?? 3485);
  let solPrice = $derived(arena.prices['SOLUSDT']?.price ?? 182.5);

  // Neural Network Architecture Data
  // Radius of each neuron circle
  const R = 22;
  const ARROW_OFFSET = 4;

  const layers = [
    {
      id: 'input',
      name: 'Input layer',
      x: 75,
      nodes: [
        { id: 'in_0', label: 'BTC', sub: 'TICK', val: () => `$${formatUSD(btcPrice).replace('$', '')}`, type: 'input' },
        { id: 'in_1', label: 'ETH', sub: 'TICK', val: () => `$${formatUSD(ethPrice).replace('$', '')}`, type: 'input' },
        { id: 'in_2', label: 'SOL', sub: 'TICK', val: () => `$${formatUSD(solPrice).replace('$', '')}`, type: 'input' },
        { id: 'in_3', label: 'VOL', sub: 'ATR', val: () => '24h Vol', type: 'input' },
        { id: 'in_4', label: 'RSI', sub: 'OB', val: () => 'Depth', type: 'input' },
      ],
      yCoords: [110, 180, 250, 320, 390],
      stroke: '#38bdf8',
      fill: 'rgba(56, 189, 248, 0.08)',
      glow: '#38bdf8',
    },
    {
      id: 'h1',
      name: 'Hidden Layer 1',
      x: 225,
      nodes: [
        { id: 'h1_0', label: 'EMA', sub: 'Trend', desc: 'EMA 9/21 Trend Filter' },
        { id: 'h1_1', label: 'MACD', sub: 'Mom', desc: 'MACD Divergence' },
        { id: 'h1_2', label: 'ATR', sub: 'Vol', desc: 'ATR Volatility Squeeze' },
        { id: 'h1_3', label: 'BOLL', sub: 'Bands', desc: 'Bollinger Breakout' },
        { id: 'h1_4', label: 'GRID', sub: 'Micro', desc: 'High-Freq Spread Harvest' },
      ],
      yCoords: [110, 180, 250, 320, 390],
      stroke: '#06b6d4',
      fill: 'rgba(6, 182, 212, 0.08)',
      glow: '#06b6d4',
    },
    {
      id: 'h2',
      name: 'Hidden Layer 2',
      x: 365,
      nodes: [
        { id: 'h2_0', label: 'W₁', sub: '0.84', desc: 'Strategy Model Weight #1' },
        { id: 'h2_1', label: 'W₁₄', sub: '0.91', desc: 'Strategy Model Weight #14' },
        { id: 'h2_2', label: 'W₂₇', sub: '0.78', desc: 'Strategy Model Weight #27' },
        { id: 'h2_3', label: 'W₃₉', sub: '0.86', desc: 'Strategy Model Weight #39' },
        { id: 'h2_4', label: 'W₅₀', sub: '0.95', desc: 'Strategy Model Weight #50' },
      ],
      yCoords: [110, 180, 250, 320, 390],
      stroke: '#0ea5e9',
      fill: 'rgba(14, 165, 233, 0.08)',
      glow: '#0ea5e9',
    },
    {
      id: 'h3',
      name: 'Hidden Layer 3',
      x: 505,
      nodes: [
        { id: 'h3_0', label: 'NORM', sub: 'Z-Scr', desc: 'Statistical Normalization' },
        { id: 'h3_1', label: 'RISK', sub: 'Var', desc: 'Value-at-Risk Engine' },
        { id: 'h3_2', label: 'MTM', sub: '1s', desc: 'Mark-to-Market Live PnL' },
        { id: 'h3_3', label: 'FUND', sub: '8h', desc: 'Funding Rate Simulator' },
        { id: 'h3_4', label: 'LEVR', sub: '20x', desc: 'Leverage Risk Controller' },
      ],
      yCoords: [110, 180, 250, 320, 390],
      stroke: '#10b981',
      fill: 'rgba(16, 185, 129, 0.08)',
      glow: '#10b981',
    },
    {
      id: 'output',
      name: 'Output layer',
      x: 645,
      nodes: [
        { id: 'out_0', label: 'LONG', sub: 'FUTURES', tag: '20x LEV', desc: 'Binance Futures Long Position', type: 'output-long' },
        { id: 'out_1', label: 'SPOT', sub: 'CRYPTO', tag: '1x SPOT', desc: 'Binance Spot Execution', type: 'output-spot' },
        { id: 'out_2', label: 'SHORT', sub: 'FUTURES', tag: '20x LEV', desc: 'Binance Futures Short Position', type: 'output-short' },
      ],
      yCoords: [180, 250, 320],
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
    // Generate a new flowing pulse wave every 600ms
    pulseTimer = setInterval(() => {
      // Pick random nodes in each layer to form an active signal chain
      const n0 = Math.floor(Math.random() * 5);
      const n1 = Math.floor(Math.random() * 5);
      const n2 = Math.floor(Math.random() * 5);
      const n3 = Math.floor(Math.random() * 5);
      const n4 = Math.floor(Math.random() * 3);

      const chain = [
        `in_${n0}->h1_${n1}`,
        `h1_${n1}->h2_${n2}`,
        `h2_${n2}->h3_${n3}`,
        `h3_${n3}->out_${n4}`,
      ];

      // Random color: cyan, emerald, gold
      const colors = ['#38bdf8', '#10b981', '#f59e0b'];
      const chosenColor = colors[Math.floor(Math.random() * colors.length)];

      const newPulse = {
        id: Date.now() + Math.random(),
        chain,
        color: chosenColor,
        step: 0,
        t: 0,
      };

      activePulses = [...activePulses.slice(-5), newPulse];
    }, 700);

    // 60FPS animation loop for pulse particle movement
    let animFrame;
    function updatePulses() {
      animFrame = requestAnimationFrame(updatePulses);
      activePulses = activePulses
        .map((p) => {
          p.t += 0.035;
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
      <span class="mono header-tag">STRATEGY ARENA · NEURAL NETWORK INFERENCE</span>
    </div>
    <div class="top-badges mono">
      <span class="tag-live">LIVE TICK ENGINE</span>
      <span class="tag-latency">LATENCY &lt; 5MS</span>
    </div>
  </div>

  <!-- Main Responsive SVG Canvas -->
  <div class="svg-container">
    <svg viewBox="0 0 720 440" preserveAspectRatio="xMidYMid meet" class="nn-svg">
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
      </defs>

      <!-- 1. DIAGRAM TITLES & BRACKETS (Directly matching reference image) -->

      <!-- Column Title: Input layer -->
      <text x="75" y="58" text-anchor="middle" class="svg-col-title">Input layer</text>

      <!-- Bracket above Multiple hidden layers (x = 225 to x = 505) -->
      <path 
        d="M 225,64 L 225,50 L 357,50 L 365,42 L 373,50 L 505,50 L 505,64" 
        fill="none" 
        stroke="#64748b" 
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <text x="365" y="38" text-anchor="middle" class="svg-col-title">Multiple hidden layers</text>

      <!-- Column Title: Output layer -->
      <text x="645" y="58" text-anchor="middle" class="svg-col-title">Output layer</text>

      <!-- 2. SYNAPSE CONNECTIONS (Directed arrows between all layers) -->
      <g class="synapse-group">
        {#each synapses as syn (syn.id)}
          {@const isConnected = hoveredNodeId && (syn.fromId === hoveredNodeId || syn.toId === hoveredNodeId)}
          {@const markerName = syn.layerIdx === 0 ? 'arrow-blue' : syn.layerIdx === 1 ? 'arrow-cyan' : syn.layerIdx === 2 ? 'arrow-teal' : 'arrow-green'}
          <line
            x1={syn.sx}
            y1={syn.sy}
            x2={syn.ex}
            y2={syn.ey}
            class="synapse-line"
            class:synapse-active={isConnected}
            stroke={isConnected ? '#f59e0b' : syn.layerIdx === 0 ? '#38bdf8' : syn.layerIdx === 1 ? '#06b6d4' : syn.layerIdx === 2 ? '#0ea5e9' : '#10b981'}
            stroke-width={isConnected ? 2.2 : 1.1}
            stroke-opacity={isConnected ? 0.95 : 0.28}
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

      <!-- 4. NEURON CIRCLE NODES (With precise colors and typography) -->
      {#each layers as layer}
        <g class="layer-group">
          {#each layer.nodes as node, idx}
            {@const ny = layer.yCoords[idx]}
            {@const isHovered = hoveredNodeId === node.id}
            
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
                <circle cx={layer.x} cy={ny} r={R + 5} fill="none" stroke="#f59e0b" stroke-width="2" opacity="0.8"/>
              {/if}

              <!-- Main Neuron Ring (matching the circular aesthetic of reference) -->
              <circle
                cx={layer.x}
                cy={ny}
                r={R}
                fill={layer.id === 'output' ? 'rgba(245, 158, 11, 0.12)' : layer.id === 'input' ? 'rgba(56, 189, 248, 0.1)' : 'rgba(6, 182, 212, 0.08)'}
                stroke={isHovered ? '#ffffff' : layer.stroke}
                stroke-width="3"
                class="neuron-circle"
              />

              <!-- Inner Center Dot / Code Symbol -->
              <text 
                x={layer.x} 
                y={ny + 4} 
                text-anchor="middle" 
                class="node-label mono"
                fill={layer.id === 'output' ? '#fbbf24' : '#ffffff'}
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
          <span>INPUT (100+ BINANCE TICKS)</span>
        </div>
        <div class="l-item">
          <span class="l-dot dot-cyan"></span>
          <span>HIDDEN (50+ ALGO WEIGHTS)</span>
        </div>
        <div class="l-item">
          <span class="l-dot dot-gold"></span>
          <span>OUTPUT (SPOT 1X & FUTURES 20X)</span>
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
    min-height: 480px;
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

  .top-badges {
    display: flex;
    gap: 8px;
  }

  .tag-live {
    font-size: 10px;
    background: rgba(16, 185, 129, 0.12);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.25);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
  }

  .tag-latency {
    font-size: 10px;
    background: rgba(255, 255, 255, 0.05);
    color: #94a3b8;
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
  }

  /* SVG Container */
  .svg-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 0;
  }

  .nn-svg {
    width: 100%;
    height: auto;
    max-height: 400px;
    display: block;
    user-select: none;
  }

  /* Diagram Titles matching reference image */

  .svg-col-title {
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 12px;
    font-weight: 600;
    fill: #94a3b8;
  }

  /* Node Typography & Effects */
  .neuron-circle {
    transition: transform 0.15s ease, stroke 0.15s ease;
  }

  .node-label {
    font-size: 10px;
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
