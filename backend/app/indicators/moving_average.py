from app.indicators.base import Indicator, RollingBuffer


class SMA(Indicator):
    def __init__(self, period: int) -> None:
        self._period = period
        self._buf = RollingBuffer(period)
        self._total = 0.0

    def update(self, value: float) -> None:
        if self._buf.full():
            self._total -= self._buf.to_list()[0]
        self._buf.push(value)
        self._total += value

    def value(self) -> float | None:
        if not self._buf.full():
            return None
        return self._total / self._period

    def reset(self) -> None:
        self._buf.clear()
        self._total = 0.0


class EMA(Indicator):
    def __init__(self, period: int) -> None:
        self._period = period
        self._k = 2.0 / (period + 1)
        self._ema: float | None = None
        self._count = 0

    def update(self, value: float) -> None:
        if self._ema is None:
            self._ema = value
        else:
            self._ema = value * self._k + self._ema * (1 - self._k)
        self._count += 1

    def value(self) -> float | None:
        if self._count < self._period:
            return None
        return self._ema

    def reset(self) -> None:
        self._ema = None
        self._count = 0
