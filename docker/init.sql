-- Strategy Arena — skema database (multi-aset: crypto, saham, forex)
-- Semua waktu disimpan sebagai BIGINT epoch milliseconds (UTC).

CREATE TABLE IF NOT EXISTS pairs (
    symbol          TEXT PRIMARY KEY,
    base            TEXT NOT NULL,
    quote           TEXT NOT NULL,
    rank            INTEGER NOT NULL DEFAULT 9999,
    quote_volume    DOUBLE PRECISION NOT NULL DEFAULT 0,
    last_close      DOUBLE PRECISION,
    updated_at      BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bars (
    symbol  TEXT NOT NULL REFERENCES pairs(symbol) ON DELETE CASCADE,
    open_t  BIGINT NOT NULL,
    o       DOUBLE PRECISION NOT NULL,
    h       DOUBLE PRECISION NOT NULL,
    l       DOUBLE PRECISION NOT NULL,
    c       DOUBLE PRECISION NOT NULL,
    v       DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (symbol, open_t)
);
CREATE INDEX IF NOT EXISTS bars_open_t ON bars (open_t DESC);

CREATE TABLE IF NOT EXISTS accounts (
    strategy    TEXT PRIMARY KEY,
    equity      DOUBLE PRECISION NOT NULL,
    cash        DOUBLE PRECISION NOT NULL,
    peak        DOUBLE PRECISION NOT NULL,
    max_dd      DOUBLE PRECISION NOT NULL DEFAULT 0,
    trades      INTEGER NOT NULL DEFAULT 0,
    wins        INTEGER NOT NULL DEFAULT 0,
    gross_win   DOUBLE PRECISION NOT NULL DEFAULT 0,
    gross_loss  DOUBLE PRECISION NOT NULL DEFAULT 0,
    realized    DOUBLE PRECISION NOT NULL DEFAULT 0,
    updated_at  BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS positions (
    strategy    TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        SMALLINT NOT NULL,
    qty         DOUBLE PRECISION NOT NULL,
    entry       DOUBLE PRECISION NOT NULL,
    stop        DOUBLE PRECISION,
    target      DOUBLE PRECISION,
    opened_at   BIGINT NOT NULL,
    notional    DOUBLE PRECISION NOT NULL,
    risk_amount DOUBLE PRECISION NOT NULL,
    reason      TEXT,
    PRIMARY KEY (strategy, symbol)
);

CREATE TABLE IF NOT EXISTS trades (
    id          BIGSERIAL PRIMARY KEY,
    strategy    TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        SMALLINT NOT NULL,
    qty         DOUBLE PRECISION NOT NULL,
    entry       DOUBLE PRECISION NOT NULL,
    exit        DOUBLE PRECISION NOT NULL,
    opened_at   BIGINT NOT NULL,
    closed_at   BIGINT NOT NULL,
    pnl         DOUBLE PRECISION NOT NULL,
    fee         DOUBLE PRECISION NOT NULL,
    reason      TEXT NOT NULL,
    equity_after DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS trades_strategy_closed ON trades (strategy, closed_at DESC);
CREATE INDEX IF NOT EXISTS trades_closed ON trades (closed_at DESC);

CREATE TABLE IF NOT EXISTS equity_curve (
    strategy   TEXT NOT NULL,
    ts         BIGINT NOT NULL,
    equity     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (strategy, ts)
);

CREATE TABLE IF NOT EXISTS events (
    id         BIGSERIAL PRIMARY KEY,
    ts         BIGINT NOT NULL,
    strats     TEXT[] NOT NULL DEFAULT '{}',
    symbol     TEXT,
    kind       TEXT NOT NULL,
    message    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_ts ON events (ts DESC);
