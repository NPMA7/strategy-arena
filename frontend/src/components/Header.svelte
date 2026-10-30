<script>
  import { arena } from "../lib/store.svelte.js";
  import { formatUptime } from "../lib/formatters.js";

  let mobileMenuOpen = $state(false);

  function handleModeChange(m) {
    arena.setMode(m);
  }

  function handleNav(mode) {
    mobileMenuOpen = false;
    if (mode === "executions") {
      arena.navigate("/neural-execution");
    } else {
      arena.setMode(mode);
      const target =
        mode === "spot"
          ? "/crypto-spot"
          : mode === "futures"
            ? "/crypto-futures"
            : "/forex";
      arena.navigate(target);
    }
  }
</script>

<header class="header-root">
  <div class="header-left">
    <a
      href="/"
      class="brand-link"
      title="Kembali ke Page Utama"
      onclick={(e) => {
        e.preventDefault();
        mobileMenuOpen = false;
        arena.navigate("/");
      }}
    >
      <div class="brand-emblem">
        <svg viewBox="0 0 64 64" width="34" height="34" class="emblem-svg">
          <defs>
            <linearGradient id="hdrBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#151b26" />
              <stop offset="100%" stop-color="#080c12" />
            </linearGradient>
            <linearGradient id="hdrGold" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#fbbf24" />
              <stop offset="100%" stop-color="#d97706" />
            </linearGradient>
            <linearGradient id="hdrCyan" x1="0%" y1="0%" x2="100%" y2="100%">
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
            fill="url(#hdrBg)"
            stroke="#232d3d"
            stroke-width="1.5"
          />
          <path
            d="M26 16 L15 16 L15 29 L26 31 L26 47 L14 47"
            stroke="url(#hdrGold)"
            stroke-width="4.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M31 47 L41 16 L51 47"
            stroke="url(#hdrGold)"
            stroke-width="4.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            d="M35 37 L47 37"
            stroke="url(#hdrCyan)"
            stroke-width="3"
            stroke-linecap="round"
          />
          <circle cx="41" cy="16" r="3.2" fill="#ffffff" />
        </svg>
      </div>
      <div class="brand-text">
        <div class="brand-title">STRATEGY <span>ARENA</span></div>
        <div class="brand-sub mono">MULTI-ASSET QUANT ENGINE</div>
      </div>
    </a>

    <!-- Multi-Asset Market Switcher Navigation (Desktop) -->
    <nav class="market-switcher desktop-nav" aria-label="Market Mode Selection">
      <button
        class="switcher-btn {arena.currentRoute === 'spot' ? 'active-spot' : ''}"
        onclick={() => handleModeChange("spot")}
      >
        <span class="indicator-dot dot-amber"></span>
        <span class="label">Crypto Spot</span>
      </button>

      <button
        class="switcher-btn {arena.currentRoute === 'futures' ? 'active-futures' : ''}"
        onclick={() => handleModeChange("futures")}
      >
        <span class="indicator-dot dot-cyan"></span>
        <span class="label">Crypto Futures</span>
      </button>

      <button
        class="switcher-btn {arena.currentRoute === 'forex' ? 'active-forex' : ''}"
        onclick={() => handleModeChange("forex")}
      >
        <span class="indicator-dot dot-emerald"></span>
        <span class="label">Forex & Metals</span>
      </button>

      <button
        class="switcher-btn {arena.currentRoute === 'executions' ? 'active-neural' : ''}"
        onclick={() => arena.navigate("/neural-execution")}
        title="Lihat Visual Neural Network & Seluruh Eksekusi Trade Multi-Pasar"
      >
        <span class="indicator-dot dot-purple"></span>
        <span class="label">Neural Execution</span>
      </button>

      <div class="switcher-btn disabled" title="Direncanakan untuk Phase 2">
        <span class="label">Saham</span>
        <span class="tag-soon">Segera</span>
      </div>
    </nav>
  </div>

  <div class="header-right">
    <!-- Live Feed Telemetry Pill (Desktop/Tablet) -->
    <div class="telemetry-pill">
      <span class="live-status {arena.connected ? 'online' : 'offline'}">
        <span class="pulse-ring"></span>
        <span class="status-dot"></span>
        <span class="status-text"
          >{arena.connected ? "" : "RECONNECTING"}</span
        >
      </span>

      <span class="telemetry-divider"></span>

      <!-- Database Size Badge -->
      <div
        class="db-size-badge"
        title="Ukuran total penyimpanan database PostgreSQL ($PGDATA: data tabel, indeks & WAL)"
      >
        <span class="lbl">DB:</span>
        <span class="val num">{arena.dbSize}</span>
      </div>

      <span class="telemetry-divider"></span>

      <!-- Continuous Uptime Clock -->
      <div
        class="uptime-badge"
        title="Waktu berjalan kontinu (tidak reset saat restart)"
      >
        <span class="lbl">UPTIME:</span>
        <span class="val num">{formatUptime(arena.uptime)}</span>
      </div>
    </div>

    <!-- Copy-Trade API Trigger Button -->
    <button
      class="btn-copy-trade"
      onclick={() => (arena.copyTradeModalOpen = true)}
      title="Buka panduan & API Key untuk menyalin sinyal trading"
    >
      <svg
        class="btn-icon-svg"
        viewBox="0 0 24 24"
        width="13"
        height="13"
        fill="none"
        stroke="currentColor"
        stroke-width="2.2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>
      <span class="btn-text">Copy-Trade API</span>
    </button>

    <!-- Hamburger Button (Mobile Only) -->
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
            class="drawer-nav-item item-spot {arena.currentRoute === 'spot' ? 'active-item' : ''}"
            onclick={() => handleNav('spot')}
          >
            <div class="drawer-icon icon-spot">
              <span class="dot-spot"></span>
            </div>
            <div class="drawer-item-info">
              <span class="item-name">Terminal Spot</span>
              <span class="item-desc">Binance Crypto Spot (No-Leverage)</span>
            </div>
            {#if arena.currentRoute === 'spot'}
              <span class="active-badge spot">AKTIF</span>
            {/if}
            <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>

          <button
            type="button"
            class="drawer-nav-item item-futures {arena.currentRoute === 'futures' ? 'active-item' : ''}"
            onclick={() => handleNav('futures')}
          >
            <div class="drawer-icon icon-futures">
              <span class="dot-futures"></span>
            </div>
            <div class="drawer-item-info">
              <span class="item-name">Terminal Futures</span>
              <span class="item-desc">Binance Perpetual (Leverage 1–20x)</span>
            </div>
            {#if arena.currentRoute === 'futures'}
              <span class="active-badge futures">AKTIF</span>
            {/if}
            <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>

          <button
            type="button"
            class="drawer-nav-item item-forex {arena.currentRoute === 'forex' ? 'active-item' : ''}"
            onclick={() => handleNav('forex')}
          >
            <div class="drawer-icon icon-forex">
              <span class="dot-forex"></span>
            </div>
            <div class="drawer-item-info">
              <span class="item-name">Terminal Forex & Metals</span>
              <span class="item-desc">MT5 Direct Feed & Eksekusi Headway</span>
            </div>
            {#if arena.currentRoute === 'forex'}
              <span class="active-badge forex">AKTIF</span>
            {/if}
            <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>

          <button
            type="button"
            class="drawer-nav-item item-neural {arena.currentRoute === 'executions' ? 'active-item' : ''}"
            onclick={() => handleNav('executions')}
          >
            <div class="drawer-icon icon-neural">
              <span class="dot-neural"></span>
            </div>
            <div class="drawer-item-info">
              <span class="item-name">Neural Execution</span>
              <span class="item-desc">Visual 3D Matrix & Realtime Trade Feed</span>
            </div>
            {#if arena.currentRoute === 'executions'}
              <span class="active-badge neural">AKTIF</span>
            {/if}
            <svg class="chevron-svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>
        </div>

        <div class="drawer-footer">
          <div class="drawer-telemetry-row">
            <span class="live-status {arena.connected ? 'online' : 'offline'}">
              <span class="status-dot"></span>
              <span class="status-text">{arena.connected ? 'SYSTEM ONLINE' : 'RECONNECTING'}</span>
            </span>
            <span class="telemetry-divider"></span>
            <div class="uptime-badge">
              <span class="lbl">UPTIME:</span>
              <span class="val num">{formatUptime(arena.uptime)}</span>
            </div>
            <span class="telemetry-divider"></span>
            <div class="db-size-badge">
              <span class="lbl">DB:</span>
              <span class="val num">{arena.dbSize}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}
</header>

<style>
  .header-root {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
    background-color: var(--bg-surface);
    border-bottom: 1px solid var(--border-subtle);
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 50;
    backdrop-filter: blur(8px);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 24px;
    flex-wrap: wrap;
  }

  .brand-link {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    color: inherit;
  }

  .brand-emblem {
    display: flex;
    align-items: center;
  }

  .brand-title {
    font-family: var(--font-display);
    font-weight: 800;
    font-size: 15px;
    letter-spacing: -0.02em;
    color: var(--fg-primary);
    line-height: 1.1;
  }

  .brand-title span {
    color: var(--color-amber);
  }

  .brand-sub {
    font-size: 9px;
    letter-spacing: 0.08em;
    color: var(--fg-muted);
  }

  /* Market Switcher */
  .market-switcher {
    display: flex;
    align-items: center;
    gap: 4px;
    background-color: var(--bg-base);
    padding: 3px;
    border-radius: 8px;
    border: 1px solid var(--border-subtle);
  }

  .switcher-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 12.5px;
    font-weight: 600;
    color: var(--fg-secondary);
    transition: all 0.15s ease;
  }

  .switcher-btn:hover:not(.disabled) {
    color: var(--fg-primary);
    background-color: var(--bg-surface-elevated);
  }

  .switcher-btn.active-spot {
    background-color: var(--bg-surface-elevated);
    color: var(--color-amber);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border-amber);
  }

  .switcher-btn.active-futures {
    background-color: var(--bg-surface-elevated);
    color: var(--color-cyan);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border-cyan);
  }

  .switcher-btn.active-forex {
    background-color: var(--bg-surface-elevated);
    color: #10b981;
    box-shadow: var(--shadow-sm);
    border: 1px solid rgba(16, 185, 129, 0.4);
  }

  .switcher-btn.active-neural {
    background-color: var(--bg-surface-elevated);
    color: #ffffff85;
    box-shadow: 1px solid var(--shadow-sm);
    border: 1px solid rgba(255, 255, 255, 0.548);
  }

  .switcher-btn.disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .indicator-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  .dot-amber {
    background-color: var(--color-amber);
  }

  .dot-cyan {
    background-color: var(--color-cyan);
  }

  .dot-emerald {
    background-color: #10b981;
  }

  .dot-purple {
    background-color: #ffffffa6;
  }

  .tag-soon {
    font-size: 9.5px;
    font-weight: 600;
    padding: 1px 5px;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.05);
    color: var(--fg-dim);
    text-transform: uppercase;
  }

  /* Right Section */
  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .telemetry-pill {
    display: flex;
    align-items: center;
    gap: 10px;
    background-color: var(--bg-base);
    padding: 5px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-subtle);
    font-size: 11.5px;
  }

  .live-status {
    display: flex;
    align-items: center;
    gap: 6px;
    position: relative;
    font-weight: 600;
    letter-spacing: 0.03em;
  }

  .live-status.online {
    color: var(--color-up);
  }

  .live-status.offline {
    color: var(--color-down);
  }

  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: currentColor;
  }

  .pulse-ring {
    position: absolute;
    top: 50%;
    left: 3.5px;
    transform: translate(-50%, -50%);
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 1.5px solid var(--color-up);
    opacity: 0.4;
    animation: pulsePing 2s cubic-bezier(0, 0, 0.2, 1) infinite;
  }

  @keyframes pulsePing {
    0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0.8; }
    80%, 100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
  }

  .telemetry-divider {
    width: 1px;
    height: 12px;
    background: var(--border-muted);
  }

  .uptime-badge {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .uptime-badge .lbl {
    color: var(--fg-muted);
    font-size: 10px;
    font-weight: 600;
  }

  .uptime-badge .val {
    color: var(--fg-primary);
    font-weight: 600;
  }

  .db-size-badge {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .db-size-badge .lbl {
    color: var(--fg-muted);
    font-size: 10px;
    font-weight: 600;
  }

  .db-size-badge .val {
    color: #38bdf8;
    font-weight: 700;
    font-family: var(--font-mono, monospace);
  }

  /* Copy-Trade Button */
  .btn-copy-trade {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 6px;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid var(--border-amber);
    color: var(--color-amber);
    font-size: 12.5px;
    font-weight: 600;
    transition: all 0.2s ease;
    white-space: nowrap;
  }

  .btn-copy-trade:hover {
    background: rgba(245, 158, 11, 0.16);
    border-color: var(--color-amber);
    box-shadow: 0 0 10px rgba(245, 158, 11, 0.2);
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
    top: 56px;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(3, 7, 18, 0.85);
    backdrop-filter: blur(10px);
    z-index: 100;
    animation: fadeIn 0.18s ease;
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

  .drawer-nav-item.active-item {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.2);
  }

  .active-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: 0.05em;
    flex-shrink: 0;
  }

  .active-badge.spot {
    background: rgba(245, 158, 11, 0.15);
    color: var(--color-amber);
    border: 1px solid rgba(245, 158, 11, 0.35);
  }

  .active-badge.futures {
    background: rgba(56, 189, 248, 0.15);
    color: var(--color-cyan);
    border: 1px solid rgba(56, 189, 248, 0.35);
  }

  .active-badge.forex {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.35);
  }

  .active-badge.neural {
    background: rgba(168, 85, 247, 0.15);
    color: #c084fc;
    border: 1px solid rgba(168, 85, 247, 0.35);
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

  .drawer-footer {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .drawer-telemetry-row {
    display: flex;
    align-items: center;
    justify-content: space-around;
    font-size: 11px;
    color: var(--fg-muted);
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideDown {
    from { transform: translateY(-12px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }

  @media (max-width: 900px) {
    .header-root {
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      gap: 12px;
    }
    .header-left {
      flex-direction: row;
      align-items: center;
      gap: 12px;
      width: auto;
    }
    .brand-link {
      width: auto;
      justify-content: flex-start;
    }
    .market-switcher {
      display: none !important;
    }
    .hamburger-btn {
      display: flex;
    }
    .header-right {
      width: auto;
      border-top: none;
      padding-top: 0;
      gap: 8px;
    }
  }

  @media (max-width: 640px) {
    .header-right .telemetry-pill {
      display: none;
    }
  }

  @media (max-width: 480px) {
    .header-root {
      padding: 8px 12px;
    }
    .brand-title {
      font-size: 14px;
    }
    .brand-sub {
      font-size: 8px;
    }
    .btn-copy-trade {
      padding: 5px 9px;
      font-size: 11px;
    }
    .btn-copy-trade .btn-text {
      font-size: 11px;
    }
  }
</style>
