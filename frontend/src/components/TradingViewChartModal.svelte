<script>
  import { onDestroy } from 'svelte';
  import { arena } from '../lib/store.svelte.js';
  import { formatPrice, formatUSD } from '../lib/formatters.js';

  let selectedInterval = $state('15'); // '1', '5', '15', '60', '240', 'D'

  const intervals = [
    { id: '1', label: '1m' },
    { id: '5', label: '5m' },
    { id: '15', label: '15m' },
    { id: '60', label: '1h' },
    { id: '240', label: '4h' },
    { id: 'D', label: '1D' },
  ];

  let rawSymbol = $derived(arena.chartModalSymbol || '');

  // Parse market category and base/quote
  let symbolInfo = $derived.by(() => {
    if (!rawSymbol) return { symbol: '', base: '', quote: '', category: 'crypto', tvSymbol: 'BINANCE:BTCUSDT' };
    const sym = rawSymbol.toUpperCase().trim();

    // 1. Metals & Commodities
    if (sym === 'XAUUSD' || sym === 'GOLD') {
      return { symbol: 'XAUUSD', base: 'XAU', quote: 'USD', category: 'forex', name: 'Gold / US Dollar', tvSymbol: 'OANDA:XAUUSD' };
    }
    if (sym === 'XAGUSD' || sym === 'SILVER') {
      return { symbol: 'XAGUSD', base: 'XAG', quote: 'USD', category: 'forex', name: 'Silver / US Dollar', tvSymbol: 'OANDA:XAGUSD' };
    }
    if (sym === 'XTIUSD' || sym === 'USOIL' || sym === 'WTIUSD' || sym === 'OIL') {
      return { symbol: 'XTIUSD', base: 'XTI', quote: 'USD', category: 'forex', name: 'WTI Crude Oil', tvSymbol: 'TVC:USOIL' };
    }

    // 2. Forex Pairs (6 characters)
    const isForex = arena.chartModalCategory === 'forex' || (
      sym.length === 6 &&
      !sym.endsWith('USDT') &&
      !sym.endsWith('USDC') &&
      ['EUR', 'GBP', 'USD', 'JPY', 'AUD', 'CAD', 'CHF', 'NZD'].some(c => sym.startsWith(c))
    );

    if (isForex) {
      const base = sym.slice(0, 3);
      const quote = sym.slice(3);
      return {
        symbol: sym,
        base,
        quote,
        category: 'forex',
        name: `${base} / ${quote} (OANDA)`,
        tvSymbol: `OANDA:${sym}`
      };
    }

    // 3. Crypto Pairs
    const normSym = sym.endsWith('USDT') ? sym : `${sym}USDT`;
    const base = normSym.replace('USDT', '');
    return {
      symbol: normSym,
      base,
      quote: 'USDT',
      category: 'crypto',
      name: `${base} / Tether USD`,
      tvSymbol: `BINANCE:${normSym}`
    };
  });

  // Current live market price
  let livePrice = $derived.by(() => {
    if (!rawSymbol) return null;
    const px = arena.prices[rawSymbol] ?? arena.prices[symbolInfo.symbol] ?? null;
    return px ? Number(px) : null;
  });

  // TradingView Iframe Embed URL with hidesidetoolbar=1 (NO DRAWING TOOLS)
  let iframeUrl = $derived.by(() => {
    const s = encodeURIComponent(symbolInfo.tvSymbol);
    const i = selectedInterval;
    return `https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=${s}&interval=${i}&hidesidetoolbar=1&symboledit=0&saveimage=0&toolbarbg=060910&theme=dark&style=1&timezone=Asia%2FJakarta&locale=id`;
  });

  function handleKeyDown(e) {
    if (e.key === 'Escape' && arena.chartModalOpen) {
      arena.closeChart();
    }
  }

  $effect(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  });
</script>

{#if arena.chartModalOpen}
  <div class="chart-modal-root" role="dialog" aria-modal="true">
    <button
      class="modal-backdrop"
      type="button"
      aria-label="Tutup Chart"
      onclick={() => arena.closeChart()}
    ></button>

    <div class="chart-modal-card">
      <!-- Modal Header -->
      <div class="modal-header">
      
        <div class="header-left">

          <div class="title-wrap">
            <h2 class="sym-title">
              <span class="base-txt">{symbolInfo.base}</span><span class="quote-txt">/{symbolInfo.quote}</span>
            </h2>
            <span class="sub-name mono">{symbolInfo.name}</span>
          </div>

          {#if livePrice != null}
            <div class="live-price-pill mono">
              <span class="dot-live"></span>
              <span class="px-val">
                {symbolInfo.category === 'forex' ? (livePrice.toFixed(symbolInfo.symbol.includes('JPY') ? 3 : 5)) : formatPrice(livePrice)}
              </span>
            </div>
          {/if}
        </div>

        <!-- Middle: Timeframe Switcher -->
        <div class="tf-selector-group">
          {#each intervals as tf}
            <button
              type="button"
              class="tf-btn mono {selectedInterval === tf.id ? 'active' : ''}"
              onclick={() => selectedInterval = tf.id}
            >
              {tf.label}
            </button>
          {/each}
        </div>

        <!-- Right: Public Clean Mode & Close Button -->
        <div class="header-right">
          <button
            type="button"
            class="close-btn"
            aria-label="Tutup Chart"
            onclick={() => arena.closeChart()}
          >
            ✕
          </button>
        </div>
      </div>

      <!-- Modal Body: TradingView Iframe Widget -->
      <div class="chart-viewport">
        <iframe
          title="TradingView Real-time Chart ({symbolInfo.tvSymbol})"
          src={iframeUrl}
          class="tv-iframe"
          frameborder="0"
          allowtransparency="true"
          scrolling="no"
          allowfullscreen
        ></iframe>
      </div>
    </div>
  </div>
{/if}

<style>
  .chart-modal-root {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: grid;
    place-items: center;
    padding: 20px;
    animation: fadeInModal 0.16s ease-out;
  }

  @keyframes fadeInModal {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(4, 7, 13, 0.82);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border: none;
    cursor: default;
    width: 100%;
    height: 100%;
  }

  .chart-modal-card {
    position: relative;
    z-index: 10000;
    width: 100%;
    max-width: 1240px;
    height: 82vh;
    min-height: 580px;
    max-height: 880px;
    background: #060910;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(56, 189, 248, 0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: slideUpModal 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes slideUpModal {
    from {
      opacity: 0;
      transform: translateY(18px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  /* Header */
  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    background: #080d16;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    gap: 16px;
    flex-shrink: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }

  .title-wrap {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .sym-title {
    margin: 0;
    font-size: 19px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
    line-height: 1.1;
  }

  .base-txt {
    color: #ffffff;
  }

  .quote-txt {
    color: #64748b;
    font-size: 14px;
  }

  .sub-name {
    font-size: 10px;
    color: #94a3b8;
  }

  .live-price-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #0d1524;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 4px 10px;
    border-radius: 6px;
  }

  .dot-live {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
    animation: pulseDot 1.2s ease-in-out infinite alternate;
  }

  @keyframes pulseDot {
    from { opacity: 0.5; }
    to { opacity: 1; }
  }

  .px-val {
    font-size: 13px;
    font-weight: 700;
    color: #f1f5f9;
  }

  /* Timeframe selector */
  .tf-selector-group {
    display: flex;
    align-items: center;
    background: #03060a;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 2px;
    gap: 2px;
  }

  .tf-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .tf-btn:hover {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.06);
  }

  .tf-btn.active {
    background: #f59e0b;
    color: #000000;
    font-weight: 800;
  }

  /* Right Side */
  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }


  .close-btn {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    width: 32px;
    height: 32px;
    border-radius: 6px;
    font-size: 15px;
    display: grid;
    place-items: center;
    cursor: pointer;
    transition: all 0.14s ease;
  }

  .close-btn:hover {
    background: rgba(244, 63, 94, 0.2);
    border-color: rgba(244, 63, 94, 0.5);
    color: #f43f5e;
  }

  /* Viewport */
  .chart-viewport {
    flex: 1 1 0;
    min-height: 0;
    position: relative;
    background: #060910;
  }

  .tv-iframe {
    width: 100%;
    height: 100%;
    border: none;
    display: block;
  }

  @media (max-width: 800px) {
    .chart-modal-card {
      height: 92vh;
      padding: 0;
    }
    .modal-header {
      flex-direction: column;
      align-items: stretch;
      gap: 10px;
    }
  }
</style>

