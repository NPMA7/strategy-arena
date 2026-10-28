<script>
  import { onMount, onDestroy } from 'svelte';
  import * as THREE from 'three';

  let containerRef = $state(null);
  let canvasRef = $state(null);
  let animId = null;
  let renderer = null;
  let scene = null;
  let camera = null;

  // Selected stage state for interactive inspection
  let activeStage = $state('all'); // 'all', 'ingest', 'core', 'execution'

  // Mouse interaction state
  let mouseX = 0;
  let mouseY = 0;
  let targetRotX = 0.58;
  let targetRotY = 0.0;
  let currentRotX = 0.58;
  let currentRotY = 0.0;
  let isDragging = false;
  let previousMousePos = { x: 0, y: 0 };

  // Helper to generate crisp high-DPI text canvas textures
  function createLabelTexture(mainText, subText, accentColor = '#38bdf8', bgColor = '#090d16', borderColor = 'rgba(255,255,255,0.12)') {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 160;
    const ctx = canvas.getContext('2d');

    // Background Card
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, 512, 160);

    // Accent left stripe
    ctx.fillStyle = accentColor;
    ctx.fillRect(0, 0, 10, 160);

    // Subtle border
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, 508, 156);

    // Main Title
    ctx.font = 'bold 34px "JetBrains Mono", monospace';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'left';
    ctx.fillText(mainText, 26, 62);

    // Subtitle / Metrics
    if (subText) {
      ctx.font = '600 22px "JetBrains Mono", monospace';
      ctx.fillStyle = accentColor;
      ctx.fillText(subText, 26, 114);
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    return texture;
  }

  onMount(() => {
    if (!canvasRef || !containerRef) return;

    const width = containerRef.clientWidth || 540;
    const height = containerRef.clientHeight || 480;

    // 1. Scene & Isometric Perspective Camera
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
    camera.position.set(0, 115, 155);
    camera.lookAt(0, -6, 0);

    // 2. WebGL Renderer
    renderer = new THREE.WebGLRenderer({
      canvas: canvasRef,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    // 3. Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(40, 90, 60);
    scene.add(dirLight);

    const goldPoint = new THREE.PointLight(0xf59e0b, 2.8, 260);
    goldPoint.position.set(45, 45, 30);
    scene.add(goldPoint);

    const cyanPoint = new THREE.PointLight(0x38bdf8, 2.5, 260);
    cyanPoint.position.set(-45, 45, -20);
    scene.add(cyanPoint);

    // Root Group holding all components
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // -------------------------------------------------------------
    // 4. MAIN ARCHITECTURAL MOTHERBOARD (BASE CHASSIS)
    // -------------------------------------------------------------
    const boardWidth = 168;
    const boardDepth = 104;
    const boardGeo = new THREE.BoxGeometry(boardWidth, 3, boardDepth);
    const boardMat = new THREE.MeshPhongMaterial({
      color: 0x080c14,
      specular: 0x1e293b,
      shininess: 30,
    });
    const motherboard = new THREE.Mesh(boardGeo, boardMat);
    motherboard.position.y = -1.5;
    rootGroup.add(motherboard);

    // Subtle edge rim on the motherboard
    const rimGeo = new THREE.BoxGeometry(boardWidth + 1, 0.5, boardDepth + 1);
    const rimMat = new THREE.MeshBasicMaterial({ color: 0x1e293b, wireframe: true });
    const rim = new THREE.Mesh(rimGeo, rimMat);
    rim.position.y = 0.2;
    rootGroup.add(rim);

    // High-tech PCB Grid Pattern on top of motherboard
    const gridHelper = new THREE.GridHelper(160, 32, 0x1e293b, 0x0f172a);
    gridHelper.position.y = 0.1;
    rootGroup.add(gridHelper);

    // -------------------------------------------------------------
    // 5. STAGE 1: MARKET INGESTION BAY (LEFT SIDE, X = -54)
    // Live tick feeds from Binance WebSocket across 100++ USDT pairs
    // -------------------------------------------------------------
    const ingestGroup = new THREE.Group();
    ingestGroup.position.set(-54, 0, 0);
    rootGroup.add(ingestGroup);

    // Ingestion Rack Base
    const ingestBaseGeo = new THREE.BoxGeometry(32, 6, 68);
    const ingestBaseMat = new THREE.MeshPhongMaterial({
      color: 0x0b1322,
      specular: 0x38bdf8,
      shininess: 40,
    });
    const ingestBase = new THREE.Mesh(ingestBaseGeo, ingestBaseMat);
    ingestBase.position.y = 3;
    ingestGroup.add(ingestBase);

    // 3 Server Blade Units (BTC, ETH, SOL Market Feeds)
    const bladeGeo = new THREE.BoxGeometry(26, 4, 16);
    const bladeMat = new THREE.MeshPhongMaterial({ color: 0x0f172a, specular: 0x38bdf8 });
    const bladePositionsZ = [-20, 0, 20];
    const bladePairs = ['BTC/USDT', 'ETH/USDT', '100+ PAIRS'];
    const bladeLeds = [];

    bladePositionsZ.forEach((bz, idx) => {
      const blade = new THREE.Mesh(bladeGeo, bladeMat);
      blade.position.set(0, 7.5, bz);
      ingestGroup.add(blade);

      // Status LED strip on blade front
      const ledGeo = new THREE.BoxGeometry(2, 1, 10);
      const ledMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
      const led = new THREE.Mesh(ledGeo, ledMat);
      led.position.set(13, 8.5, bz);
      ingestGroup.add(led);
      bladeLeds.push(led);
    });

    // Ingestion Stage Floating 3D Title Label
    const ingestTex = createLabelTexture('01 · MARKET INGESTION', '100++ USDT PAIRS · BINANCE WS', '#38bdf8', '#070f1e');
    const labelPlaneGeo = new THREE.PlaneGeometry(32, 10);
    const ingestLabelMat = new THREE.MeshBasicMaterial({ map: ingestTex, transparent: true });
    const ingestLabelMesh = new THREE.Mesh(labelPlaneGeo, ingestLabelMat);
    ingestLabelMesh.rotation.x = -Math.PI / 2;
    ingestLabelMesh.position.set(0, 6.2, -40);
    ingestGroup.add(ingestLabelMesh);

    // -------------------------------------------------------------
    // 6. STAGE 2: NEURALINK QUANT CORE PROCESSOR (CENTER, X = 0)
    // 50++ Independent Strategy Models running parallel compute
    // -------------------------------------------------------------
    const coreGroup = new THREE.Group();
    coreGroup.position.set(0, 0, 0);
    rootGroup.add(coreGroup);

    // Ceramic CPU Substrate / Heatspreader
    const cpuSubstrateGeo = new THREE.BoxGeometry(50, 7, 50);
    const cpuSubstrateMat = new THREE.MeshPhongMaterial({
      color: 0x070c16,
      specular: 0xf59e0b,
      shininess: 70,
    });
    const cpuSubstrate = new THREE.Mesh(cpuSubstrateGeo, cpuSubstrateMat);
    cpuSubstrate.position.y = 3.5;
    coreGroup.add(cpuSubstrate);

    // Gold chamfered rim around CPU
    const cpuGoldRimGeo = new THREE.BoxGeometry(51, 1, 51);
    const cpuGoldRimMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
    const cpuGoldRim = new THREE.Mesh(cpuGoldRimGeo, cpuGoldRimMat);
    cpuGoldRim.position.y = 7.1;
    coreGroup.add(cpuGoldRim);

    // 4 Modular Algorithm Compute Units (Silicon Dies on top of CPU)
    // Die 1: Trend / Momentum (15 Algos)
    // Die 2: Volatility / Breakout (14 Algos)
    // Die 3: Mean Reversion / RSI (12 Algos)
    // Die 4: High-Freq Grid / Scalp (12 Algos)
    const dieOffsets = [
      { x: -12, z: -12, label: 'TREND', count: '15 ALGOS', color: 0xf59e0b },
      { x: 12, z: -12, label: 'VOLATILITY', count: '14 ALGOS', color: 0x38bdf8 },
      { x: -12, z: 12, label: 'MEAN-REV', count: '12 ALGOS', color: 0x10b981 },
      { x: 12, z: 12, label: 'GRID/SCALP', count: '12 ALGOS', color: 0xe0e7ff },
    ];
    const dieGeo = new THREE.BoxGeometry(19, 3, 19);
    const dieLeds = [];

    dieOffsets.forEach((dieInfo) => {
      const dieMat = new THREE.MeshPhongMaterial({
        color: 0x0f172a,
        emissive: dieInfo.color,
        emissiveIntensity: 0.15,
        specular: 0xffffff,
      });
      const dieMesh = new THREE.Mesh(dieGeo, dieMat);
      dieMesh.position.set(dieInfo.x, 8.5, dieInfo.z);
      coreGroup.add(dieMesh);

      // Micro LED on each die
      const ledGeo = new THREE.SphereGeometry(1.2, 8, 8);
      const ledMat = new THREE.MeshBasicMaterial({ color: dieInfo.color });
      const led = new THREE.Mesh(ledGeo, ledMat);
      led.position.set(dieInfo.x, 10.6, dieInfo.z);
      coreGroup.add(led);
      dieLeds.push(led);
    });

    // Central Neuralink N1 Bridge Hub (Directly interconnecting all 4 dies)
    const hubUnitGeo = new THREE.CylinderGeometry(5.5, 6.0, 4, 24);
    const hubUnitMat = new THREE.MeshPhongMaterial({
      color: 0x030712,
      specular: 0xf59e0b,
      shininess: 90,
    });
    const hubUnit = new THREE.Mesh(hubUnitGeo, hubUnitMat);
    hubUnit.position.set(0, 10, 0);
    coreGroup.add(hubUnit);

    const hubBeaconGeo = new THREE.SphereGeometry(1.8, 16, 16);
    const hubBeaconMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
    const hubBeacon = new THREE.Mesh(hubBeaconGeo, hubBeaconMat);
    hubBeacon.position.set(0, 12.8, 0);
    coreGroup.add(hubBeacon);

    // Laser Scan Beam sweeping across CPU
    const scanBeamGeo = new THREE.BoxGeometry(48, 0.4, 1.2);
    const scanBeamMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.8 });
    const scanBeam = new THREE.Mesh(scanBeamGeo, scanBeamMat);
    scanBeam.position.set(0, 10.5, 0);
    coreGroup.add(scanBeam);

    // Quant Core Floating 3D Title Label
    const coreTex = createLabelTexture('02 · NEURALINK QUANT CORE', '50++ STRATEGY ENGINES IN PARALLEL', '#f59e0b', '#0f0a05');
    const coreLabelMat = new THREE.MeshBasicMaterial({ map: coreTex, transparent: true });
    const coreLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(36, 11), coreLabelMat);
    coreLabelMesh.rotation.x = -Math.PI / 2;
    coreLabelMesh.position.set(0, 6.2, -35);
    coreGroup.add(coreLabelMesh);

    // -------------------------------------------------------------
    // 7. STAGE 3: DUAL EXECUTION TERMINALS (RIGHT SIDE, X = +54)
    // Terminal 1: Crypto Spot Arena (1x Leverage, 39 Models)
    // Terminal 2: Crypto Futures Arena (Leverage Hingga 20x, 53 Models)
    // -------------------------------------------------------------
    const execGroup = new THREE.Group();
    execGroup.position.set(54, 0, 0);
    rootGroup.add(execGroup);

    // Execution Terminal Platform
    const termBaseGeo = new THREE.BoxGeometry(32, 6, 68);
    const termBaseMat = new THREE.MeshPhongMaterial({
      color: 0x090f19,
      specular: 0x10b981,
      shininess: 40,
    });
    const termBase = new THREE.Mesh(termBaseGeo, termBaseMat);
    termBase.position.y = 3;
    execGroup.add(termBase);

    // Terminal A: SPOT ARENA TOWER (Z = -18)
    const spotTowerGeo = new THREE.BoxGeometry(26, 8, 24);
    const spotTowerMat = new THREE.MeshPhongMaterial({
      color: 0x091c15,
      specular: 0x10b981,
      shininess: 60,
    });
    const spotTower = new THREE.Mesh(spotTowerGeo, spotTowerMat);
    spotTower.position.set(0, 10, -18);
    execGroup.add(spotTower);

    const spotTex = createLabelTexture('CRYPTO SPOT', '1X LEV · 39 STRATS', '#10b981', '#06130e');
    const spotLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(24, 8), new THREE.MeshBasicMaterial({ map: spotTex, transparent: true }));
    spotLabelMesh.rotation.x = -Math.PI / 2;
    spotLabelMesh.position.set(0, 14.2, -18);
    execGroup.add(spotLabelMesh);

    // Terminal B: FUTURES ARENA TOWER (Z = +18)
    const futuresTowerGeo = new THREE.BoxGeometry(26, 8, 24);
    const futuresTowerMat = new THREE.MeshPhongMaterial({
      color: 0x1c1305,
      specular: 0xf59e0b,
      shininess: 60,
    });
    const futuresTower = new THREE.Mesh(futuresTowerGeo, futuresTowerMat);
    futuresTower.position.set(0, 10, 18);
    execGroup.add(futuresTower);

    const futuresTex = createLabelTexture('CRYPTO FUTURES', '20X LEV · 53 STRATS', '#f59e0b', '#180f03');
    const futuresLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(24, 8), new THREE.MeshBasicMaterial({ map: futuresTex, transparent: true }));
    futuresLabelMesh.rotation.x = -Math.PI / 2;
    futuresLabelMesh.position.set(0, 14.2, 18);
    execGroup.add(futuresLabelMesh);

    // Execution Stage Floating 3D Title Label
    const execTex = createLabelTexture('03 · DUAL EXECUTION ARENAS', 'MTM PER DETIK · SPOT & FUTURES 20X', '#10b981', '#050f14');
    const execLabelMesh = new THREE.Mesh(new THREE.PlaneGeometry(32, 10), new THREE.MeshBasicMaterial({ map: execTex, transparent: true }));
    execLabelMesh.rotation.x = -Math.PI / 2;
    execLabelMesh.position.set(0, 6.2, -40);
    execGroup.add(execLabelMesh);

    // -------------------------------------------------------------
    // 8. BUS HIGHWAYS & DYNAMIC DATA PACKETS (LEFT -> CENTER -> RIGHT)
    // -------------------------------------------------------------
    // Glowing Bus Highway Tracks (Line Segments)
    const busLinesPositions = [
      // Ingestion to Core (3 parallel lanes)
      -38, 2, -14,   -25, 2, -14,
      -38, 2,   0,   -25, 2,   0,
      -38, 2,  14,   -25, 2,  14,
      // Core to Spot Terminal
      25, 2, -18,    38, 2, -18,
      // Core to Futures Terminal
      25, 2,  18,    38, 2,  18,
    ];
    const busLineGeo = new THREE.BufferGeometry();
    busLineGeo.setAttribute('position', new THREE.Float32BufferAttribute(busLinesPositions, 3));
    const busLineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.6 });
    const busLineMesh = new THREE.LineSegments(busLineGeo, busLineMat);
    rootGroup.add(busLineMesh);

    // Streaming Data Pulses (Particles racing along the bus tracks)
    const inPulseCount = 28;
    const inPulsePositions = new Float32Array(inPulseCount * 3);
    const inPulses = [];
    for (let i = 0; i < inPulseCount; i++) {
      inPulses.push({
        progress: Math.random(),
        laneZ: (i % 3 === 0 ? -14 : i % 3 === 1 ? 0 : 14),
        speed: 0.4 + Math.random() * 0.4,
      });
    }
    const inPulseGeo = new THREE.BufferGeometry();
    inPulseGeo.setAttribute('position', new THREE.BufferAttribute(inPulsePositions, 3));
    const inPulseMat = new THREE.PointsMaterial({ color: 0x38bdf8, size: 2.8, transparent: true, opacity: 0.9 });
    const inPulseMesh = new THREE.Points(inPulseGeo, inPulseMat);
    rootGroup.add(inPulseMesh);

    // Outgoing Order Pulses (Core -> Spot & Futures)
    const outPulseCount = 18;
    const outPulsePositions = new Float32Array(outPulseCount * 3);
    const outPulses = [];
    for (let i = 0; i < outPulseCount; i++) {
      const isSpot = i % 2 === 0;
      outPulses.push({
        isSpot,
        progress: Math.random(),
        speed: 0.5 + Math.random() * 0.5,
      });
    }
    const outPulseGeo = new THREE.BufferGeometry();
    outPulseGeo.setAttribute('position', new THREE.BufferAttribute(outPulsePositions, 3));
    const outPulseMat = new THREE.PointsMaterial({ color: 0xfef08a, size: 3.2, transparent: true, opacity: 0.95 });
    const outPulseMesh = new THREE.Points(outPulseGeo, outPulseMat);
    rootGroup.add(outPulseMesh);

    // -------------------------------------------------------------
    // 9. MOUSE TRACKING & INTERACTIVE CAMERA CONTROLS
    // -------------------------------------------------------------
    function handleMouseMove(e) {
      if (isDragging) {
        const deltaX = e.clientX - previousMousePos.x;
        const deltaY = e.clientY - previousMousePos.y;
        targetRotY += deltaX * 0.006;
        targetRotX += deltaY * 0.005;
        // Clamp vertical tilt
        targetRotX = Math.max(0.35, Math.min(0.95, targetRotX));
        previousMousePos = { x: e.clientX, y: e.clientY };
      } else {
        const rect = containerRef.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        mouseX = (e.clientX - cx) / (rect.width / 2);
        mouseY = (e.clientY - cy) / (rect.height / 2);
        targetRotY = mouseX * 0.28;
        targetRotX = 0.58 + mouseY * 0.16;
      }
    }

    function handleMouseDown(e) {
      isDragging = true;
      previousMousePos = { x: e.clientX, y: e.clientY };
    }

    function handleMouseUp() {
      isDragging = false;
    }

    function handleResize() {
      if (!containerRef || !renderer || !camera) return;
      const w = containerRef.clientWidth || 540;
      const h = containerRef.clientHeight || 480;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('resize', handleResize);

    // -------------------------------------------------------------
    // 10. ANIMATION LOOP
    // -------------------------------------------------------------
    const clock = new THREE.Clock();

    function animate() {
      animId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const elapsed = clock.getElapsedTime();

      // Damped smooth camera / root tilt
      currentRotY += (targetRotY - currentRotY) * 0.06;
      currentRotX += (targetRotX - currentRotX) * 0.06;
      rootGroup.rotation.y = currentRotY;
      rootGroup.rotation.x = currentRotX;

      // 1. Ingestion blade LEDs blink (simulating live tick arrival)
      bladeLeds.forEach((led, idx) => {
        const blink = Math.sin(elapsed * 6 + idx * 1.5) > 0.3;
        led.material.color.set(blink ? 0x10b981 : 0x064e3b);
      });

      // 2. Scan beam sweep on Neuralink Quant CPU
      scanBeam.position.z = Math.sin(elapsed * 2.2) * 20;

      // 3. Central Hub Beacon heartbeat
      const hubPulse = 0.5 + 0.5 * Math.sin(elapsed * 4);
      hubBeaconMat.color.setRGB(0.06 * hubPulse, 0.72 + 0.28 * hubPulse, 0.5);

      // 4. Algorithm die LEDs flash (simulating active strategy evaluations)
      dieLeds.forEach((led, idx) => {
        const flash = Math.sin(elapsed * 8 + idx * 2.0) > 0.4;
        led.scale.setScalar(flash ? 1.4 : 1.0);
      });

      // 5. Update Input Data Pulses (Ingestion -> Core)
      const inPos = inPulseGeo.attributes.position.array;
      for (let i = 0; i < inPulseCount; i++) {
        const p = inPulses[i];
        p.progress += delta * p.speed;
        if (p.progress >= 1.0) p.progress = 0;

        // Travel from X = -38 to X = -25
        inPos[i * 3] = -38 + p.progress * 13;
        inPos[i * 3 + 1] = 2.5;
        inPos[i * 3 + 2] = p.laneZ;
      }
      inPulseGeo.attributes.position.needsUpdate = true;

      // 6. Update Outgoing Execution Pulses (Core -> Spot & Futures)
      const outPos = outPulseGeo.attributes.position.array;
      for (let i = 0; i < outPulseCount; i++) {
        const p = outPulses[i];
        p.progress += delta * p.speed;
        if (p.progress >= 1.0) p.progress = 0;

        // Travel from X = 25 to X = 38
        outPos[i * 3] = 25 + p.progress * 13;
        outPos[i * 3 + 1] = 2.5;
        outPos[i * 3 + 2] = p.isSpot ? -18 : 18;
      }
      outPulseGeo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    }

    animate();

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('resize', handleResize);
      if (animId) cancelAnimationFrame(animId);
      if (renderer) renderer.dispose();
    };
  });
</script>

<div class="simulator-wrapper" bind:this={containerRef}>
  <!-- Main 3D Canvas -->
  <canvas 
    bind:this={canvasRef}
    onmousedown={(e) => {
      isDragging = true;
      previousMousePos = { x: e.clientX, y: e.clientY };
    }}
  ></canvas>

  <!-- Top Institutional HUD Header -->
  <div class="hud-top">
    <div class="hud-pill live-pill">
      <span class="pulse-dot"></span>
      <span class="mono">LIVE SYSTEM SIMULATION · STRATEGY ARENA ARCHITECTURE</span>
    </div>
    <div class="hud-pill mono latency-pill">
      LATENCY &lt; 5MS · MTM 1s
    </div>
  </div>

  <!-- Interactive Stage Selector / Architecture Legend at Bottom -->
  <div class="hud-bottom-bar">
    <div class="legend-card" class:active={activeStage === 'ingest'}>
      <div class="step-num mono">01</div>
      <div class="card-info">
        <span class="card-title">MARKET INGESTION</span>
        <span class="card-desc mono">100++ Pair Liquid Binance WebSocket</span>
      </div>
    </div>

    <div class="arrow-divider">→</div>

    <div class="legend-card center-card" class:active={activeStage === 'core'}>
      <div class="step-num mono">02</div>
      <div class="card-info">
        <span class="card-title">NEURALINK QUANT CORE</span>
        <span class="card-desc mono">50++ Algoritma Independen Paralel</span>
      </div>
    </div>

    <div class="arrow-divider">→</div>

    <div class="legend-card" class:active={activeStage === 'execution'}>
      <div class="step-num mono">03</div>
      <div class="card-info">
        <span class="card-title">DUAL ARENA EXECUTION</span>
        <span class="card-desc mono">Spot (1x) & Futures (Leverage 20x)</span>
      </div>
    </div>
  </div>
</div>

<style>
  .simulator-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 480px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: radial-gradient(circle at 50% 40%, rgba(15, 23, 42, 0.5) 0%, rgba(5, 8, 14, 0.95) 75%, #04070c 100%);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    overflow: hidden;
  }

  canvas {
    position: absolute;
    inset: 0;
    display: block;
    width: 100%;
    height: 100%;
    cursor: grab;
  }

  canvas:active {
    cursor: grabbing;
  }

  /* HUD Top Header */
  .hud-top {
    position: relative;
    z-index: 10;
    pointer-events: none;
    padding: 14px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .hud-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(9, 13, 20, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 5px 12px;
    border-radius: 6px;
    font-size: 11px;
    color: #cbd5e1;
    backdrop-filter: blur(6px);
  }

  .live-pill {
    font-weight: 700;
    letter-spacing: 0.04em;
  }

  .latency-pill {
    color: #10b981;
    font-weight: 700;
  }

  .pulse-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
  }

  /* Interactive Legend Bottom Bar */
  .hud-bottom-bar {
    position: relative;
    z-index: 10;
    padding: 12px 14px;
    display: grid;
    grid-template-columns: 1fr auto 1.15fr auto 1fr;
    gap: 8px;
    align-items: center;
    background: rgba(5, 8, 14, 0.9);
    border-top: 1px solid rgba(255, 255, 255, 0.07);
    backdrop-filter: blur(8px);
  }

  .legend-card {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.06);
    padding: 8px 10px;
    border-radius: 6px;
    transition: all 0.15s ease;
  }

  .legend-card:hover {
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(15, 23, 42, 0.85);
  }

  .center-card {
    border-color: rgba(245, 158, 11, 0.25);
    background: rgba(245, 158, 11, 0.04);
  }

  .step-num {
    font-size: 11px;
    font-weight: 800;
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.15);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .card-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .card-title {
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .card-desc {
    font-size: 9.5px;
    color: #94a3b8;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .arrow-divider {
    color: #475569;
    font-size: 12px;
    font-weight: 800;
    user-select: none;
  }

  @media (max-width: 768px) {
    .hud-bottom-bar {
      grid-template-columns: 1fr;
      gap: 6px;
    }
    .arrow-divider {
      display: none;
    }
  }
</style>
