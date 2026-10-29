"""
Centralized Configuration for Strategy Arena.
Loads variables from .env if available, with robust system environment fallback.
"""
import os
from pathlib import Path


def _load_env_file():
    """Load key-value pairs from .env into os.environ if not already set."""
    candidates = [
        Path(".env"),
        Path(__file__).resolve().parent.parent / ".env",
        Path("/app/.env"),
        Path("/var/www/strategy-arena/.env"),
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
                break
            except Exception:
                pass


_load_env_file()

# Arena Capital & Risk Management
START_EQUITY = float(os.getenv("START_EQUITY", "1000.0"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.02"))
SINGLE_POS_CAP = float(os.getenv("SINGLE_POS_CAP", "0.20"))
SL_MULT = float(os.getenv("SL_MULT", "2.0"))
FOREX_TARGET_RISK = float(os.getenv("FOREX_TARGET_RISK", "15.0"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://arena:arena@db:5432/arena")

# Binance Feeds
ARENA_BINANCE_REST = os.getenv("ARENA_BINANCE_REST", "https://data-api.binance.vision")
ARENA_BINANCE_WS = os.getenv("ARENA_BINANCE_WS", "wss://data-stream.binance.vision")
ARENA_PAIRS = int(os.getenv("ARENA_PAIRS", "100"))
ARENA_WARMUP_MIN = int(os.getenv("ARENA_WARMUP_MIN", "0"))
ARENA_SNAPSHOT_SEC = float(os.getenv("ARENA_SNAPSHOT_SEC", "2.0"))
SNAPSHOT_SEC = ARENA_SNAPSHOT_SEC

# MT5 & Forex
MT5_BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://mt5-bridge:5000")
MT5_RPYC_HOST = os.getenv("MT5_RPYC_HOST", "mt5-vnc")
MT5_RPYC_PORT = int(os.getenv("MT5_RPYC_PORT", "18812"))
MT5_LOGIN = os.getenv("MT5_LOGIN", "6310591")
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "dL7ny!PE")
MT5_SERVER = os.getenv("MT5_SERVER", "Headway-Demo")


def get_client_config() -> dict:
    """Return public config dictionary passed to frontend web clients."""
    return {
        "start_equity": START_EQUITY,
        "risk_per_trade": RISK_PER_TRADE,
        "single_pos_cap": SINGLE_POS_CAP,
        "sl_mult": SL_MULT,
        "forex_target_risk": FOREX_TARGET_RISK,
        "universal_start_equity": START_EQUITY * 3.0,
        "arena_pairs": ARENA_PAIRS,
        "snapshot_sec": ARENA_SNAPSHOT_SEC,
    }
