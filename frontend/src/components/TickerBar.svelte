<script>
  import { arena } from '../lib/store.svelte.js';
  import { formatPrice } from '../lib/formatters.js';

  // Dynamic top pairs from Binance feed, default fallback to top crypto
  let pairs = $derived.by(() => {
    const list = arena.activePairs;
    if (list && list.length > 0) {
      return list.slice(0, 36);
    }
    return [
      { symbol: 'BTCUSDT', base: 'BTC' },
      { symbol: 'ETHUSDT', base: 'ETH' },
      { symbol: 'SOLUSDT', base: 'SOL' },
      { symbol: 'BNBUSDT', base: 'BNB' },
      { symbol: 'XRPUSDT', base: 'XRP' },
      { symbol: 'DOGEUSDT', base: 'DOGE' },
      { symbol: 'ADAUSDT', base: 'ADA' },
      { symbol: 'AVAXUSDT', base: 'AVAX' },
      { symbol: 'SUIUSDT', base: 'SUI' },
      { symbol: 'NEARUSDT', base: 'NEAR' },
      { symbol: 'LINKUSDT', base: 'LINK' },
      { symbol: 'PEPEUSDT', base: 'PEPE' },
      { symbol: 'APTUSDT', base: 'APT' },
      { symbol: 'OPUSDT', base: 'OP' },
      { symbol: 'ARBUSDT', base: 'ARB' },
      { symbol: 'AAVEUSDT', base: 'AAVE' },
      { symbol: 'DOTUSDT', base: 'DOT' },
      { symbol: 'LTCUSDT', base: 'LTC' },
      { symbol: 'ENAUSDT', base: 'ENA' },
      { symbol: 'WLDUSDT', base: 'WLD' },
    ];
  });

  let isFutures = $derived(arena.mode === 'futures');
  let isForex = $derived(arena.mode === 'forex');
</script>

<div class="ticker-bar-root">
  <!-- Market Mode Identifier Pill -->
  <div class="ticker-label">
    <span class="dot {isForex ? 'dot-forex' : (isFutures ? 'dot-futures' : 'dot-spot')}">●</span>
    <span class="label-text">{isForex ? 'FOREX & METALS' : (isFutures ? 'FUTURES PAIRS' : 'SPOT PAIRS')}</span>
  </div>

  <!-- Infinite Smooth Animated Marquee Ticker -->
  <div class="marquee-viewport">
    <div class="marquee-track">
      <!-- First Copy -->
      <div class="marquee-group">
        {#each pairs as p (p.symbol + '_g1')}
          {@const price = arena.prices[p.symbol] ?? p.last_close}
          {@const flash = arena.priceChanges[p.symbol]}
          {@const dec = p.digits ?? (p.symbol.includes('JPY') || p.symbol === 'USOIL' ? 3 : (p.symbol === 'XAUUSD' ? 2 : 5))}
          {@const bid = p.bid ?? price}
          {@const ask = p.ask ?? (price && p.spread ? price + p.spread : price)}
          {@const spr = p.spread_pips ?? '0.8'}
          <div class="ticker-item {isForex ? 'ticker-item-fx' : ''}">
            <span class="ticker-sym">{isForex ? p.symbol : (p.base || p.symbol.replace('USDT', ''))}</span>
            {#if isForex}
              <div class="fx-ticker-3row mono {flash === 'up' ? 'flash-up' : flash === 'down' ? 'flash-down' : ''}">
                <span class="fx-b">B {bid ? Number(bid).toFixed(dec) : '---'}</span>
                <span class="fx-a">A {ask ? Number(ask).toFixed(dec) : '---'}</span>
                <span class="fx-s">{spr}p</span>
              </div>
            {:else}
              <span class="ticker-price mono {flash === 'up' ? 'flash-up' : flash === 'down' ? 'flash-down' : ''}">
                ${price ? formatPrice(price) : '---'}
              </span>
            {/if}
          </div>
        {/each}
      </div>

      <!-- Second Duplicate Copy for Seamless Infinite Loop -->
      <div class="marquee-group" aria-hidden="true">
        {#each pairs as p (p.symbol + '_g2')}
          {@const price = arena.prices[p.symbol] ?? p.last_close}
          {@const flash = arena.priceChanges[p.symbol]}
          {@const dec = p.digits ?? (p.symbol.includes('JPY') || p.symbol === 'USOIL' ? 3 : (p.symbol === 'XAUUSD' ? 2 : 5))}
          {@const bid = p.bid ?? price}
          {@const ask = p.ask ?? (price && p.spread ? price + p.spread : price)}
          {@const spr = p.spread_pips ?? '0.8'}
          <div class="ticker-item {isForex ? 'ticker-item-fx' : ''}">
            <span class="ticker-sym">{isForex ? p.symbol : (p.base || p.symbol.replace('USDT', ''))}</span>
            {#if isForex}
              <div class="fx-ticker-3row mono {flash === 'up' ? 'flash-up' : flash === 'down' ? 'flash-down' : ''}">
                <span class="fx-b">B {bid ? Number(bid).toFixed(dec) : '---'}</span>
                <span class="fx-a">A {ask ? Number(ask).toFixed(dec) : '---'}</span>
                <span class="fx-s">{spr}p</span>
              </div>
            {:else}
              <span class="ticker-price mono {flash === 'up' ? 'flash-up' : flash === 'down' ? 'flash-down' : ''}">
                ${price ? formatPrice(price) : '---'}
              </span>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  .ticker-bar-root {
    display: flex;
    align-items: center;
    background-color: #05080e;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    height: 32px;
    font-size: 11px;
    overflow: hidden;
    position: relative;
    user-select: none;
  }

  .ticker-label {
    display: flex;
    align-items: center;
    gap: 7px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 0.06em;
    color: #94a3b8;
    padding: 0 16px;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    white-space: nowrap;
    background: #05080e;
    z-index: 10;
    flex-shrink: 0;
    height: 100%;
  }

  .dot {
    font-size: 8px;
  }

  .dot-spot {
    color: #fbbf24;
    text-shadow: 0 0 6px rgba(251, 191, 36, 0.6);
  }

  .dot-futures {
    color: #38bdf8;
    text-shadow: 0 0 6px rgba(56, 189, 248, 0.6);
  }

  .dot-forex {
    color: #10b981;
    text-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
  }

  .label-text {
    color: #e2e8f0;
    font-family: var(--font-display, inherit);
  }

  /* Viewport with smooth fading edge masks */
  .marquee-viewport {
    flex: 1;
    overflow: hidden;
    height: 100%;
    display: flex;
    align-items: center;
    mask-image: linear-gradient(
      90deg,
      transparent 0%,
      black 24px,
      black calc(100% - 24px),
      transparent 100%
    );
    -webkit-mask-image: linear-gradient(
      90deg,
      transparent 0%,
      black 24px,
      black calc(100% - 24px),
      transparent 100%
    );
  }

  /* Track with continuous linear movement */
  .marquee-track {
    display: flex;
    width: max-content;
    will-change: transform;
    animation: marquee-scroll 45s linear infinite;
  }

  .marquee-track:hover {
    animation-play-state: paused;
  }

  .marquee-group {
    display: flex;
    align-items: center;
    gap: 22px;
    padding-right: 22px;
    flex-shrink: 0;
  }

  .ticker-item {
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }

  .ticker-item-fx {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 1px 6px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 4px;
  }

  .fx-ticker-3row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
  }

  .fx-b {
    color: #38bdf8;
  }

  .fx-a {
    color: #f43f5e;
  }

  .fx-s {
    color: #10b981;
    font-size: 9.5px;
    font-weight: 700;
    background: rgba(16, 185, 129, 0.12);
    padding: 1px 4px;
    border-radius: 3px;
  }

  .ticker-sym {
    font-weight: 700;
    font-size: 11px;
    color: #64748b;
    letter-spacing: 0.02em;
  }

  .ticker-price {
    font-weight: 600;
    font-size: 11.5px;
    color: #e2e8f0;
    transition: color 0.3s ease;
  }

  .flash-up {
    color: #10b981 !important;
    text-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
  }

  .flash-down {
    color: #f43f5e !important;
    text-shadow: 0 0 8px rgba(244, 63, 94, 0.4);
  }

  @keyframes marquee-scroll {
    0% {
      transform: translateX(0%);
    }
    100% {
      transform: translateX(-50%);
    }
  }
</style>
