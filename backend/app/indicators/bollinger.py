import math
from dataclasses import dataclass
from app.indicators.base import Indicator, RollingBuffer


@dataclass
class BandValue:
    upper: float
    middle: float
    lower: float
    bandwidth: float   # (upper - lower) / middle
    pct_b: float       # position of last price within band (0=lower, 1=upper)


class BollingerBands(Indicator):
    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        self._period  = period
        self._num_std = num_std
        self._buf     = RollingBuffer(period)
        self._last: float = 0.0

    def update(self, value: float) -> None:
        self._buf.push(value)
        self._last = value

    def value(self) -> BandValue | None:
        if not self._buf.full():
            return None
        data = self._buf.to_list()
        mean = sum(data) / self._period
        variance = sum((x - mean) ** 2 for x in data) / self._period
        std  = math.sqrt(variance)
        upper  = mean + self._num_std * std
        lower  = mean - self._num_std * std
        bw     = (upper - lower) / mean if mean else 0.0
        pct_b  = (self._last - lower) / (upper - lower) if upper != lower else 0.5
        return BandValue(upper=upper, middle=mean, lower=lower, bandwidth=bw, pct_b=pct_b)

    def reset(self) -> None:
        self._buf.clear()
        self._last = 0.0
