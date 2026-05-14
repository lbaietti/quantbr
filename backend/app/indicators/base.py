"""
ISO 25010 — Maintainability: each indicator is a self-contained, testable unit.
"""
from abc import ABC, abstractmethod
from collections import deque


class Indicator(ABC):
    """Incremental (tick-by-tick) indicator base class."""

    @abstractmethod
    def update(self, value: float) -> None:
        """Push a new data point."""

    @abstractmethod
    def value(self) -> float | None:
        """Return current indicator value, or None if not enough data."""

    @abstractmethod
    def reset(self) -> None:
        """Clear all state (e.g. at session open)."""


class RollingBuffer:
    """Fixed-size FIFO buffer backed by a deque."""

    def __init__(self, maxlen: int) -> None:
        self._buf: deque[float] = deque(maxlen=maxlen)
        self.maxlen = maxlen

    def push(self, v: float) -> None:
        self._buf.append(v)

    def full(self) -> bool:
        return len(self._buf) == self.maxlen

    def clear(self) -> None:
        self._buf.clear()

    def __len__(self) -> int:
        return len(self._buf)

    def __iter__(self):
        return iter(self._buf)

    def to_list(self) -> list[float]:
        return list(self._buf)
