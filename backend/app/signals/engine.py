"""
Signal evaluation engine.
Maintains per-instrument indicator state and evaluates all registered signals
every time a new snapshot/trade arrives from the feed.

ISO 25010 — Functional Suitability: correct signal computation.
ISO 25010 — Performance Efficiency: O(1) incremental update per tick.
"""
from collections import defaultdict
from datetime import datetime, timezone

from app.indicators import RSI, BollingerBands, EMA, SessionVWAP
from app.signals.base import BaseSignal, SignalResult


# ── Built-in signal definitions ───────────────────────────────────────────────

class RSISignal(BaseSignal):
    name = "RSI"

    def evaluate(self, symbol: str, rsi: float | None, **_) -> SignalResult | None:
        if rsi is None:
            return None
        if rsi < 30:
            return SignalResult(symbol=symbol, signal="RSI_OVERSOLD",
                                direction="BUY", strength=(30 - rsi) / 30,
                                detail={"rsi": round(rsi, 2)})
        if rsi > 70:
            return SignalResult(symbol=symbol, signal="RSI_OVERBOUGHT",
                                direction="SELL", strength=(rsi - 70) / 30,
                                detail={"rsi": round(rsi, 2)})
        return None


class BollingerSignal(BaseSignal):
    name = "BOLLINGER"

    def evaluate(self, symbol: str, bb=None, **_) -> SignalResult | None:
        if bb is None:
            return None
        if bb.pct_b < 0.05:
            return SignalResult(symbol=symbol, signal="BB_LOWER_TOUCH",
                                direction="BUY", strength=1.0 - bb.pct_b,
                                detail={"pct_b": round(bb.pct_b, 4), "bw": round(bb.bandwidth, 4)})
        if bb.pct_b > 0.95:
            return SignalResult(symbol=symbol, signal="BB_UPPER_TOUCH",
                                direction="SELL", strength=bb.pct_b,
                                detail={"pct_b": round(bb.pct_b, 4), "bw": round(bb.bandwidth, 4)})
        return None


class VWAPCrossSignal(BaseSignal):
    name = "VWAP_CROSS"

    def __init__(self) -> None:
        self._prev_above: dict[str, bool | None] = defaultdict(lambda: None)

    def evaluate(self, symbol: str, price: float | None = None,
                 vwap: float | None = None, **_) -> SignalResult | None:
        if price is None or vwap is None:
            return None
        above = price > vwap
        prev  = self._prev_above[symbol]
        self._prev_above[symbol] = above

        if prev is None or prev == above:
            return None

        direction = "BUY" if above else "SELL"
        return SignalResult(
            symbol=symbol, signal="VWAP_CROSS", direction=direction,
            strength=abs(price - vwap) / vwap,
            detail={"price": round(price, 4), "vwap": round(vwap, 4)},
        )


# ── Per-instrument indicator state ────────────────────────────────────────────

class _InstrumentState:
    def __init__(self) -> None:
        self.rsi    = RSI(period=14)
        self.bb     = BollingerBands(period=20, num_std=2.0)
        self.ema9   = EMA(period=9)
        self.ema21  = EMA(period=21)
        self.vwap   = SessionVWAP()

    def on_trade(self, price: float, qty: int) -> None:
        self.rsi.update(price)
        self.bb.update(price)
        self.ema9.update(price)
        self.ema21.update(price)
        self.vwap.update_trade(price, qty)

    def session_reset(self) -> None:
        self.rsi.reset()
        self.bb.reset()
        self.ema9.reset()
        self.ema21.reset()
        self.vwap.reset()


# ── Engine ────────────────────────────────────────────────────────────────────

class SignalEngine:
    def __init__(self) -> None:
        self._states: dict[str, _InstrumentState] = {}
        self._signals: list[BaseSignal] = [
            RSISignal(),
            BollingerSignal(),
            VWAPCrossSignal(),
        ]

    def on_trade(self, symbol: str, price: float, qty: int) -> list[SignalResult]:
        state = self._states.setdefault(symbol, _InstrumentState())
        state.on_trade(price, qty)

        ctx = {
            "price": price,
            "rsi":   state.rsi.value(),
            "bb":    state.bb.value(),
            "ema9":  state.ema9.value(),
            "ema21": state.ema21.value(),
            "vwap":  state.vwap.value(),
        }

        results = []
        for sig in self._signals:
            result = sig.evaluate(symbol=symbol, **ctx)
            if result is not None:
                results.append(result)
        return results

    def session_reset(self, symbol: str | None = None) -> None:
        if symbol:
            if symbol in self._states:
                self._states[symbol].session_reset()
        else:
            for state in self._states.values():
                state.session_reset()

    def register(self, signal: BaseSignal) -> None:
        self._signals.append(signal)
