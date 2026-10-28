"""MetaTrader 5 Realtime Bridge Service
Menghubungkan terminal MetaTrader 5 (Headway-Demo / Broker) langsung ke Strategy Arena.
Menyediakan REST API di port 5000 (localhost:5000 dan host.docker.internal:5000).
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

try:
    # pyrefly: ignore[missing-import]
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("mt5-bridge")

TERMINAL_PATH = os.getenv("MT5_TERMINAL_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
PORT = int(os.getenv("MT5_BRIDGE_PORT", "5000"))

# Mapping pair arena -> symbol broker
SYMBOL_MAP = {
    "USOIL": "XTIUSD",
}

REVERSE_MAP = {v: k for k, v in SYMBOL_MAP.items()}

FOREX_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "GBPJPY", "EURJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
    "EURGBP", "EURCHF", "GBPCHF", "AUDNZD", "AUDCAD", "EURAUD", "GBPAUD",
    "XAUUSD", "USOIL"
]

state = {
    "initialized": False,
    "account": None,
    "last_error": None,
}


def init_mt5() -> bool:
    if not MT5_AVAILABLE:
        log.error("Package MetaTrader5 tidak terinstall di Python.")
        return False
    try:
        ok = mt5.initialize(path=TERMINAL_PATH)
        if not ok:
            err = mt5.last_error()
            log.warning("Gagal initialize MT5 di %s: %s", TERMINAL_PATH, err)
            # Coba tanpa path jika terminal sudah jalan
            ok = mt5.initialize()
        if ok:
            acc = mt5.account_info()
            state["initialized"] = True
            state["account"] = acc._asdict() if acc else {}
            log.info("✓ Terhubung ke MetaTrader 5! Broker: %s | Akun: %s (%s)",
                     state["account"].get("server"), state["account"].get("login"), state["account"].get("name"))
            # Subscribe symbols ke MarketWatch
            for s in FOREX_PAIRS:
                broker_sym = SYMBOL_MAP.get(s, s)
                mt5.symbol_select(broker_sym, True)
            return True
        else:
            state["last_error"] = str(mt5.last_error())
            return False
    except Exception as exc:
        log.error("Exception saat init MT5: %s", exc)
        state["last_error"] = str(exc)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    log.info("Memulai MT5 Realtime Bridge di port %d...", PORT)
    # Start MT5 initialization in background thread so server binds port immediately
    asyncio.create_task(asyncio.to_thread(init_mt5))
    yield
    if MT5_AVAILABLE and state["initialized"]:
        try:
            mt5.shutdown()
            log.info("MT5 koneksi ditutup dengan aman.")
        except Exception:
            pass


app = FastAPI(title="MetaTrader 5 Realtime Bridge", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    is_ok = state["initialized"]
    acc = state.get("account") or {}
    return {
        "status": "healthy" if is_ok else "degraded",
        "connected": is_ok,
        "broker": acc.get("server", "Unknown"),
        "login": acc.get("login"),
        "name": acc.get("name"),
        "currency": acc.get("currency"),
        "balance": acc.get("balance"),
        "leverage": acc.get("leverage"),
        "error": state.get("last_error"),
    }


@app.get("/ticks")
def get_all_ticks():
    """Mengambil seluruh tick realtime untuk 22 pair Forex & Metals."""
    if not state["initialized"] and not init_mt5():
        raise HTTPException(status_code=503, detail="MT5 tidak terhubung")

    out = {}
    for sym in FOREX_PAIRS:
        broker_sym = SYMBOL_MAP.get(sym, sym)
        tick = mt5.symbol_info_tick(broker_sym)
        if tick:
            bid = float(tick.bid)
            ask = float(tick.ask)
            last = float(tick.last) if tick.last > 0 else (bid + ask) / 2.0
            out[sym] = {
                "symbol": sym,
                "broker_symbol": broker_sym,
                "bid": bid,
                "ask": ask,
                "last": last,
                "price": last,
                "spread": round(ask - bid, 5),
                "volume": int(tick.volume),
                "time": int(tick.time),
                "time_msc": int(tick.time_msc),
            }
    return out


@app.get("/symbol_info_tick/{symbol}")
def get_symbol_tick(symbol: str):
    """Kompatibilitas dengan route metatrader5-quant-server-python."""
    if not state["initialized"] and not init_mt5():
        raise HTTPException(status_code=503, detail="MT5 tidak terhubung")

    sym = symbol.upper()
    broker_sym = SYMBOL_MAP.get(sym, sym)
    tick = mt5.symbol_info_tick(broker_sym)
    if not tick:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} tidak ditemukan di broker")

    bid = float(tick.bid)
    ask = float(tick.ask)
    last = float(tick.last) if tick.last > 0 else (bid + ask) / 2.0
    return {
        "bid": bid,
        "ask": ask,
        "last": last,
        "volume": int(tick.volume),
        "time": int(tick.time),
    }


@app.get("/fetch_data_pos")
def fetch_data_pos(symbol: str = Query(...), timeframe: str = Query("M1"), num_bars: int = Query(100)):
    """Mengambil bar historis langsung dari broker MT5."""
    if not state["initialized"] and not init_mt5():
        raise HTTPException(status_code=503, detail="MT5 tidak terhubung")

    sym = symbol.upper()
    broker_sym = SYMBOL_MAP.get(sym, sym)

    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "D1": mt5.TIMEFRAME_D1,
    }
    tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_M1)
    rates = mt5.copy_rates_from_pos(broker_sym, tf, 0, min(num_bars, 1000))
    if rates is None or len(rates) == 0:
        return []

    out = []
    for r in rates:
        out.append({
            "time": int(r["time"]),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "tick_volume": int(r["tick_volume"]),
            "spread": int(r["spread"]),
        })
    return out


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
