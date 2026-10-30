// Reactive Store using Svelte 5 Runes in .svelte.js
import { calculateForexPnl } from './formatters.js';

class ArenaStore {
  // Navigation & Market Mode
  mode = $state(
    window.location.pathname.includes('forex')
      ? 'forex'
      : (window.location.pathname.includes('futures') ? 'futures' : 'spot')
  );
  currentRoute = $state(
    window.location.pathname === '/' || window.location.pathname === ''
      ? 'landing'
      : (window.location.pathname.includes('neural-execution') || window.location.pathname.includes('executions')
          ? 'executions'
          : (window.location.pathname.includes('forex')
              ? 'forex'
              : (window.location.pathname.includes('futures') ? 'futures' : 'spot')))
  );

  // WebSocket Connection & Telemetry
  connected = $state(false);
  uptime = $state(0);
  symbolsCount = $state(100);
  totalTrades = $state(0);
  dbSize = $state('166.7 MB');
  activeApiKey = $state('pk_live_strategyarena_public_feed');

  // Runtime Config from Backend / .env
  config = $state({
    start_equity: 1000,
    universal_start_equity: 3000,
    risk_per_trade: 0.02,
    single_pos_cap: 0.20,
    sl_mult: 2.0,
    forex_target_risk: 15.0,
  });

  get startEquity() {
    return Number(this.config?.start_equity ?? 1000);
  }

  get universalStartEquity() {
    return Number(this.config?.universal_start_equity ?? (this.startEquity * 3));
  }

  // Engine States
  spot = $state({
    accounts: [],
    positions: [],
    curves: {},
    events: [],
    pairs: [],
  });

  futures = $state({
    accounts: [],
    positions: [],
    curves: {},
    events: [],
    pairs: [],
  });

  forex = $state({
    accounts: [],
    positions: [],
    curves: {},
    events: [],
    pairs: [],
  });

  // Pairs List
  pairs = $state([]);

  // Price Rings
  prices = $state({});
  priceChanges = $state({}); // tracks green/red flashes

  // UI State
  selectedStrategyId = $state(null);
  copyTradeModalOpen = $state(false);
  chartModalOpen = $state(false);
  chartModalSymbol = $state(null);
  chartModalCategory = $state(null);
  searchQuery = $state('');
  archetypeFilter = $state('all');
  sortBy = $state('equity');
  sortAsc = $state(false);

  // Internal WebSocket
  ws = null;
  reconnectTimer = null;
  uptimeInterval = null;
  pingInterval = null;

  constructor() {
    this.initModeFromUrl();
    this.startUptimeClock();
    this.fetchInitialMeta();
    this.pollLiveState();
    this.connectWs();

    // Polling interval 1 detik untuk menjamin state selalu update di semua halaman tanpa reload
    if (typeof window !== 'undefined') {
      setInterval(() => this.pollLiveState(), 1000);
      window.addEventListener('popstate', () => {
        this.initModeFromUrl();
      });
    }
  }

  async pollLiveState() {
    try {
      const res = await fetch('/api/state');
      if (res.ok) {
        const data = await res.json();
        this.handleMessage(data);
      }
    } catch {
      // offline fallback
    }
  }

  initModeFromUrl() {
    const path = window.location.pathname;
    if (path === '/' || path === '') {
      this.currentRoute = 'landing';
    } else if (path.includes('neural-execution') || path.includes('executions')) {
      this.currentRoute = 'executions';
    } else if (path.includes('forex')) {
      this.currentRoute = 'forex';
      this.mode = 'forex';
    } else if (path.includes('futures')) {
      this.currentRoute = 'futures';
      this.mode = 'futures';
    } else if (path.includes('spot')) {
      this.currentRoute = 'spot';
      this.mode = 'spot';
    }
  }

  navigate(path) {
    if (path === '/') {
      this.currentRoute = 'landing';
      window.history.pushState({}, '', '/');
    } else if (path === '/neural-execution' || path === '/executions') {
      this.currentRoute = 'executions';
      window.history.pushState({}, '', '/neural-execution');
    } else if (path === '/crypto-spot') {
      this.currentRoute = 'spot';
      this.mode = 'spot';
      localStorage.setItem('sa_mode', 'spot');
      window.history.pushState({}, '', '/crypto-spot');
    } else if (path === '/crypto-futures') {
      this.currentRoute = 'futures';
      this.mode = 'futures';
      localStorage.setItem('sa_mode', 'futures');
      window.history.pushState({}, '', '/crypto-futures');
    } else if (path === '/forex') {
      this.currentRoute = 'forex';
      this.mode = 'forex';
      localStorage.setItem('sa_mode', 'forex');
      window.history.pushState({}, '', '/forex');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  setMode(newMode) {
    this.mode = newMode;
    this.currentRoute = newMode;
    localStorage.setItem('sa_mode', newMode);
    const targetUrl = newMode === 'spot'
      ? '/crypto-spot'
      : (newMode === 'futures' ? '/crypto-futures' : '/forex');
    window.history.pushState({}, '', targetUrl);
  }

  startUptimeClock() {
    this.uptimeInterval = setInterval(() => {
      if (this.uptime > 0) {
        this.uptime += 1;
      }
    }, 1000);
  }

  async fetchInitialMeta() {
    try {
      const [resHealth, resKey, resConfig] = await Promise.all([
        fetch('/health'),
        fetch('/api/v1/auth/public-key'),
        fetch('/api/config'),
      ]);
      if (resHealth.ok) {
        const d = await resHealth.json();
        if (d.uptime) this.uptime = d.uptime;
        if (d.symbols) this.symbolsCount = d.symbols;
        if (d.db_size) this.dbSize = d.db_size;
        this.totalTrades = (d.spot_signals || 0) + (d.futures_signals || 0);
      }
      if (resKey.ok) {
        const d = await resKey.json();
        if (d.api_key) this.activeApiKey = d.api_key;
      }
      if (resConfig && resConfig.ok) {
        const cfg = await resConfig.json();
        if (cfg) this.config = { ...this.config, ...cfg };
      }
    } catch {
      // ignore offline fallback
    }
  }

  connectWs() {
    if (this.ws) {
      try {
        this.ws.close();
      } catch {}
    }

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${window.location.host}/ws`;

    try {
      this.ws = new WebSocket(url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.connected = true;
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      if (this.pingInterval) clearInterval(this.pingInterval);
      this.pingInterval = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          try {
            this.ws.send('ping');
          } catch {}
        }
      }, 15000);
    };

    this.ws.onclose = () => {
      this.connected = false;
      if (this.pingInterval) clearInterval(this.pingInterval);
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.connected = false;
    };

    this.ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        this.handleMessage(data);
      } catch (err) {
        console.error('WS parse error:', err);
      }
    };
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connectWs();
    }, 1500);
  }

  normalizePosition(p) {
    const sym = p.symbol || '';
    const side = (p.side === 1 || p.side === 'LONG' || p.side === 'buy') ? 'LONG' : 'SHORT';
    const entry = p.entry ?? p.entry_price ?? 0;
    const mark = this.prices[sym] ?? p.mark ?? p.mark_price ?? entry;
    const sideSign = side === 'LONG' ? 1 : -1;

    // Accurate MT5 Lot parsing (never divide an existing lot < 100 by 100)
    let lot = (p.lot != null && Number(p.lot) > 0) ? Number(p.lot) : null;
    if (lot == null && p.qty) {
      const q = Number(p.qty);
      if (q >= 1000) {
        lot = Number((q / 100000).toFixed(2));
      } else if (q > 0) {
        lot = Number(q.toFixed(2));
      }
    }

    const isForex = this.mode === 'forex' || p.mode === 'forex' || lot != null || (p.strategy && p.strategy.startsWith('fx_'));
    let upnl = 0;
    if (isForex) {
      upnl = calculateForexPnl(sym, entry, mark, side, lot || 0.10, this.prices);
    } else {
      upnl = p.qty > 0 && mark > 0 ? (mark - entry) * p.qty * sideSign : (p.upnl ?? p.pnl ?? 0);
    }
    const margin = p.margin_used ?? p.margin ?? p.notional ?? 0;
    const pnlPct = margin > 0 ? (upnl / margin) * 100 : 0;

    return {
      strategy: p.strategy,
      mode: p.mode || (isForex ? 'forex' : this.mode),
      symbol: sym,
      side,
      qty: p.qty ?? 0,
      lot: lot != null ? lot : (isForex ? 0.10 : null),
      entry,
      entry_price: entry,
      mark,
      mark_price: mark,
      stop: p.stop ?? p.stop_loss ?? null,
      stop_loss: p.stop ?? p.stop_loss ?? null,
      target: p.target ?? p.take_profit ?? null,
      take_profit: p.target ?? p.take_profit ?? null,
      margin,
      margin_used: margin,
      risk_amount: p.risk_amount ?? 0,
      leverage: p.leverage ?? 1,
      upnl: Math.round(upnl * 100) / 100,
      pnl: Math.round(upnl * 100) / 100,
      pnl_pct: pnlPct,
      opened_at: p.opened_at,
    };
  }

  handleMessage(msg) {
    if (!msg) return;

    if (msg.uptime != null) {
      this.uptime = msg.uptime;
    }
    if (msg.db_size) {
      this.dbSize = msg.db_size;
    } else if (msg.stats?.db_size) {
      this.dbSize = msg.stats.db_size;
    } else if (msg.feed?.db_size) {
      this.dbSize = msg.feed.db_size;
    }
    if (msg.stats) {
      this.totalTrades = (msg.stats.spot_signals || 0) + (msg.stats.futures_signals || 0) + (msg.stats.forex_signals || 0);
    }
    if (msg.prices) {
      this.updatePrices(msg.prices);
    }
    const inPairs = msg.pairs || msg.spot?.pairs || msg.futures?.pairs || msg.forex?.pairs;
    if (inPairs && Array.isArray(inPairs) && inPairs.length > 0) {
      this.pairs = inPairs;
    }

    if (msg.config) {
      this.config = { ...this.config, ...msg.config };
    }

    if (msg.type === 'hello' || msg.type === 'snapshot' || msg.type === 'state') {
      const startEq = this.startEquity;
      const mapAccounts = (rawList) => (rawList || []).map((a) => {
        const bal = a.balance ?? a.cash ?? a.equity ?? startEq;
        const initial = a.initial_balance ?? startEq;
        return {
          ...a,
          balance: bal,
          equity: a.equity ?? bal,
          ret: (bal - initial) / initial,
          returnPct: ((bal - initial) / initial) * 100,
          refillCount: a.mc_count ?? a.refill_count ?? 0,
        };
      });

      if (msg.spot) {
        this.spot = {
          accounts: mapAccounts(msg.spot.accounts),
          positions: (msg.spot.positions || []).map((p) => this.normalizePosition(p)),
          curves: msg.spot.curves || this.spot.curves || {},
          events: msg.spot.events || this.spot.events || [],
          pairs: msg.spot.pairs || this.spot.pairs || [],
        };
      }
      if (msg.futures) {
        this.futures = {
          accounts: mapAccounts(msg.futures.accounts),
          positions: (msg.futures.positions || []).map((p) => this.normalizePosition(p)),
          curves: msg.futures.curves || this.futures.curves || {},
          events: msg.futures.events || this.futures.events || [],
          pairs: msg.futures.pairs || this.futures.pairs || [],
        };
      }
      if (msg.forex) {
        this.forex = {
          accounts: mapAccounts(msg.forex.accounts),
          positions: (msg.forex.positions || []).map((p) => this.normalizePosition(p)),
          curves: msg.forex.curves || this.forex.curves || {},
          events: msg.forex.events || this.forex.events || [],
          pairs: msg.forex.pairs || this.forex.pairs || [],
        };
      }

      // Auto-select first strategy if none selected or previous one no longer exists
      const accts = this.activeAccounts;
      if (accts.length > 0) {
        if (!this.selectedStrategyId || !accts.some((a) => a.id === this.selectedStrategyId)) {
          const sorted = [...accts].sort((a, b) => (b.balance ?? b.cash ?? b.equity ?? 0) - (a.balance ?? a.cash ?? a.equity ?? 0));
          this.selectedStrategyId = sorted[0].id;
        }
      }
    } else if (msg.type === 'price_tick') {
      if (msg.prices) {
        this.updatePrices(msg.prices);
      }
    }
  }

  updatePrices(newPrices) {
    const changes = { ...this.priceChanges };
    for (const [sym, price] of Object.entries(newPrices)) {
      const prev = this.prices[sym];
      if (prev && prev !== price) {
        changes[sym] = price > prev ? 'up' : 'down';
      }
    }
    this.prices = { ...this.prices, ...newPrices };
    this.priceChanges = changes;
  }

  // Active dataset getter based on current mode
  get activeData() {
    if (this.mode === 'spot') return this.spot;
    if (this.mode === 'futures') return this.futures;
    if (this.mode === 'forex') return this.forex;
    return this.spot;
  }

  // Active accounts with return calculations
  get activeAccounts() {
    const startEq = this.startEquity;
    const accounts = this.activeData.accounts || [];
    return accounts.map((a) => {
      const bal = a.balance ?? a.cash ?? a.equity ?? startEq;
      const initial = a.initial_balance ?? startEq;
      const ret = (bal - initial) / initial;
      const refillCount = a.mc_count ?? a.refill_count ?? 0;
      return {
        ...a,
        balance: bal,
        returnPct: ret,
        refillCount,
      };
    });
  }

  // Spot accounts with return calculations
  get spotAccounts() {
    const startEq = this.startEquity;
    return (this.spot?.accounts || []).map((a) => {
      const bal = a.balance ?? a.cash ?? a.equity ?? startEq;
      const initial = a.initial_balance ?? startEq;
      const ret = (bal - initial) / initial;
      return {
        ...a,
        balance: bal,
        returnPct: ret,
      };
    });
  }

  // Futures accounts with return calculations
  get futuresAccounts() {
    const startEq = this.startEquity;
    return (this.futures?.accounts || []).map((a) => {
      const bal = a.balance ?? a.cash ?? a.equity ?? startEq;
      const initial = a.initial_balance ?? startEq;
      const ret = (bal - initial) / initial;
      return {
        ...a,
        balance: bal,
        returnPct: ret,
      };
    });
  }

  // Forex accounts with return calculations
  get forexAccounts() {
    const startEq = this.startEquity;
    return (this.forex?.accounts || []).map((a) => {
      const bal = a.balance ?? a.cash ?? a.equity ?? startEq;
      const initial = a.initial_balance ?? startEq;
      const ret = (bal - initial) / initial;
      return {
        ...a,
        balance: bal,
        returnPct: ret,
      };
    });
  }

  // Selected Strategy Object
  get selectedStrategy() {
    const accts = this.activeAccounts;
    if (!accts.length) return null;
    if (!this.selectedStrategyId) return accts[0];
    return accts.find((a) => a.id === this.selectedStrategyId) || accts[0];
  }

  // Selected Strategy Positions
  get selectedStrategyPositions() {
    const strat = this.selectedStrategy;
    if (!strat) return [];
    const pos = this.activeData.positions || [];
    return pos.filter((p) => p.strategy === strat.id);
  }

  // All open positions in current mode
  get allActivePositions() {
    return this.activeData.positions || [];
  }

  // Realtime events in current mode
  get activeEvents() {
    return this.activeData.events || [];
  }

  // Curves dictionary for sparklines and charts
  get activeCurves() {
    return this.activeData.curves || {};
  }

  // Active pairs list
  get activePairs() {
    if (this.mode === 'forex') {
      const fx = this.forex?.pairs;
      if (fx && Array.isArray(fx) && fx.length > 0) return fx;
    } else if (this.mode === 'futures') {
      const fut = this.futures?.pairs;
      if (fut && Array.isArray(fut) && fut.length > 0) return fut;
    } else {
      const spt = this.spot?.pairs;
      if (spt && Array.isArray(spt) && spt.length > 0) return spt;
    }
    if (this.pairs && Array.isArray(this.pairs) && this.pairs.length > 0) return this.pairs;
    const syms = Object.keys(this.prices || {});
    if (syms.length > 0) {
      return syms.map((s, idx) => ({
        symbol: s,
        base: s.replace('USDT', ''),
        quote: 'USDT',
        rank: idx + 1,
        quote_volume: 50000000,
        last_close: this.prices[s] || 0,
      }));
    }
    return [];
  }

  // Open TradingView Chart Modal
  openChart(symbol, category = null) {
    if (!symbol) return;
    this.chartModalSymbol = symbol;
    this.chartModalCategory = category;
    this.chartModalOpen = true;
  }

  // Close TradingView Chart Modal
  closeChart() {
    this.chartModalOpen = false;
    this.chartModalSymbol = null;
    this.chartModalCategory = null;
  }
}

export const arena = new ArenaStore();
