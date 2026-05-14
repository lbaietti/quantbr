from app.indicators.base import Indicator


class RSI(Indicator):
    """Wilder's RSI (exponential smoothing variant used by most platforms)."""

    def __init__(self, period: int = 14) -> None:
        self._period = period
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._prev: float | None = None
        self._count = 0

    def update(self, value: float) -> None:
        if self._prev is None:
            self._prev = value
            return

        change = value - self._prev
        self._prev = value
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if self._count < self._period:
            # Seed with simple average
            self._avg_gain += gain / self._period
            self._avg_loss += loss / self._period
        else:
            # Wilder smoothing
            self._avg_gain = (self._avg_gain * (self._period - 1) + gain) / self._period
            self._avg_loss = (self._avg_loss * (self._period - 1) + loss) / self._period

        self._count += 1

    def value(self) -> float | None:
        if self._count < self._period:
            return None
        if self._avg_loss == 0.0:
            # No losses at all — if no gains either (flat market) return neutral 50
            return 100.0 if self._avg_gain > 0.0 else 50.0
        rs = self._avg_gain / self._avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def reset(self) -> None:
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._prev = None
        self._count = 0
