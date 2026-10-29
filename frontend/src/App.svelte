<script>
  import Header from './components/Header.svelte';
  import TickerBar from './components/TickerBar.svelte';
  import BoardGrid from './components/BoardGrid.svelte';
  import StrategyDossier from './components/StrategyDossier.svelte';
  import OpenPositionsDesk from './components/OpenPositionsDesk.svelte';
  import MarketPairs from './components/MarketPairs.svelte';
  import RealtimeLogs from './components/RealtimeLogs.svelte';
  import CopyTradeModal from './components/CopyTradeModal.svelte';
  import TradingViewChartModal from './components/TradingViewChartModal.svelte';
  import LandingPage from './components/LandingPage.svelte';
  import NeuralExecutionPage from './components/NeuralExecutionPage.svelte';
  import { arena } from './lib/store.svelte.js';

  let totalTrades = $derived(arena.totalTrades);
  let openPositionsCount = $derived(arena.allActivePositions.length);
</script>

{#if arena.currentRoute === 'landing'}
  <LandingPage />
{:else if arena.currentRoute === 'executions'}
  <div class="app-shell">
    <Header />
    <TickerBar />
    <NeuralExecutionPage />
  </div>
{:else}
  <div class="app-shell">
    <!-- Top Navigation & Market Switcher (Modern Header) -->
    <Header />

    <!-- Live Binance Spot/Futures / MT5 Forex Ticker Bar -->
    <TickerBar />

    <!-- Main Trading Floor Shell -->
    <main class="trading-floor">
      <!-- Papan Peringkat: The Beloved 7-Column Card Grid with Sparklines -->
      <BoardGrid />

      <!-- Split Trading Desk: Selected Strategy Dossier + Pair Yang Sedang Diperdagangkan (Equal Height) -->
      <div class="grid desk-grid">
        <div class="cell desk-left">
          <StrategyDossier />
        </div>
        <div class="cell desk-right">
          <OpenPositionsDesk />
        </div>
      </div>

      <!-- Split Market & Realtime Logs: Pasar Pair + Log Realtime (Equal Height) -->
      <div class="grid market-logs-grid">
        <div class="cell bottom-left">
          <MarketPairs />
        </div>
        <div class="cell bottom-right">
          <RealtimeLogs />
        </div>
      </div>

      <!-- Institutional Footer Bar -->
      <footer class="floor-foot">
        <span class="foot-left">
          Data: {arena.mode === 'forex' ? 'MT5 Realtime Feed' : 'Binance REST + WebSocket'} · Database menyimpan candle, akun, trade, kurva ekuitas
        </span>
        <span class="foot-right mono">
          {openPositionsCount} posisi terbuka
        </span>
      </footer>
    </main>

    <!-- Copy-Trade API Key Modal -->
    <CopyTradeModal />
  </div>
{/if}

<!-- Global TradingView Chart Modal (Tanpa Tools, Publik) -->
<TradingViewChartModal />

<style>
  .app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: var(--bg-base);
  }

  .trading-floor {
    display: flex;
    flex-direction: column;
    padding: 10px 16px 24px 16px;
    flex: 1;
    max-width: 1740px;
    width: 100%;
    margin: 0 auto;
    box-sizing: border-box;
  }

  .grid {
    display: grid;
    gap: 12px;
    align-items: stretch; /* Enforces 100% equal height on both containers */
  }

  /* Desk Grid: Dossier + Pair Yang Sedang Diperdagangkan */
  .desk-grid {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    height: 480px;
    max-height: 480px;
    min-height: 480px;
    margin-bottom: 12px;
    overflow: hidden;
  }

  /* Market & Logs Grid: Pasar + Log Realtime */
  .market-logs-grid {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    height: 380px;
    max-height: 380px;
    min-height: 380px;
    margin-bottom: 12px;
    overflow: hidden;
  }

  .cell {
    min-width: 0;
    min-height: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .floor-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 14px 6px 14px;
    font-size: 11px;
    color: #64748b;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    margin-top: 4px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .foot-right {
    color: #94a3b8;
  }

  @media (max-width: 1100px) {
    .desk-grid,
    .market-logs-grid {
      grid-template-columns: minmax(0, 1fr);
      height: auto;
      min-height: auto;
      max-height: none;
      overflow: visible;
    }
    .cell {
      height: 480px;
      min-height: 480px;
    }
  }

  @media (max-width: 768px) {
    .trading-floor {
      padding: 8px 10px 20px 10px;
    }
    .desk-grid,
    .market-logs-grid {
      max-height: none;
      overflow: visible;
    }
    .cell {
      height: 460px;
      min-height: 460px;
    }
  }
</style>
