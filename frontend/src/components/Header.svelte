<script>
  import { arena } from "../lib/store.svelte.js";
  import { formatUptime } from "../lib/formatters.js";

  function handleModeChange(m) {
    arena.setMode(m);
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

    <!-- Multi-Asset Market Switcher Navigation -->
    <nav class="market-switcher" aria-label="Market Mode Selection">
      <button
        class="switcher-btn {arena.mode === 'spot' ? 'active-spot' : ''}"
        onclick={() => handleModeChange("spot")}
      >
        <span class="indicator-dot dot-amber"></span>
        <span class="label">Crypto Spot</span>
      </button>

      <button
        class="switcher-btn {arena.mode === 'futures' ? 'active-futures' : ''}"
        onclick={() => handleModeChange("futures")}
      >
        <span class="indicator-dot dot-cyan"></span>
        <span class="label">Crypto Futures</span>
      </button>

      <button
        class="switcher-btn {arena.mode === 'forex' ? 'active-forex' : ''}"
        onclick={() => handleModeChange("forex")}
      >
        <span class="indicator-dot dot-emerald"></span>
        <span class="label">Forex & Metals</span>
      </button>

      <div class="switcher-btn disabled" title="Direncanakan untuk Phase 2">
        <span class="label">Saham</span>
        <span class="tag-soon">Segera</span>
      </div>
    </nav>
  </div>

  <div class="header-right">
    <!-- Live Feed Telemetry Pill -->
    <div class="telemetry-pill">
      <span class="live-status {arena.connected ? 'online' : 'offline'}">
        <span class="pulse-ring"></span>
        <span class="status-dot"></span>
        <span class="status-text"
          >{arena.connected ? "LIVE FEED" : "RECONNECTING"}</span
        >
      </span>

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
  </div>
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
  }

  .btn-copy-trade:hover {
    background: rgba(245, 158, 11, 0.16);
    border-color: var(--color-amber);
    box-shadow: 0 0 10px rgba(245, 158, 11, 0.2);
  }

  @media (max-width: 900px) {
    .header-root {
      flex-direction: column;
      align-items: stretch;
      padding: 10px 12px;
    }
    .header-left,
    .header-right {
      justify-content: space-between;
      width: 100%;
    }
    .market-switcher {
      overflow-x: auto;
      max-width: 100%;
    }
  }
</style>
