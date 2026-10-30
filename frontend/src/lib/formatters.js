export function formatUSD(v, decimals = 2) {
  if (v === null || v === undefined || isNaN(v)) return '$0.00';
  return '$' + Number(v).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(v, withSign = true) {
  if (v === null || v === undefined || isNaN(v)) return '0.0%';
  const num = Number(v) * (Math.abs(v) < 1 ? 100 : 1);
  const sign = withSign && num > 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
}

export function formatPrice(p, maxDecimals = null) {
  if (p === null || p === undefined || isNaN(p)) return '0.00';
  const num = Number(p);
  if (maxDecimals !== null) return num.toFixed(maxDecimals);
  if (num >= 1000) return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (num >= 200) return num.toFixed(2);
  if (num >= 20) return num.toFixed(3);
  if (num >= 1) return num.toFixed(5);
  if (num >= 0.001) return num.toFixed(5);
  return num.toFixed(7);
}

export function formatForexPrice(p, symbol) {
  if (p === null || p === undefined || isNaN(p)) return '—';
  const num = Number(p);
  const sym = (symbol || '').toUpperCase();
  const is3Dec = sym.includes('JPY') ||
                 sym.includes('XAU') ||
                 sym.includes('GOLD') ||
                 sym.includes('XAG') ||
                 sym.includes('SILVER') ||
                 sym.includes('XTI') ||
                 sym.includes('OIL') ||
                 sym.includes('USOIL');
  return num.toFixed(is3Dec ? 3 : 5);
}

export function formatUptime(seconds) {
  if (!seconds || seconds <= 0) return '00:00';
  const s = Math.floor(seconds);
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  if (hrs > 0) {
    return `${hrs}j ${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`;
  }
  return `${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s`;
}

const wibTimeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Jakarta',
  hour12: false,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

export function formatClock(ts) {
  if (!ts) return '—';
  const ms = ts > 1e12 ? ts : ts * 1000;
  const d = new Date(ms);
  if (isNaN(d.getTime())) return '—';
  return `${wibTimeFormatter.format(d)} WIB`;
}

export function formatClockWIB(ts) {
  return formatClock(ts);
}

export function formatFullDateTime(ts) {
  if (!ts) return '';
  const ms = ts > 1e12 ? ts : ts * 1000;
  const d = new Date(ms);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleString('id-ID', {
    timeZone: 'Asia/Jakarta',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }) + ' WIB';
}

export function formatTimeAgo(ts) {
  if (!ts) return '';
  const now = Date.now();
  const diffSec = Math.floor((now - (ts > 1e12 ? ts : ts * 1000)) / 1000);
  if (diffSec < 5) return 'baru saja';
  if (diffSec < 60) return `${diffSec}s lalu`;
  const mins = Math.floor(diffSec / 60);
  if (mins < 60) return `${mins}m lalu`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}j lalu`;
  const days = Math.floor(hrs / 24);
  return `${days}h lalu`;
}

export function calculateForexPips(symbol, entry, mark, side) {
  if (!entry || !mark) return 0;
  const sym = (symbol || '').toUpperCase();
  let pipSize = 0.0001;
  if (sym.includes('JPY') || sym === 'USOIL' || sym.includes('XTI')) {
    pipSize = 0.01;
  } else if (sym.includes('XAU') || sym.includes('GOLD')) {
    pipSize = 0.1;
  }
  const sideSign = (side === 'LONG' || side === 1 || side === 'buy') ? 1 : -1;
  return ((Number(mark) - Number(entry)) * sideSign) / pipSize;
}

export function calculateForexPnl(symbol, entry, mark, side, lot = 0.10, prices = {}) {
  if (!entry || !mark) return 0;
  const sym = (symbol || '').toUpperCase();
  const sideSign = (side === 'LONG' || side === 1 || side === 'buy') ? 1 : -1;
  const diff = (Number(mark) - Number(entry)) * sideSign;
  const numLot = Number(lot) || 0.10;

  let cSize = 100000;
  if (sym.includes('XAU') || sym.includes('GOLD')) cSize = 100;
  else if (sym.includes('XAG') || sym.includes('SILVER')) cSize = 5000;
  else if (sym.includes('XTI') || sym.includes('USO') || sym.includes('WTI') || sym.includes('OIL')) cSize = 1000;

  const basePnl = diff * (numLot * cSize);

  const getPx = (s, fallback) => {
    const v = prices[s];
    if (v == null) return fallback;
    return typeof v === 'object' ? (Number(v.price) || fallback) : (Number(v) || fallback);
  };

  if (sym.endsWith('USD')) return basePnl;
  if (sym.endsWith('JPY')) {
    const usdjpy = getPx('USDJPY', 158.0);
    return basePnl / Math.max(usdjpy, 1.0);
  }
  if (sym.endsWith('CAD')) {
    const usdcad = getPx('USDCAD', 1.40);
    return basePnl / Math.max(usdcad, 0.1);
  }
  if (sym.endsWith('CHF')) {
    const usdchf = getPx('USDCHF', 0.83);
    return basePnl / Math.max(usdchf, 0.1);
  }
  if (sym.endsWith('GBP')) {
    const gbpusd = getPx('GBPUSD', 1.33);
    return basePnl * gbpusd;
  }
  if (sym.endsWith('NZD')) {
    const nzdusd = getPx('NZDUSD', 0.56);
    return basePnl * nzdusd;
  }
  if (sym.endsWith('AUD')) {
    const audusd = getPx('AUDUSD', 0.70);
    return basePnl * audusd;
  }
  return basePnl;
}


