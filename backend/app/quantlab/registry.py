"""
Strategy registry — live management of user-defined strategies.
Each registered strategy receives market events from the feed.
"""
from __future__ import annotations

import asyncio
import json
import structlog
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.quantlab.sdk import BaseStrategy, TradeEvent, QuoteEvent, Signal

log = structlog.get_logger(__name__)


@dataclass
class StrategyRecord:
    id: str
    name: str
    author: str
    source: str
    cls: type[BaseStrategy]
    instance: BaseStrategy
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signal_count: int = 0
    error_count: int = 0
    last_error: str | None = None
    enabled: bool = True


class StrategyRegistry:
    """
    Singleton that holds all live user strategies.
    Wired into FeedSubscriber — every trade/quote is dispatched here.
    """

    def __init__(self, redis: Any) -> None:
        self._redis = redis
        self._strategies: dict[str, StrategyRecord] = {}

    def add(self, strategy_id: str, name: str, author: str,
            source: str, cls: type[BaseStrategy]) -> StrategyRecord:
        instance = cls()
        record = StrategyRecord(
            id=strategy_id, name=name, author=author,
            source=source, cls=cls, instance=instance,
        )
        self._strategies[strategy_id] = record
        log.info("quantlab.strategy.registered", id=strategy_id, name=name)
        return record

    def remove(self, strategy_id: str) -> bool:
        return bool(self._strategies.pop(strategy_id, None))

    def get(self, strategy_id: str) -> StrategyRecord | None:
        return self._strategies.get(strategy_id)

    def list_all(self) -> list[StrategyRecord]:
        return list(self._strategies.values())

    async def dispatch_trade(self, event: TradeEvent) -> None:
        for record in self._strategies.values():
            if not record.enabled:
                continue
            syms = record.instance.symbols
            if syms and event.symbol not in syms:
                continue
            try:
                result: Signal | None = record.instance.on_trade(event)
                if result:
                    record.signal_count += 1
                    result.symbol = result.symbol or event.symbol
                    await self._publish_signal(record, result)
            except Exception as exc:
                record.error_count += 1
                record.last_error = str(exc)
                log.warning("quantlab.strategy.error", id=record.id, error=str(exc))

    async def dispatch_quote(self, event: QuoteEvent) -> None:
        for record in self._strategies.values():
            if not record.enabled:
                continue
            syms = record.instance.symbols
            if syms and event.symbol not in syms:
                continue
            try:
                result = record.instance.on_quote(event)
                if result:
                    record.signal_count += 1
                    result.symbol = result.symbol or event.symbol
                    await self._publish_signal(record, result)
            except Exception as exc:
                record.error_count += 1
                record.last_error = str(exc)

    async def _publish_signal(self, record: StrategyRecord, sig: Signal) -> None:
        payload = json.dumps({
            "source":    "quantlab",
            "strategy":  record.name,
            "strategy_id": record.id,
            "symbol":    sig.symbol,
            "direction": sig.direction,
            "strength":  round(sig.strength, 4),
            "ts":        sig.ts.isoformat(),
            "meta":      sig.meta,
        })
        await self._redis.publish(f"lab:signal:{sig.symbol}", payload)
        await self._redis.publish("lab:signal:*", payload)
        # Also store last N signals for REST retrieval
        await self._redis.lpush(f"lab:signals:{record.id}", payload)
        await self._redis.ltrim(f"lab:signals:{record.id}", 0, 199)
