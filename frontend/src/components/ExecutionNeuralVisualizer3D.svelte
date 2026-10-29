<script>
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';
  import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
  import { arena } from '../lib/store.svelte.js';
  import { STRATEGIES_88, FALLBACK_PAIRS_128 } from '../lib/strategies_data.js';

  let { activeTrade = null, onSelectPair = null, onClearTrade = null, onNewTrade = null } = $props();

  let containerElem = $state(null);
  let animFrameId = null;
  let isAutoRotate = $state(true);
  let pairCategory = $state('all'); // 'all', 'crypto', 'forex'
  let pairSearch = $state('');

  // Selected item state
  let selectedSymbol = $state(null);
  let selectedStrategyId = $state(null);
  let hoveredInfo = $state(null);
  let tooltipPos = $state({ x: 0, y: 0, visible: false });

  // Three.js instances
  let scene, camera, renderer, controls;
  let raycaster, mouse;
  let inputMeshGroup, stratMeshGroup, engineMeshGroup;
  let baseSynapsesMesh, activeSynapsesMesh;
  let activePulses = [];
  let pulsePointsGeometry, pulsePointsMaterial, pulsePointsMesh;
  let resizeObserver = null;

  // Deduplication state for live realtime detection
  let knownPositionKeys = new Set();
  let knownEventKeys = new Set();
  let isDetectionReady = false;

  // Active Symbol resolution: from active trade prop or manual selection
  let activeSymbol = $derived.by(() => {
    if (activeTrade && activeTrade.symbol) return activeTrade.symbol;
    return selectedSymbol;
  });

  // Active Strategy resolution
  let activeStratId = $derived.by(() => {
    if (activeTrade && activeTrade.strategy) return activeTrade.strategy;
    return selectedStrategyId;
  });

  // -------------------------------------------------------------
  // 1. DATA PREPARATION FOR 3D LAYERS (KOTAK / PROPOSIONAL 1:1)
  // Layer 1: Input (16 kesamping x 8 kebawah = 128 Node)
  // Layer 2: Strategi (11 kesamping x 8 kebawah = 88 Node)
  // Layer 3: Engines (Formasi Kotak Diamond 150 x 150)
  // -------------------------------------------------------------
  const LAYER_X_INPUT = -260;
  const LAYER_X_STRAT = 0;
  const LAYER_X_ENGINE = 260;

  // Layer 1: Input 128 Pairs in 16 Columns (Z) x 8 Rows (Y)
  // 100 Crypto Pairs + 28 Forex & Metals Pairs = TOTAL 128 PAIR RIIL (Tanpa Dummy FOREX_28..31)
  let input3DNodes = $derived.by(() => {
    let list = (arena.pairs && arena.pairs.length >= 100) ? arena.pairs : FALLBACK_PAIRS_128;
    const crypto = list.filter(p => p.category === 'crypto' || (!p.symbol.startsWith('XAU') && !p.symbol.startsWith('XAG') && !p.symbol.startsWith('XTI') && p.symbol.endsWith('USDT')));
    const forex = list.filter(p => p.category === 'forex' || (p.symbol.length === 6 && !p.symbol.endsWith('USDT') && !p.symbol.endsWith('USDC')) || p.symbol === 'XAUUSD' || p.symbol === 'XAGUSD' || p.symbol === 'XTIUSD');

    const cSlice = crypto.length >= 100 ? crypto : FALLBACK_PAIRS_128.filter(p => p.category === 'crypto');
    const fSlice = forex.length >= 28 ? forex : FALLBACK_PAIRS_128.filter(p => p.category === 'forex');

    // Tepat 128 pair riil (100 Crypto + 28 Forex)
    const allPairs = [...cSlice.slice(0, 100), ...fSlice.slice(0, 28)];

    const nodes = [];
    const q = pairSearch.toUpperCase().trim();

    // 16 Kolom ke samping (Z: -115 s/d +115 = lebar 230)
    // 8 Baris ke bawah (Y: +115 s/d -115 = tinggi 230) -> Kotak 1:1 Presisi
    for (let col = 0; col < 16; col++) {
      const z = -115 + (col / 15) * 230;

      for (let row = 0; row < 8; row++) {
        const y = 115 - (row / 7) * 230;
        const pairIdx = col * 8 + row;
        const p = allPairs[pairIdx] || allPairs[0];

        const isForex = (p.category === 'forex' || pairIdx >= 100);
        const sym = p.symbol || '';
        const base = p.base || sym.replace('USDT', '').replace('USD', '') || sym;
        const isMatched = activeSymbol ? (activeSymbol === sym) : false;
        const isSearchHit = q ? (sym.includes(q) || base.includes(q)) : false;

        let isDimmed = false;
        if (pairCategory === 'crypto' && isForex) isDimmed = true;
        if (pairCategory === 'forex' && !isForex) isDimmed = true;
        if (q && !isSearchHit) isDimmed = true;

        nodes.push({
          id: `in_${col}_${row}`,
          type: 'input',
          symbol: sym,
          base: base.slice(0, 5),
          name: p.name || sym,
          category: isForex ? 'forex' : 'crypto',
          pos: new THREE.Vector3(LAYER_X_INPUT, y, z),
          col,
          row,
          isActive: isMatched,
          isSearchHit,
          isDimmed,
          price: arena.prices[sym]?.price ?? arena.prices[sym] ?? null
        });
      }
    }

    return nodes;
  });

  // Layer 2: 88 Quantitative Strategies in 11 Columns (Z) x 8 Rows (Y)
  // 11 Kolom ke samping (Z: -105 s/d +105 = lebar 210)
  // 8 Baris ke bawah (Y: +105 s/d -105 = tinggi 210) -> Kotak 1:1 Presisi
  let strat3DNodes = $derived.by(() => {
    const all = STRATEGIES_88;
    const nodes = [];

    for (let col = 0; col < 11; col++) {
      const z = -105 + (col / 10) * 210;

      for (let row = 0; row < 8; row++) {
        const y = 105 - (row / 7) * 210;
        const sIdx = col * 8 + row;
        const s = all[sIdx] || { id: `strat_${sIdx}`, name: `Strategy ${sIdx}`, family: 'Quant', code: 'QNT' };
        const isMatched = activeStratId ? (s.id.toLowerCase() === activeStratId.toLowerCase()) : false;

        nodes.push({
          id: `strat_${col}_${row}`,
          type: 'strategy',
          stratId: s.id,
          name: s.name,
          family: s.family,
          code: s.code,
          is_forex: s.is_forex,
          pos: new THREE.Vector3(LAYER_X_STRAT, y, z),
          col,
          row,
          isActive: isMatched
        });
      }
    }

    return nodes;
  });

  // Layer 3: 5 Execution Engines in Proportional Diamond/Matrix (150 x 150)
  const engine3DNodes = [
    { id: 'out_fut_l',  label: 'FUT·L',  sub: 'FUTURES',   tag: '20x LEV',    pos: new THREE.Vector3(LAYER_X_ENGINE, 75, 0),    type: 'engine', engineType: 'futures-long',  isCryptoOnly: true, desc: 'Binance Futures Long Position (1-20x)' },
    { id: 'out_spot',   label: 'SPOT',   sub: 'CRYPTO',    tag: '1x SPOT',    pos: new THREE.Vector3(LAYER_X_ENGINE, 0, 0),     type: 'engine', engineType: 'spot',          isCryptoOnly: true, desc: 'Binance Spot Execution (Tanpa Leverage)' },
    { id: 'out_fut_s',  label: 'FUT·S',  sub: 'FUTURES',   tag: '20x LEV',    pos: new THREE.Vector3(LAYER_X_ENGINE, -75, 0),   type: 'engine', engineType: 'futures-short', isCryptoOnly: true, desc: 'Binance Futures Short Position (1-20x)' },
    { id: 'out_fx_buy', label: 'FX·BUY', sub: 'MT5 DIRECT', tag: 'LOT SIZING', pos: new THREE.Vector3(LAYER_X_ENGINE, 0, -75),   type: 'engine', engineType: 'forex-buy',     isForexOnly: true,  desc: 'MetaTrader 5 Direct Buy Order' },
    { id: 'out_fx_sel', label: 'FX·SEL', sub: 'MT5 DIRECT', tag: 'LOT SIZING', pos: new THREE.Vector3(LAYER_X_ENGINE, 0, 75),    type: 'engine', engineType: 'forex-sell',    isForexOnly: true,  desc: 'MetaTrader 5 Direct Sell Order' },
  ];

  // Map of all node objects by ID for raycasting and inspection
  let nodeObjectsMap = new Map();

  // -------------------------------------------------------------
  // 2. THREE.JS INITIALIZATION
  // -------------------------------------------------------------
  function initThreeScene() {
    if (!containerElem) return;

    const width = containerElem.clientWidth || 1100;
    const height = containerElem.clientHeight || 700;

    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x04070d);
    scene.fog = new THREE.FogExp2(0x04070d, 0.00065);

    // Camera
    camera = new THREE.PerspectiveCamera(46, width / height, 1, 3500);
    camera.position.set(380, 200, 380);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    containerElem.appendChild(renderer.domElement);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = isAutoRotate;
    controls.autoRotateSpeed = 0.55;
    controls.minDistance = 140;
    controls.maxDistance = 1400;
    controls.target.set(0, 0, 0);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 2.2);
    dirLight1.position.set(220, 320, 420);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xf59e0b, 1.4);
    dirLight2.position.set(-220, -220, -320);
    scene.add(dirLight2);

    const pointLight = new THREE.PointLight(0x10b981, 1.6, 900);
    pointLight.position.set(0, 60, 0);
    scene.add(pointLight);

    // Raycaster & Mouse
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2(-999, -999);

    // Build Scene Meshes
    build3DNodes();
    buildBaseSynapses();
    buildPulseParticleSystem();
    buildLayerPlatesAndLabels();

    // Event Listeners
    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('pointerdown', onPointerDown);

    // ResizeObserver for robust layout adaptation
    resizeObserver = new ResizeObserver(() => {
      onWindowResize();
    });
    resizeObserver.observe(containerElem);

    // Start 60-120 FPS Loop
    renderLoop();
  }

  // -------------------------------------------------------------
  // 3. BUILD 3D NODES
  // -------------------------------------------------------------
  function build3DNodes() {
    inputMeshGroup = new THREE.Group();
    stratMeshGroup = new THREE.Group();
    engineMeshGroup = new THREE.Group();
    nodeObjectsMap.clear();

    const sphereGeom = new THREE.SphereGeometry(3.6, 16, 16);
    const engineGeom = new THREE.SphereGeometry(9.0, 24, 24);
    const engineRingGeom = new THREE.TorusGeometry(14.0, 0.9, 8, 36);

    // Materials
    const cryptoMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.65, roughness: 0.25, metalness: 0.7 });
    const forexMat = new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x059669, emissiveIntensity: 0.65, roughness: 0.25, metalness: 0.7 });
    const stratMat = new THREE.MeshStandardMaterial({ color: 0x818cf8, emissive: 0x4f46e5, emissiveIntensity: 0.65, roughness: 0.25, metalness: 0.7 });

    // 1. Multi-Asset Input Nodes
    input3DNodes.forEach(node => {
      const mat = (node.category === 'forex' ? forexMat : cryptoMat).clone();
      const mesh = new THREE.Mesh(sphereGeom, mat);
      mesh.position.copy(node.pos);
      mesh.userData = { nodeData: node };
      inputMeshGroup.add(mesh);
      nodeObjectsMap.set(node.id, mesh);
    });

    // 2. Quantitative Strategy Nodes
    strat3DNodes.forEach(node => {
      const mat = stratMat.clone();
      const mesh = new THREE.Mesh(sphereGeom, mat);
      mesh.position.copy(node.pos);
      mesh.userData = { nodeData: node };
      stratMeshGroup.add(mesh);
      nodeObjectsMap.set(node.id, mesh);
    });

    // 3. Execution Engine Nodes
    engine3DNodes.forEach(node => {
      let color = 0xf59e0b;
      let emissive = 0xd97706;
      if (node.engineType === 'forex-buy' || node.engineType === 'forex-sell') {
        color = 0x10b981;
        emissive = 0x059669;
      } else if (node.engineType === 'spot') {
        // SPOT: Rose / Red (Swapped with FUT·S)
        color = 0xf43f5e;
        emissive = 0xe11d48;
      } else if (node.engineType === 'futures-short' || node.engineType === 'futures-long') {
        // FUT·S & FUT·L: Amber / Orange
        color = 0xf59e0b;
        emissive = 0xd97706;
      }

      const mat = new THREE.MeshStandardMaterial({ color, emissive, emissiveIntensity: 0.9, roughness: 0.2, metalness: 0.8 });
      const mesh = new THREE.Mesh(engineGeom, mat);
      mesh.position.copy(node.pos);
      mesh.userData = { nodeData: node };

      // Outer Torus Ring
      const ringMat = new THREE.MeshBasicMaterial({ color, wireframe: true, transparent: true, opacity: 0.65 });
      const ringMesh = new THREE.Mesh(engineRingGeom, ringMat);
      ringMesh.rotation.x = Math.PI / 2;
      mesh.add(ringMesh);

      engineMeshGroup.add(mesh);
      nodeObjectsMap.set(node.id, mesh);
    });

    scene.add(inputMeshGroup);
    scene.add(stratMeshGroup);
    scene.add(engineMeshGroup);
  }

  // -------------------------------------------------------------
  // 4. BUILD 3D SYNAPSE LINES (HIGH-DENSITY LATTICE - PROPORTIONAL)
  // -------------------------------------------------------------
  function buildBaseSynapses() {
    if (baseSynapsesMesh) {
      scene.remove(baseSynapsesMesh);
      baseSynapsesMesh.geometry.dispose();
    }

    const linePoints = [];

    // 1. Input -> Strategy:
    // Kedua layer sama-sama memiliki 8 baris (Y) presisi!
    // Sambungkan setiap node input ke strategi di baris yang sama dan baris terdekat
    input3DNodes.forEach(pNode => {
      const sameRowStrats = strat3DNodes.filter(s => Math.abs(s.row - pNode.row) <= 1);
      const sorted = [...sameRowStrats].sort((a, b) => Math.abs(a.pos.z - pNode.pos.z) - Math.abs(b.pos.z - pNode.pos.z));
      sorted.slice(0, 2).forEach(sNode => {
        linePoints.push(pNode.pos.x, pNode.pos.y, pNode.pos.z);
        linePoints.push(sNode.pos.x, sNode.pos.y, sNode.pos.z);
      });
    });

    // 2. Inter-column Strategy Synapses (Volumetric Lattice across 11 Columns)
    for (let col = 0; col < 10; col++) {
      const colA = strat3DNodes.filter(s => s.col === col);
      const colB = strat3DNodes.filter(s => s.col === col + 1);

      colA.forEach(sA => {
        const targets = colB.filter(sB => Math.abs(sB.row - sA.row) <= 1);
        targets.forEach(sB => {
          linePoints.push(sA.pos.x, sA.pos.y, sA.pos.z);
          linePoints.push(sB.pos.x, sB.pos.y, sB.pos.z);
        });
      });
    }

    // 3. Strategy -> Engine (Setiap strategi kuantitatif terhubung ke 2 engine terdekat)
    strat3DNodes.forEach(sNode => {
      const sorted = [...engine3DNodes].sort((a, b) => a.pos.distanceTo(sNode.pos) - b.pos.distanceTo(sNode.pos));
      sorted.slice(0, 2).forEach(e => {
        linePoints.push(sNode.pos.x, sNode.pos.y, sNode.pos.z);
        linePoints.push(e.pos.x, e.pos.y, e.pos.z);
      });
    });

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(linePoints, 3));

    const mat = new THREE.LineBasicMaterial({
      color: 0x0ea5e9,
      transparent: true,
      opacity: 0.12,
      blending: THREE.AdditiveBlending
    });

    baseSynapsesMesh = new THREE.LineSegments(geom, mat);
    scene.add(baseSynapsesMesh);
  }

  // -------------------------------------------------------------
  // 5. HIGHLIGHT ACTIVE 3D ROUTE (PAIR -> STRATEGY -> ENGINE)
  // -------------------------------------------------------------
  function updateActiveSynapseHighlights() {
    if (!scene) return;
    if (activeSynapsesMesh) {
      scene.remove(activeSynapsesMesh);
      activeSynapsesMesh.geometry.dispose();
      activeSynapsesMesh = null;
    }

    let inNode = null;
    let sNode = null;
    let eNode = null;

    if (activeSymbol) {
      inNode = input3DNodes.find(n => n.symbol === activeSymbol);
    }
    if (activeStratId) {
      sNode = strat3DNodes.find(s => s.stratId.toLowerCase() === activeStratId.toLowerCase());
    }

    if (activeTrade) {
      const mode = (activeTrade.mode || (activeTrade.symbol?.endsWith('USDT') ? 'spot' : 'forex')).toLowerCase();
      const isLong = (activeTrade.side === 1 || activeTrade.side_label === 'LONG');
      if (mode === 'forex') {
        eNode = engine3DNodes.find(e => e.id === (isLong ? 'out_fx_buy' : 'out_fx_sel'));
      } else if (mode === 'futures') {
        eNode = engine3DNodes.find(e => e.id === (isLong ? 'out_fut_l' : 'out_fut_s'));
      } else {
        eNode = engine3DNodes.find(e => e.id === 'out_spot');
      }
    }

    const highlightPoints = [];

    // Case 1: Specific trade audit route (inNode -> sNode -> eNode)
    if (inNode && sNode && eNode) {
      highlightPoints.push(inNode.pos.x, inNode.pos.y, inNode.pos.z);
      highlightPoints.push(sNode.pos.x, sNode.pos.y, sNode.pos.z);

      highlightPoints.push(sNode.pos.x, sNode.pos.y, sNode.pos.z);
      highlightPoints.push(eNode.pos.x, eNode.pos.y, eNode.pos.z);
    }
    // Case 2: Pair selected -> connect to all 88 strategies then to engines
    else if (inNode) {
      strat3DNodes.forEach(s => {
        highlightPoints.push(inNode.pos.x, inNode.pos.y, inNode.pos.z);
        highlightPoints.push(s.pos.x, s.pos.y, s.pos.z);
      });
      // Seluruh 88 strategi kuantitatif terhubung serentak ke output engines tanpa kecuali!
      const targetEngines = inNode.category === 'forex'
        ? engine3DNodes.filter(e => e.id === 'out_fx_buy' || e.id === 'out_fx_sel')
        : engine3DNodes.filter(e => e.id === 'out_fut_l' || e.id === 'out_spot' || e.id === 'out_fut_s');

      strat3DNodes.forEach(s => {
        targetEngines.forEach(e => {
          highlightPoints.push(s.pos.x, s.pos.y, s.pos.z);
          highlightPoints.push(e.pos.x, e.pos.y, e.pos.z);
        });
      });
    }
    // Case 3: Strategy selected -> SEMUA 128 pair terhubung serentak ke strategi ini!
    else if (sNode) {
      input3DNodes.forEach(p => {
        highlightPoints.push(p.pos.x, p.pos.y, p.pos.z);
        highlightPoints.push(sNode.pos.x, sNode.pos.y, sNode.pos.z);
      });
      engine3DNodes.forEach(e => {
        highlightPoints.push(sNode.pos.x, sNode.pos.y, sNode.pos.z);
        highlightPoints.push(e.pos.x, e.pos.y, e.pos.z);
      });
    }

    if (highlightPoints.length > 0) {
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.Float32BufferAttribute(highlightPoints, 3));
      const mat = new THREE.LineBasicMaterial({
        color: activeTrade ? 0xfbbf24 : (inNode?.category === 'forex' ? 0x10b981 : 0x38bdf8),
        transparent: true,
        opacity: 0.94,
        linewidth: 2.2,
        blending: THREE.AdditiveBlending
      });
      activeSynapsesMesh = new THREE.LineSegments(geom, mat);
      scene.add(activeSynapsesMesh);
    }

    // Node glowing scale and emissive highlight
    nodeObjectsMap.forEach((mesh, id) => {
      const isPrimary = (inNode && id === inNode.id) || (sNode && id === sNode.id) || (eNode && id === eNode.id);
      let isSecondary = false;
      if (sNode) {
        // Strategy clicked -> SEMUA 128 input pairs dan seluruh engine menyala serentak!
        isSecondary = (id.startsWith('pair_') || id.startsWith('out_'));
      } else if (inNode) {
        // Pair clicked -> seluruh 88 strategi kuantitatif dan target engine menyala serentak!
        const isTargetEngine = inNode.category === 'forex'
          ? (id === 'out_fx_buy' || id === 'out_fx_sel')
          : (id === 'out_fut_l' || id === 'out_spot' || id === 'out_fut_s');
        isSecondary = (id.startsWith('s_') || isTargetEngine);
      }

      if (isPrimary) {
        mesh.scale.set(1.5, 1.5, 1.5);
        if (mesh.material.emissive) mesh.material.emissiveIntensity = 1.8;
      } else if (isSecondary) {
        mesh.scale.set(1.15, 1.15, 1.15);
        if (mesh.material.emissive) mesh.material.emissiveIntensity = 1.2;
      } else {
        mesh.scale.set(1.0, 1.0, 1.0);
        if (mesh.material.emissive) mesh.material.emissiveIntensity = (sNode || inNode) ? 0.35 : 0.65;
      }
    });
  }

  // -------------------------------------------------------------
  // 6. 3D TRAVELING PULSES & PARTICLES
  // -------------------------------------------------------------
  function buildPulseParticleSystem() {
    pulsePointsGeometry = new THREE.BufferGeometry();
    const maxParticles = 20;
    const positions = new Float32Array(maxParticles * 3);
    const colors = new Float32Array(maxParticles * 3);

    pulsePointsGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    pulsePointsGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    pulsePointsMaterial = new THREE.PointsMaterial({
      size: 9.5,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending
    });

    pulsePointsMesh = new THREE.Points(pulsePointsGeometry, pulsePointsMaterial);
    scene.add(pulsePointsMesh);
  }

  function fireTrade3DPulse(trade) {
    if (!trade || !trade.symbol) return;
    const sym = trade.symbol.toUpperCase();
    const strat = (trade.strategy || trade.strategy_name || '').toLowerCase();
    const isLong = (trade.side === 1 || trade.side_label === 'LONG');
    const mode = (trade.mode || (sym.endsWith('USDT') ? 'spot' : 'forex')).toLowerCase();

    const inNode = input3DNodes.find(n => n.symbol === sym) || input3DNodes[0];
    const sNode = strat3DNodes.find(s => s.stratId.toLowerCase() === strat) || strat3DNodes[0];
    let eNode;
    if (mode === 'forex') {
      eNode = engine3DNodes.find(e => e.id === (isLong ? 'out_fx_buy' : 'out_fx_sel'));
    } else if (mode === 'futures') {
      eNode = engine3DNodes.find(e => e.id === (isLong ? 'out_fut_l' : 'out_fut_s'));
    } else {
      eNode = engine3DNodes.find(e => e.id === 'out_spot');
    }

    if (!inNode || !sNode || !eNode) return;

    const pulse = {
      p1: inNode.pos,
      p2: sNode.pos,
      p3: eNode.pos,
      t: 0,
      step: 0,
      color: new THREE.Color(isLong ? 0x10b981 : 0xf43f5e)
    };

    activePulses.push(pulse);
    if (activePulses.length > 10) {
      activePulses = activePulses.slice(-10);
    }
  }

  // -------------------------------------------------------------
  // 7. LAYER FLOATING TITLES & PLATES
  // -------------------------------------------------------------
  function makeTextSprite(message, color = '#38bdf8', fontSize = 36) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, 512, 128);

    ctx.font = `bold ${fontSize}px Inter, sans-serif`;
    ctx.fillStyle = color;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(message, 256, 64);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.9 });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(130, 32, 1);
    return sprite;
  }

  function buildLayerPlatesAndLabels() {
    // 1. Layer Labels
    const inTitle = makeTextSprite('MULTI-ASSET INPUT', '#38bdf8', 30);
    inTitle.position.set(LAYER_X_INPUT, 150, 0);
    scene.add(inTitle);

    const stratTitle = makeTextSprite('QUANT STRATEGIES ', '#818cf8', 30);
    stratTitle.position.set(LAYER_X_STRAT, 145, 0);
    scene.add(stratTitle);

    const outTitle = makeTextSprite('EXECUTION ENGINES', '#f59e0b', 30);
    outTitle.position.set(LAYER_X_ENGINE, 130, 0);
    scene.add(outTitle);

    // 2. Engine Labels
    engine3DNodes.forEach(e => {
      let lblColor = '#fbbf24';
      if (e.engineType.includes('forex')) {
        lblColor = '#34d399';
      } else if (e.engineType === 'spot') {
        lblColor = '#f43f5e';
      }
      const lbl = makeTextSprite(e.label, lblColor, 36);
      lbl.scale.set(60, 15, 1);
      lbl.position.set(e.pos.x + 25, e.pos.y, e.pos.z);
      scene.add(lbl);
    });
  }

  // -------------------------------------------------------------
  // 8. INTERACTION & RAYCASTING
  // -------------------------------------------------------------
  function onPointerMove(e) {
    if (!containerElem || !renderer || !camera) return;
    const rect = containerElem.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const allMeshList = [...inputMeshGroup.children, ...stratMeshGroup.children, ...engineMeshGroup.children];
    const intersects = raycaster.intersectObjects(allMeshList);

    if (intersects.length > 0) {
      const mesh = intersects[0].object;
      const data = mesh.userData.nodeData;
      if (data) {
        hoveredInfo = data;
        tooltipPos = {
          x: e.clientX - rect.left + 16,
          y: e.clientY - rect.top + 16,
          visible: true
        };
        document.body.style.cursor = 'pointer';
        return;
      }
    }

    hoveredInfo = null;
    tooltipPos.visible = false;
    document.body.style.cursor = 'default';
  }

  function onPointerDown(e) {
    if (hoveredInfo) {
      if (hoveredInfo.type === 'input') {
        selectedSymbol = (selectedSymbol === hoveredInfo.symbol ? null : hoveredInfo.symbol);
        selectedStrategyId = null;
        if (onSelectPair) onSelectPair(selectedSymbol);
      } else if (hoveredInfo.type === 'strategy') {
        selectedStrategyId = (selectedStrategyId === hoveredInfo.stratId ? null : hoveredInfo.stratId);
        selectedSymbol = null;
      }
      updateActiveSynapseHighlights();
    }
  }

  function onWindowResize() {
    if (!containerElem || !renderer || !camera) return;
    const width = containerElem.clientWidth || 1100;
    const height = containerElem.clientHeight || 700;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  export function resetCamera() {
    if (!camera || !controls) return;
    camera.position.set(380, 200, 380);
    controls.target.set(0, 0, 0);
    controls.update();
  }

  export function toggleAutoRotate() {
    isAutoRotate = !isAutoRotate;
    if (controls) controls.autoRotate = isAutoRotate;
  }

  // -------------------------------------------------------------
  // 9. ANIMATION LOOP (60 - 120 FPS)
  // -------------------------------------------------------------
  function renderLoop() {
    animFrameId = requestAnimationFrame(renderLoop);

    if (controls) controls.update();

    // Pulse animation update
    if (activePulses.length > 0 && pulsePointsGeometry) {
      const posAttr = pulsePointsGeometry.attributes.position;
      const colAttr = pulsePointsGeometry.attributes.color;

      for (let i = 0; i < activePulses.length; i++) {
        const p = activePulses[i];
        p.t += 0.024;
        if (p.t >= 1) {
          p.t = 0;
          p.step += 1;
        }

        let curPos = new THREE.Vector3();
        if (p.step === 0) {
          curPos.lerpVectors(p.p1, p.p2, p.t);
        } else if (p.step === 1) {
          curPos.lerpVectors(p.p2, p.p3, p.t);
        }

        posAttr.setXYZ(i, curPos.x, curPos.y, curPos.z);
        colAttr.setXYZ(i, p.color.r, p.color.g, p.color.b);
      }

      // Hide inactive slots
      for (let i = activePulses.length; i < 20; i++) {
        posAttr.setXYZ(i, 9999, 9999, 9999);
      }

      posAttr.needsUpdate = true;
      colAttr.needsUpdate = true;
      activePulses = activePulses.filter(p => p.step < 2);
    }

    if (renderer && scene && camera) {
      renderer.render(scene, camera);
    }
  }

  // Real-time Event Monitor for incoming trades
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
          const tObj = {
            mode: e.mode,
            symbol: e.symbol,
            strategy: strat,
            side: isShort ? -1 : 1,
            opened_at: e.ts,
            message: e.message
          };
          fireTrade3DPulse(tObj);
          if (onNewTrade) onNewTrade(tObj);
          break;
        }
      }
    }

    // Deteksi Trade Baru Terbuka dari Posisi Aktif
    for (const p of currentPositions) {
      const key = `${p.mode}_${p.strategy}_${p.symbol}_${p.opened_at}`;
      if (!knownPositionKeys.has(key)) {
        knownPositionKeys.add(key);
        const eventKey = `${p.mode}_${p.symbol}_${p.opened_at}`;
        if (!knownEventKeys.has(eventKey)) {
          knownEventKeys.add(eventKey);
          fireTrade3DPulse(p);
          if (onNewTrade) onNewTrade(p);
          break;
        }
      }
    }
  });

  // Reactivity: Rebuild / Update highlights when activeTrade changes
  $effect(() => {
    if (activeTrade) {
      updateActiveSynapseHighlights();
      fireTrade3DPulse(activeTrade);
    } else {
      updateActiveSynapseHighlights();
    }
  });

  $effect(() => {
    // When pair search or category changes, update opacity of node meshes
    inputMeshGroup?.children.forEach(mesh => {
      const node = mesh.userData.nodeData;
      if (node) {
        let isDimmed = false;
        if (pairCategory === 'crypto' && node.category === 'forex') isDimmed = true;
        if (pairCategory === 'forex' && node.category === 'crypto') isDimmed = true;
        if (pairSearch) {
          const q = pairSearch.toUpperCase().trim();
          if (!node.symbol.includes(q) && !node.base.includes(q)) isDimmed = true;
        }
        mesh.material.opacity = isDimmed ? 0.22 : 1.0;
        mesh.material.transparent = isDimmed;
      }
    });
  });

  onMount(() => {
    initThreeScene();
  });

  onDestroy(() => {
    if (animFrameId) cancelAnimationFrame(animFrameId);
    if (resizeObserver) resizeObserver.disconnect();
    if (renderer) {
      renderer.dispose();
      renderer.domElement.remove();
    }
    controls?.dispose();
    scene?.clear();
  });
</script>

<div class="visualizer-3d-root">
  <!-- Top 3D Control Bar -->
  <div class="matrix-top-bar mono">
    <div class="top-left">
      <span class="pulse-emerald"></span>
      <span class="title-3d">3D NEURAL MATRIX HOLOGRAM</span>
      <span class="sub-3d">Tri-Market Deep Quantum Mesh (WebGL Hardware-Accelerated)</span>
    </div>

    <div class="top-right">
      <div class="category-pills">
        <button
          type="button"
          class="cat-pill {pairCategory === 'all' ? 'active' : ''}"
          onclick={() => pairCategory = 'all'}
        >
          Semua
        </button>
        <button
          type="button"
          class="cat-pill {pairCategory === 'crypto' ? 'active text-cyan' : ''}"
          onclick={() => pairCategory = 'crypto'}
        >
          Crypto
        </button>
        <button
          type="button"
          class="cat-pill {pairCategory === 'forex' ? 'active text-emerald' : ''}"
          onclick={() => pairCategory = 'forex'}
        >
          Forex & Metals
        </button>
      </div>

      <div class="control-actions">
        <button
          type="button"
          class="action-btn {isAutoRotate ? 'active' : ''}"
          onclick={toggleAutoRotate}
          title="Putar kamera secara otomatis"
        >
          {isAutoRotate ? '⏸ Pause Rotasi' : '▶ Putar Otomatis'}
        </button>
        <button
          type="button"
          class="action-btn"
          onclick={resetCamera}
          title="Kembalikan posisi sudut kamera ke awal"
        >
          ↺ Reset Sudut
        </button>
      </div>
    </div>
  </div>

  <!-- 3D WebGL Canvas Container -->
  <div class="webgl-container" bind:this={containerElem}>
    <!-- Floating Interactive HUD Tooltip -->
    {#if tooltipPos.visible && hoveredInfo}
      <div
        class="matrix-hud-tooltip mono"
        style="left: {tooltipPos.x}px; top: {tooltipPos.y}px;"
      >
        {#if hoveredInfo.type === 'input'}
          <div class="hud-tag {hoveredInfo.category}">
            {hoveredInfo.category === 'forex' ? 'FOREX / METALS' : 'CRYPTO SPOT & FUT'}
          </div>
          <div class="hud-main">{hoveredInfo.symbol}</div>
          <div class="hud-sub">{hoveredInfo.name}</div>
          {#if hoveredInfo.price}
            <div class="hud-price">${Number(hoveredInfo.price).toFixed(2)}</div>
          {/if}
          <div class="hud-hint">Klik untuk sorot sinapsis 3D</div>
        {:else if hoveredInfo.type === 'strategy'}
          <div class="hud-tag quant">QUANT STRATEGY MODEL</div>
          <div class="hud-main">{hoveredInfo.name}</div>
          <div class="hud-sub">Family: {hoveredInfo.family} · Code: {hoveredInfo.code}</div>
          <div class="hud-hint">Klik untuk melihat koneksi pair & output</div>
        {:else if hoveredInfo.type === 'engine'}
          <div class="hud-tag engine">{hoveredInfo.sub}</div>
          <div class="hud-main">{hoveredInfo.label}</div>
          <div class="hud-sub">{hoveredInfo.desc}</div>
        {/if}
      </div>
    {/if}

    <!-- 3D Navigation Guide Pill in Bottom Left -->
    <div class="nav-guide-pill mono">
      <span>🖱 Drag Kiri: Putar 3D</span>
      <span class="sep">·</span>
      <span>Scroll: Zoom In/Out</span>
      <span class="sep">·</span>
      <span>Drag Kanan: Geser Posisi</span>
    </div>
  </div>
</div>

<style>
  .visualizer-3d-root {
    position: relative;
    width: 100%;
    background: #04070d;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
  }

  .matrix-top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 18px;
    background: rgba(8, 12, 20, 0.95);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    flex-wrap: wrap;
    gap: 12px;
  }

  .top-left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .pulse-emerald {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 10px #10b981;
    animation: pulse 1.8s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.85); }
  }

  .title-3d {
    font-size: 13px;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: 0.04em;
  }

  .sub-3d {
    font-size: 11px;
    color: #64748b;
    margin-left: 6px;
  }

  .top-right {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }

  .category-pills {
    display: flex;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 2px;
    gap: 2px;
  }

  .cat-pill {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .cat-pill:hover {
    color: #f1f5f9;
    background: rgba(255, 255, 255, 0.05);
  }

  .cat-pill.active {
    background: #1e293b;
    color: #ffffff;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  }

  .control-actions {
    display: flex;
    gap: 6px;
  }

  .action-btn {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 700;
    padding: 5px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .action-btn:hover {
    background: #334155;
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.2);
  }

  .action-btn.active {
    background: rgba(14, 165, 233, 0.2);
    border-color: #0ea5e9;
    color: #38bdf8;
  }

  .webgl-container {
    position: relative;
    width: 100%;
    height: 680px;
    overflow: hidden;
  }

  /* Matrix HUD Tooltip */
  .matrix-hud-tooltip {
    position: absolute;
    pointer-events: none;
    z-index: 30;
    background: rgba(10, 15, 26, 0.95);
    border: 1px solid rgba(56, 189, 248, 0.4);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), 0 0 15px rgba(56, 189, 248, 0.25);
    border-radius: 8px;
    padding: 10px 14px;
    min-width: 180px;
    backdrop-filter: blur(8px);
    transform: translate(0, 0);
  }

  .hud-tag {
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 2px 6px;
    border-radius: 3px;
    display: inline-block;
    margin-bottom: 4px;
  }

  .hud-tag.crypto {
    background: rgba(56, 189, 248, 0.2);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
  }

  .hud-tag.forex {
    background: rgba(16, 185, 129, 0.2);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .hud-tag.quant {
    background: rgba(129, 140, 248, 0.2);
    color: #a5b4fc;
    border: 1px solid rgba(129, 140, 248, 0.3);
  }

  .hud-tag.engine {
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .hud-main {
    font-size: 15px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 2px;
  }

  .hud-sub {
    font-size: 11px;
    color: #94a3b8;
    margin-bottom: 4px;
  }

  .hud-price {
    font-size: 13px;
    font-weight: 800;
    color: #38bdf8;
  }

  .hud-hint {
    font-size: 9px;
    color: #64748b;
    margin-top: 6px;
    border-top: 1px dashed rgba(255, 255, 255, 0.1);
    padding-top: 4px;
  }

  .nav-guide-pill {
    position: absolute;
    bottom: 14px;
    left: 16px;
    background: rgba(6, 9, 16, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 10.5px;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 8px;
    backdrop-filter: blur(6px);
    pointer-events: none;
    z-index: 10;
  }

  .nav-guide-pill .sep {
    color: #475569;
  }
</style>
