"""Engine 50 strategi × seluruh pair. Dual mode: Spot dan Futures.

Spot mode:
  - Hanya LONG, fee 0.05% per sisi, no leverage, no funding.

Futures mode:
  - LONG + SHORT, leverage configurable per strategi (3x-20x).
  - Fee taker 0.05%, funding rate 0.01% per 8 jam.
  - Margin = notional / leverage. Liquidation jika equity <= 0.

Risk management (kedua mode):
  - Risiko 2% equity per trade, total notional ≤ 100% equity, total risk ≤ 20%.
"""

from __future__ import annotations

import time
from typing import Iterable

from .bars import BarRing
from .indicators import compute
from .strategies import (
    LONG, MAX_POS, SHORT, SIGNAL_FN, STRATEGY_IDS, STRATEGY_META, THRESHOLD,
    SINGLE_POS_CAP, TOTAL_NOTIONAL_CAP, TOTAL_RISK_CAP, DEFAULT_LEVERAGE,
    SPOT_FEE, FUTURES_TAKER_FEE, FUNDING_RATE_DEFAULT, FUNDING_INTERVAL_SEC,
    SPOT_STRATEGIES, FUTURES_STRATEGIES, FOREX_STRATEGIES, get_strategy_rr,
)

START_EQUITY = 10_000.0
RISK = 0.02
SL_MULT = 2.0
MIN_BARS = 210  # butuh EMA200 dulu

STRAT_COLORS = [
    "#f0a03c", "#5b9bf0", "#2bb98a", "#d377c4", "#f07a52", "#8f80ff", "#2fb3b3", "#a8b32b",
    "#ef6257", "#8a94a3", "#e9c46a", "#69d2e7", "#f4a261", "#a3c4f3", "#7bd389", "#c9ada7",
    "#ffb4a2", "#b5838d", "#90be6d", "#4cc9f0", "#f72585", "#7209b7", "#3a86ff", "#ffbe0b",
    "#fb5607", "#06d6a0", "#118ab2", "#ef476f", "#8338ec", "#ff006e", "#00b4d8", "#c1fba4",
    "#ffd166", "#06d6a0", "#8ecae6", "#bde0fe", "#ffafcc", "#cdb4db", "#e9edc9", "#a3b18a",
    "#6d6875", "#b56576", "#457b9d", "#e76f51", "#e9c46a", "#2a9d8f", "#4a4e69", "#9a8c98",
    "#8ecae6", "#f28482",
]


def _new_account(idx: int, mode: str = "spot") -> dict:
    sid = STRATEGY_IDS[idx]
    if mode == "forex":
        leverage = 1
        fee = 0.0  # Di Forex, biaya trading murni spread bid/ask MT5
    elif mode == "futures":
        leverage = DEFAULT_LEVERAGE.get(sid, 5)
        fee = FUTURES_TAKER_FEE
    else:
        leverage = 1
        fee = SPOT_FEE
    return {
        "id": sid,
        "name": STRATEGY_META[sid]["name"],
        "family": STRATEGY_META[sid]["family"],
        "color": STRAT_COLORS[idx % len(STRAT_COLORS)],
        "mode": mode,
        "leverage": leverage,
        "fee_rate": fee,
        "equity": START_EQUITY,
        "cash": START_EQUITY,
        "peak": START_EQUITY,
        "max_dd": 0.0,
        "trades": 0,
        "wins": 0,
        "gross_win": 0.0,
        "gross_loss": 0.0,
        "realized": 0.0,
        "funding_paid": 0.0,
        "mc_count": 0,
        "pos": {},          # symbol -> position dict
        "pending": None,
        "warmed": False,
    }


class Engine:
    def __init__(self, rings: dict[str, BarRing], mode: str = "spot") -> None:
        self.mode = mode  # "spot", "futures", or "forex"
        self.rings = rings
        if mode == "forex":
            self.strategy_ids = FOREX_STRATEGIES
        elif mode == "futures":
            self.strategy_ids = FUTURES_STRATEGIES
        else:
            self.strategy_ids = SPOT_STRATEGIES
        self.accounts: dict[str, dict] = {}
        for i, sid in enumerate(STRATEGY_IDS):
            if sid in self.strategy_ids:
                self.accounts[sid] = _new_account(i, mode)
        self.events: list[dict] = []
        self.new_trades: list[dict] = []
        self.signals: list[dict] = []
        self.new_signals: list[dict] = []
        self.curve: dict[str, list[tuple[int, float]]] = {sid: [] for sid in self.strategy_ids}
        self.sparklines: dict[str, list[float]] = {sid: [START_EQUITY] for sid in self.strategy_ids}
        self.last_funding_ts = int(time.time() * 1000)
        self._last_spark_time = 0.0
        self.started = time.time()
        self.bars_processed = 0
        self.signal_count = 0

    def restore_state(self, saved_accounts: list[dict], saved_positions: list[dict], curves: dict[str, list[float]] = None) -> None:
        """Pulihkan saldo, trade, drawdown, dan posisi terbuka dari DB setelah restart."""
        acct_map = {a["strategy"]: a for a in saved_accounts}
        for sid, acct in self.accounts.items():
            saved = acct_map.get(sid)
            if saved:
                acct["equity"] = float(saved.get("equity", START_EQUITY))
                acct["cash"] = float(saved.get("cash", START_EQUITY))
                acct["peak"] = float(saved.get("peak", START_EQUITY))
                acct["max_dd"] = float(saved.get("max_dd", 0.0))
                acct["trades"] = int(saved.get("trades", 0))
                acct["wins"] = int(saved.get("wins", 0))
                acct["gross_win"] = float(saved.get("gross_win", 0.0))
                acct["gross_loss"] = float(saved.get("gross_loss", 0.0))
                acct["realized"] = float(saved.get("realized", 0.0))
                acct["funding_paid"] = float(saved.get("funding_paid", 0.0))
                acct["mc_count"] = int(saved.get("mc_count", 0))
                acct["warmed"] = True

        for p in saved_positions:
            sid = p.get("strategy")
            sym = p.get("symbol")
            if sid in self.accounts:
                self.accounts[sid]["pos"][sym] = {
                    "symbol": sym,
                    "side": int(p["side"]),
                    "qty": float(p["qty"]),
                    "entry": float(p["entry"]),
                    "stop": float(p["stop"]) if p.get("stop") is not None else None,
                    "target": float(p["target"]) if p.get("target") is not None else None,
                    "opened_at": int(p.get("opened_at", 0)),
                    "notional": float(p.get("notional", 0.0)),
                    "margin_used": float(p.get("margin_used", p.get("notional", 0.0))),
                    "risk_amount": float(p.get("risk_amount", 0.0)),
                    "score": float(p.get("score", 0.0)),
                    "leverage": int(p.get("leverage", self.accounts[sid].get("leverage", 1))),
                    "rr": float(p.get("rr", 1.8)),
                }

        if curves:
            for sid, pts in curves.items():
                if sid in self.sparklines and pts:
                    self.sparklines[sid] = [float(x) for x in pts][-60:]

    def _get_price(self, symbol: str, fallback: float = 0.0) -> float:
        """Ambil harga close terakhir dari ring buffer dengan fallback aman jika pair belum ada di feed."""
        r = self.rings.get(symbol)
        if r and r.last_close and r.last_close > 0:
            return float(r.last_close)
        return float(fallback)

    # ── feed ────────────────────────────────────────────────────────────
    def on_bar_closed(self, symbol: str, views: dict, closed_bar_close: float) -> None:
        ring = self.rings.get(symbol)
        if ring is None or ring.n < MIN_BARS:
            return
        snap = compute(views)
        if snap.n < MIN_BARS:
            return
        self.bars_processed += 1
        ts = int(snap.ts[snap.i])

        signals: list[tuple[float, str, str]] = []  # (score, sid, symbol)
        for sid in self.strategy_ids:
            fn = SIGNAL_FN[sid]
            try:
                sc = fn(snap)
            except Exception:
                sc = 0.0
            if sc is None or sc != sc:
                continue
            if sc >= THRESHOLD:
                signals.append((float(sc), sid, symbol))
            elif sc <= -THRESHOLD:
                signals.append((float(sc), sid, symbol))

        for sc, sid, sym in signals:
            self._handle_signal(self.accounts[sid], sc, sym, snap, ts)

        # Futures funding rate: apply every 8 hours
        if self.mode == "futures" and ts - self.last_funding_ts >= FUNDING_INTERVAL_SEC * 1000:
            self.last_funding_ts = ts
            self._apply_funding(ts)

        # mark to market dengan harga close terakhir semua pair yang dipegang
        for sid, acct in self.accounts.items():
            if acct["pos"]:
                eq = acct["cash"]
                for sym, p in acct["pos"].items():
                    px = self._get_price(sym, p["entry"])
                    eq += (px - p["entry"]) * p["qty"] * p["side"]
                if eq <= 0.0:
                    self._handle_mc(acct, ts)
                else:
                    acct["equity"] = eq
                    if acct["equity"] > acct["peak"]:
                        acct["peak"] = acct["equity"]
                    dd = (acct["peak"] - acct["equity"]) / acct["peak"] if acct["peak"] else 0.0
                    if dd > acct["max_dd"]:
                        acct["max_dd"] = dd
            else:
                if acct["cash"] <= 0.0 or acct["equity"] <= 0.0:
                    self._handle_mc(acct, ts)
            if not acct["warmed"]:
                acct["warmed"] = True

    def _handle_mc(self, acct: dict, ts: int) -> None:
        """Margin Call / saldo $0: likuidasi semua posisi terbuka, refill ke START_EQUITY ($10.000), catat mc_count."""
        sid = acct["id"]
        acct["mc_count"] = acct.get("mc_count", 0) + 1
        mc_num = acct["mc_count"]

        # 1. Likuidasi seluruh posisi terbuka segera
        open_syms = list(acct["pos"].keys())
        for sym in open_syms:
            p = acct["pos"].pop(sym, None)
            if not p:
                continue
            px = self._get_price(sym, p["entry"])
            fee_rate = acct.get("fee_rate", SPOT_FEE)
            gross = (px - p["entry"]) * p["qty"] * p["side"]
            fee = abs(px * p["qty"]) * fee_rate
            net = gross - fee
            acct["trades"] += 1
            if net > 0:
                acct["wins"] += 1
                acct["gross_win"] += net
            else:
                acct["gross_loss"] += -net
            acct["realized"] += net

            self.new_trades.append({
                "strategy": sid, "symbol": sym, "side": p["side"], "qty": p["qty"],
                "entry": p["entry"], "exit": px, "opened_at": p["opened_at"], "closed_at": ts,
                "pnl": net, "fee": fee, "reason": f"MC #{mc_num} Likuidasi",
                "leverage": p.get("leverage", 1),
                "equity_after": 0.0,
            })

        # 2. Refill saldo kembali ke modal awal ($10.000)
        acct["cash"] = START_EQUITY
        acct["equity"] = START_EQUITY
        acct["peak"] = START_EQUITY
        acct["max_dd"] = 1.0  # Tercatat pernah drawdown 100%

        # Update sparkline agar visualisasi menunjukkan penurunan ke 0 dan refill ke $10.000
        if sid in self.sparklines:
            self.sparklines[sid].append(0.0)
            self.sparklines[sid].append(START_EQUITY)
            if len(self.sparklines[sid]) > 60:
                self.sparklines[sid] = self.sparklines[sid][-60:]

        # 3. Kirim notifikasi event ke feed realtime
        mode_str = self.mode.upper()
        msg = f"💥 MARGIN CALL (MC {mc_num}x) [{mode_str}]: Saldo {acct['name']} habis & posisi dilikuidasi! Refill otomatis ke ${START_EQUITY:,.0f}."
        self._push_event([sid], None, "mc", msg)

    # ── eksekusi ────────────────────────────────────────────────────────
    def _portfolio_risk(self, acct: dict) -> tuple[float, float]:
        """Return (total_committed, total_risk) across all open positions.
        Spot & Forex: committed = notional (maks 100% equity).
        Futures: committed = margin_used (maks 100% equity)."""
        if self.mode == "futures":
            tc = sum(p.get("margin_used", p["notional"] / max(1, p.get("leverage", 1))) for p in acct["pos"].values())
        else:
            tc = sum(p["notional"] for p in acct["pos"].values())
        tr = sum(p["risk_amount"] for p in acct["pos"].values())
        return tc, tr

    def _handle_signal(self, acct: dict, score: float, symbol: str, snap, ts: int) -> None:
        side = LONG if score > 0 else SHORT
        price = snap.c[snap.i]
        atr = snap.atr14[snap.i]
        pos = acct["pos"].get(symbol)

        if pos and pos["side"] == side:
            return  # sudah searah

        if pos and pos["side"] != side:
            self._close(acct, symbol, price, ts, "flip", snap)

        # Risk-based position limit: alokasi margin per posisi dibatasi SINGLE_POS_CAP (20% equity = $2.000)
        # sehingga tiap strategi dapat memegang hingga MAX_POS (5) pair berbeda secara simultan
        leverage = acct.get("leverage", 1) if self.mode == "futures" else 1
        stop_dist = SL_MULT * atr if (atr and atr > 0) else price * 0.02
        stop_dist = max(stop_dist, price * 0.0035)

        # Sizing berbasis risiko murni: loss saat SL terkena adalah ~2% equity ($200 dari modal $10.000)
        target_risk = acct["equity"] * RISK
        risk_based_notional = target_risk / (stop_dist / price)
        if self.mode == "futures":
            max_notional_cap = acct["equity"] * SINGLE_POS_CAP * leverage
            est_notional = min(risk_based_notional, max_notional_cap)
            est_committed = est_notional / leverage
        else:
            max_notional_cap = acct["equity"] * SINGLE_POS_CAP
            est_notional = min(risk_based_notional, max_notional_cap)
            est_committed = est_notional
        est_risk = stop_dist * (est_notional / price) if price > 0 else 0

        tc, tr = self._portfolio_risk(acct)
        if len(acct["pos"]) >= MAX_POS:
            # Hard cap reached (5 pair) — rotasi pair terlemah jika sinyal pair baru lebih kuat
            weakest = min(acct["pos"].items(), key=lambda kv: abs(kv[1]["score"]))
            if abs(score) <= abs(weakest[1]["score"]):
                return
            self._close(acct, weakest[0], self._get_price(weakest[0], weakest[1]["entry"]), ts, "rotasi", None)
        elif tc + est_committed > acct["equity"] * TOTAL_NOTIONAL_CAP + 1e-4:
            # Budget committed penuh — rotasi jika sinyal baru lebih kuat
            weakest = min(acct["pos"].items(), key=lambda kv: abs(kv[1]["score"])) if acct["pos"] else None
            if weakest and abs(score) > abs(weakest[1]["score"]):
                self._close(acct, weakest[0], self._get_price(weakest[0], weakest[1]["entry"]), ts, "budget_rotasi", None)
            else:
                return
        elif tr + est_risk > acct["equity"] * TOTAL_RISK_CAP + 1e-4:
            # Total risiko portfolio melebihi batas (20%)
            weakest = min(acct["pos"].items(), key=lambda kv: abs(kv[1]["score"])) if acct["pos"] else None
            if weakest and abs(score) > abs(weakest[1]["score"]):
                self._close(acct, weakest[0], self._get_price(weakest[0], weakest[1]["entry"]), ts, "risk_rotasi", None)
            else:
                return

        self._open(acct, symbol, side, price, atr, ts, score)

    def _open(self, acct: dict, symbol: str, side: int, price: float, atr: float, ts: int, score: float) -> None:
        # Spot mode: skip short signals
        if self.mode == "spot" and side == SHORT:
            return
        if not (price > 0):
            return
        leverage = acct.get("leverage", 1)
        fee_rate = acct.get("fee_rate", SPOT_FEE)
        stop_dist = SL_MULT * atr if (atr and atr > 0) else price * 0.02
        stop_dist = max(stop_dist, price * 0.0035)

        # Take profit berdasarkan Risk-to-Reward (R:R) per strategi
        rr_ratio = get_strategy_rr(acct["id"])
        tp_dist = stop_dist * rr_ratio

        # Sizing berbasis risiko murni: loss saat SL terkena adalah persis ~RISK (2%) dari equity
        # Margin yang dijaminkan dibatasi maks SINGLE_POS_CAP (20% equity = $2.000)
        target_risk = acct["equity"] * RISK
        risk_based_notional = target_risk / (stop_dist / price)
        if self.mode == "futures":
            max_notional_cap = acct["equity"] * SINGLE_POS_CAP * leverage
            notional = min(risk_based_notional, max_notional_cap)
            margin_used = notional / leverage
        else:
            max_notional_cap = acct["equity"] * SINGLE_POS_CAP
            notional = min(risk_based_notional, max_notional_cap)
            margin_used = notional

        if notional < 5:
            return
        qty = notional / price
        fee = notional * fee_rate if self.mode != "forex" else 0.0
        stop = price - stop_dist if side == LONG else price + stop_dist
        target = price + tp_dist if side == LONG else price - tp_dist
        actual_risk = stop_dist * qty

        # Standar lot Forex: 1 Standard Lot = 100,000 unit
        lot = round(notional / 100000, 2)
        if self.mode == "forex" and lot < 0.01:
            lot = 0.01

        acct["cash"] -= fee
        acct["pos"][symbol] = {
            "symbol": symbol, "side": side, "qty": qty, "entry": price,
            "stop": stop, "target": target, "opened_at": ts,
            "notional": notional, "margin_used": margin_used,
            "risk_amount": actual_risk, "score": score,
            "leverage": 1 if self.mode != "futures" else leverage,
            "lot": lot if self.mode == "forex" else None,
            "rr": rr_ratio,
        }
        self.signal_count += 1
        side_label = "LONG" if side == LONG else "SHORT"
        if self.mode == "forex":
            lev_str = f" ({lot:.2f} Lot)"
        elif self.mode == "futures":
            lev_str = f" {leverage}x"
        else:
            lev_str = ""
        msg = f"OPEN {side_label}{lev_str} {symbol} @ {price:.6g} | size ${notional:.0f} | SL {stop:.6g} | TP {target:.6g} (RR 1:{rr_ratio:.1f})"
        self._push_event([acct["id"]], symbol, "entry", msg)

        # Structured signal untuk Copy-Trading API / WebSocket / Webhooks
        sig = {
            "id": f"sig_{ts}_{acct['id']}_{symbol}_open",
            "ts": ts,
            "mode": self.mode,
            "strategy": acct["id"],
            "strategy_name": acct["name"],
            "symbol": symbol,
            "action": f"OPEN_{side_label}",
            "side": side_label,
            "leverage": 1 if self.mode != "futures" else leverage,
            "lot": lot if self.mode == "forex" else None,
            "price": price,
            "stop_loss": stop,
            "take_profit": target,
            "risk_reward": f"1:{rr_ratio:.1f}",
            "notional_usd": round(notional, 2),
            "margin_usd": round(margin_used, 2),
            "risk_amount_usd": round(actual_risk, 2),
            "pnl_usd": 0.0,
            "message": msg,
        }
        self.signals.append(sig)
        self.new_signals.append(sig)
        if len(self.signals) > 500:
            self.signals = self.signals[-500:]

    def _close(self, acct: dict, symbol: str, price: float, ts: int, why: str, snap) -> None:
        p = acct["pos"].pop(symbol, None)
        if not p:
            return
        fee_rate = acct.get("fee_rate", SPOT_FEE)
        gross = (price - p["entry"]) * p["qty"] * p["side"]
        fee = abs(price * p["qty"]) * fee_rate if self.mode != "forex" else 0.0
        net = gross - fee
        acct["cash"] += net
        acct["realized"] += net
        acct["trades"] += 1
        if net > 0:
            acct["wins"] += 1
            acct["gross_win"] += net
        else:
            acct["gross_loss"] += -net
        side_label = "LONG" if p["side"] == LONG else "SHORT"
        lev = p.get("leverage", 1)
        if self.mode == "forex":
            lot_val = p.get("lot") or round(p["notional"] / 100000, 2)
            lev_str = f" ({lot_val:.2f} Lot)"
        elif self.mode == "futures":
            lev_str = f" {lev}x"
        else:
            lev_str = ""
        pnl_sign = "+" if net >= 0 else ""
        event_kind = "tp" if ("Take Profit" in why or why == "tp") else ("stop" if ("Stop" in why or why == "stop") else "trade")
        close_msg = f"{why} {side_label}{lev_str} {symbol} @ {price:.6g} | entry {p['entry']:.6g} | PnL {pnl_sign}${net:.2f} | equity ${acct['equity'] + net:,.2f}"
        self._push_event([acct["id"]], symbol, event_kind, close_msg)
        self.new_trades.append({
            "strategy": acct["id"], "symbol": symbol, "side": p["side"], "qty": p["qty"],
            "entry": p["entry"], "exit": price, "opened_at": p["opened_at"], "closed_at": ts,
            "pnl": net, "fee": fee + (p["notional"] * fee_rate if self.mode != "forex" else 0.0), "reason": why,
            "leverage": 1 if self.mode != "futures" else lev,
            "lot": p.get("lot"),
            "equity_after": acct["cash"] + sum(
                (self._get_price(s, q["entry"]) - q["entry"]) * q["qty"] * q["side"]
                for s, q in acct["pos"].items()
            ),
        })

        # Structured signal untuk Copy-Trading API
        close_action = "CLOSE_TP" if ("Take Profit" in why or why == "tp") else ("CLOSE_SL" if ("Stop" in why or why == "stop") else f"CLOSE_{why.upper()}")
        sig = {
            "id": f"sig_{ts}_{acct['id']}_{symbol}_close",
            "ts": ts,
            "mode": self.mode,
            "strategy": acct["id"],
            "strategy_name": acct["name"],
            "symbol": symbol,
            "action": close_action,
            "side": side_label,
            "leverage": lev,
            "price": price,
            "stop_loss": p.get("stop"),
            "take_profit": p.get("target"),
            "risk_reward": f"1:{p.get('rr', 1.8):.1f}",
            "notional_usd": round(p.get("notional", 0.0), 2),
            "margin_usd": round(p.get("margin_used", 0.0), 2),
            "risk_amount_usd": round(p.get("risk_amount", 0.0), 2),
            "pnl_usd": round(net, 2),
            "message": close_msg,
        }
        self.signals.append(sig)
        self.new_signals.append(sig)
        if len(self.signals) > 500:
            self.signals = self.signals[-500:]

        if not acct["pos"] and (acct["cash"] <= 0.0 or acct["equity"] <= 0.0):
            self._handle_mc(acct, ts)

    # ── funding rate (futures only) ─────────────────────────────────────
    def _apply_funding(self, ts: int) -> None:
        """Simulasi funding rate: long bayar short saat rate positif.
        Rate default 0.01% per 8 jam (Binance historical average)."""
        for sid, acct in self.accounts.items():
            if not acct["pos"]:
                continue
            total_funding = 0.0
            for sym, p in acct["pos"].items():
                # Funding = notional * rate * side (long pays when rate > 0)
                funding = p["notional"] * FUNDING_RATE_DEFAULT * p["side"]
                total_funding += funding
            if abs(total_funding) > 0.001:
                acct["cash"] -= total_funding
                acct["funding_paid"] += total_funding
                sign = "bayar" if total_funding > 0 else "terima"
                self._push_event(
                    [sid], None, "funding",
                    f"Funding {sign} ${abs(total_funding):.4f} ({len(acct['pos'])} posisi)"
                )
                eq = acct["cash"]
                for sym, p in acct["pos"].items():
                    px = self._get_price(sym, p["entry"])
                    eq += (px - p["entry"]) * p["qty"] * p["side"]
                if eq <= 0.0:
                    self._handle_mc(acct, ts)

    # ── stops & take profit (dipanggil saat tick harga, eksekusi instan) ─
    def check_stops(self, symbol: str, price: float) -> None:
        now_ts = int(time.time() * 1000)
        for sid, acct in self.accounts.items():
            p = acct["pos"].get(symbol)
            if p:
                # 1. Cek Take Profit
                tp_price = p.get("target")
                tp_hit = False
                if tp_price is not None:
                    tp_hit = (p["side"] == LONG and price >= tp_price) or (p["side"] == SHORT and price <= tp_price)

                # 2. Cek Stop Loss
                sl_price = p.get("stop")
                sl_hit = False
                if sl_price is not None:
                    sl_hit = (p["side"] == LONG and price <= sl_price) or (p["side"] == SHORT and price >= sl_price)

                if tp_hit:
                    side_label = "LONG" if p["side"] == LONG else "SHORT"
                    self._close(acct, symbol, tp_price, now_ts, "Take Profit", None)
                    self._push_event([sid], symbol, "tp", f"🎯 TP {side_label} {symbol} @ {tp_price:.6g} (target tercapai)")
                elif sl_hit:
                    side_label = "LONG" if p["side"] == LONG else "SHORT"
                    self._close(acct, symbol, sl_price, now_ts, "Stop Loss", None)
                    self._push_event([sid], symbol, "stop", f"🛑 SL {side_label} {symbol} @ {sl_price:.6g} (batas risiko)")

            # Cek MC setelah pergerakan tick
            if acct["pos"]:
                eq = acct["cash"]
                for sym, pos_item in acct["pos"].items():
                    px = self._get_price(sym, pos_item["entry"])
                    eq += (px - pos_item["entry"]) * pos_item["qty"] * pos_item["side"]
                if eq <= 0.0:
                    self._handle_mc(acct, now_ts)
            elif acct["cash"] <= 0.0 or acct["equity"] <= 0.0:
                self._handle_mc(acct, now_ts)

    # ── snapshot untuk UI/DB ────────────────────────────────────────────
    def snapshot(self) -> dict:
        now = time.time()
        record_spark = (now - self._last_spark_time >= 1.0)
        if record_spark:
            self._last_spark_time = now

        accts = []
        positions = []
        for sid, a in self.accounts.items():
            # Mark-to-market live equity real-time tiap tick snapshot
            if a["pos"]:
                live_eq = a["cash"]
                for sym, p in a["pos"].items():
                    px = self._get_price(sym, p["entry"])
                    live_eq += (px - p["entry"]) * p["qty"] * p["side"]
                eq = round(max(0.0, live_eq), 2)
            else:
                eq = round(a["equity"], 2)

            if record_spark:
                hist = self.sparklines[sid]
                if not hist or abs(hist[-1] - eq) > 0.01 or len(hist) < 2:
                    hist.append(eq)
                    if len(hist) > 60:
                        hist.pop(0)

            accts.append({
                "id": sid, "name": a["name"], "family": a["family"], "color": a["color"],
                "mode": self.mode, "leverage": 1 if self.mode != "futures" else a.get("leverage", 1),
                "equity": eq, "cash": round(a["cash"], 2), "peak": a["peak"],
                "max_dd": a["max_dd"], "trades": a["trades"], "wins": a["wins"],
                "gross_win": a["gross_win"], "gross_loss": a["gross_loss"], "realized": a["realized"],
                "funding_paid": round(a.get("funding_paid", 0), 4),
                "open": len(a["pos"]), "warmed": a["warmed"],
                "mc_count": a.get("mc_count", 0),
            })
            for sym, p in a["pos"].items():
                px = self._get_price(sym, p["entry"])
                positions.append({
                    "strategy": sid, "symbol": sym, "side": p["side"], "qty": p["qty"],
                    "entry": p["entry"], "stop": p["stop"], "target": p["target"],
                    "opened_at": p["opened_at"], "notional": p["notional"],
                    "margin_used": p.get("margin_used", p["notional"]),
                    "leverage": 1 if self.mode != "futures" else p.get("leverage", 1),
                    "lot": p.get("lot"),
                    "risk_amount": p["risk_amount"], "reason": None,
                    "mark": px, "upnl": (px - p["entry"]) * p["qty"] * p["side"],
                })
        return {
            "accounts": accts,
            "positions": positions,
            "mode": self.mode,
            "curves": {sid: list(self.sparklines[sid]) for sid in self.strategy_ids},
        }

    def _push_event(self, strats: list[str], symbol: str | None, kind: str, message: str) -> None:
        self.events.append({"ts": int(time.time() * 1000), "strats": strats, "symbol": symbol, "kind": kind, "message": message})
        if len(self.events) > 400:
            del self.events[:100]

    def drain(self) -> dict:
        trades, self.new_trades = self.new_trades, []
        signals, self.new_signals = self.new_signals, []
        # events TIDAK dikosongkan — UI butuh history tetap ada.
        # Hanya trim kalau terlalu panjang (sudah dilakukan di _push_event).
        pts = []
        now = int(time.time() * 1000) // 10000 * 10000
        for sid, a in self.accounts.items():
            pts.append((sid, now, round(a["equity"], 2)))
        return {
            "new_trades": trades,
            "new_signals": signals,
            "new_events": list(self.events[-60:]),
            "equity_points": pts
        }


def feed_loop_docs() -> str:
    return __doc__ or ""
