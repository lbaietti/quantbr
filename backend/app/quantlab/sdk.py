"""
QuantBR Lab SDK — public API surface for user-defined strategies and indicators.

Quant developers import from this module inside their strategy scripts.
Everything here is safe to expose in the sandbox context.

Example strategy:

    from quantlab.sdk import BaseStrategy, Indicator, SMA, RSI, ta, register

    class MyCrossStrategy(BaseStrategy):
        name = "SMA Cross 9/21"
        symbols = ["PETR4", "VALE3"]

        def __init__(self):
            self.fast = SMA(9)
            self.slow = SMA(21)

        def on_trade(self, event: TradeEvent) -> Signal | None:
            self.fast.update(event.price)
            self.slow.update(event.price)
            f, s = self.fast.value(), self.slow.value()
            if f is None or s is None:
                return None
            if f > s:
                return self.signal("BUY", strength=(f - s) / s)
            if f < s:
                return self.signal("SELL", strength=(s - f) / s)
            return None

    register(MyCrossStrategy)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Re-export built-in indicators so user code can import them
from app.indicators.moving_average import SMA, EMA
from app.indicators.rsi import RSI
from app.indicators.bollinger import BollingerBands
from app.indicators.vwap import SessionVWAP
from app.indicators.delta import OrderFlowDelta
from app.indicators.volume_profile import VolumeProfile
from app.indicators.base import Indicator


@dataclass
class TradeEvent:
    symbol: str
    price: float
    qty: int
    aggressor: str      # 'B' | 'S'
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class QuoteEvent:
    symbol: str
    bid: float
    ask: float
    bid_qty: int
    ask_qty: int
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Signal:
    name: str
    symbol: str
    direction: str      # 'BUY' | 'SELL' | 'NEUTRAL'
    strength: float     # 0.0–1.0
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    meta: dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """Base class for all user-defined strategies."""

    name: str = "Unnamed Strategy"
    symbols: list[str] = []     # empty = subscribe to all

    def signal(self, direction: str, strength: float = 1.0,
                symbol: str = "", **meta) -> Signal:
        return Signal(
            name=self.name,
            symbol=symbol,
            direction=direction,
            strength=min(max(strength, 0.0), 1.0),
            meta=meta,
        )

    def on_trade(self, event: TradeEvent) -> Signal | None:
        return None

    def on_quote(self, event: QuoteEvent) -> Signal | None:
        return None

    def on_session_start(self, symbol: str) -> None:
        pass

    def on_session_end(self, symbol: str) -> None:
        pass


class BaseIndicator(ABC):
    """Base class for user-defined indicators."""

    name: str = "Custom Indicator"

    @abstractmethod
    def update(self, value: float) -> None: ...

    @abstractmethod
    def value(self) -> Any: ...

    @abstractmethod
    def reset(self) -> None: ...


# ── Technical analysis helpers ───────────────────────────────────────────────

class ta:
    """Stateless utility functions for technical analysis."""

    @staticmethod
    def crossover(a_prev: float | None, a_curr: float | None,
                  b_prev: float | None, b_curr: float | None) -> bool:
        """True if series A crossed above series B."""
        if None in (a_prev, a_curr, b_prev, b_curr):
            return False
        return a_prev <= b_prev and a_curr > b_curr  # type: ignore[operator]

    @staticmethod
    def crossunder(a_prev: float | None, a_curr: float | None,
                   b_prev: float | None, b_curr: float | None) -> bool:
        """True if series A crossed below series B."""
        if None in (a_prev, a_curr, b_prev, b_curr):
            return False
        return a_prev >= b_prev and a_curr < b_curr  # type: ignore[operator]

    @staticmethod
    def highest(values: list[float], period: int) -> float | None:
        window = values[-period:]
        return max(window) if len(window) == period else None

    @staticmethod
    def lowest(values: list[float], period: int) -> float | None:
        window = values[-period:]
        return min(window) if len(window) == period else None

    @staticmethod
    def stdev(values: list[float], period: int) -> float | None:
        import math
        window = values[-period:]
        if len(window) < period:
            return None
        mean = sum(window) / period
        return math.sqrt(sum((x - mean) ** 2 for x in window) / period)


# ── Registration (populated by sandbox on load) ──────────────────────────────

_registry_hook: Any = None   # injected by StrategyRegistry

def register(strategy_cls: type[BaseStrategy]) -> None:
    """Call inside strategy script to register with QuantLab."""
    if _registry_hook is not None:
        _registry_hook(strategy_cls)
