from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SignalResult:
    symbol: str
    signal: str
    direction: str     # "BUY" | "SELL" | "NEUTRAL"
    strength: float    # 0.0 – 1.0
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detail: dict = field(default_factory=dict)


class BaseSignal(ABC):
    name: str

    @abstractmethod
    def evaluate(self, symbol: str, **kwargs) -> SignalResult | None:
        """Return a SignalResult if triggered, None otherwise."""
