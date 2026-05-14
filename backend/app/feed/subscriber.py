"""
ZMQ SUB consumer — receives JSON frames from the C++ feed process and fans
out to: Redis pub/sub (WebSocket), SignalEngine, StrategyRegistry,
tape buffer, order flow accumulators.

ISO 25010 — Reliability: reconnects on failure, drops malformed frames.
ISO 25010 — Performance Efficiency: non-blocking async recv.
"""
import asyncio
import json
import structlog
from collections import defaultdict

import zmq
import zmq.asyncio

from app.config import get_settings
from app.signals.engine import SignalEngine
from app.indicators.delta import OrderFlowDelta
from app.indicators.volume_profile import VolumeProfile
from app.quantlab.sdk import TradeEvent as LabTradeEvent, QuoteEvent as LabQuoteEvent

log = structlog.get_logger(__name__)


class FeedSubscriber:
    def __init__(self, redis, signal_engine: SignalEngine,
                 strategy_registry=None) -> None:
        self._redis    = redis
        self._engine   = signal_engine
        self._registry = strategy_registry
        self._ctx      = zmq.asyncio.Context()
        self._sock     = None
        self._running  = False

        # Per-symbol order flow state
        self._deltas:   dict[str, OrderFlowDelta]  = defaultdict(OrderFlowDelta)
        self._vprofile: dict[str, VolumeProfile]   = defaultdict(VolumeProfile)

    async def start(self) -> None:
        settings = get_settings()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.connect(settings.zmq_feed_endpoint)
        self._sock.setsockopt_string(zmq.SUBSCRIBE, "snapshot")
        self._sock.setsockopt_string(zmq.SUBSCRIBE, "trade")
        self._running = True
        log.info("feed.subscriber.started", endpoint=settings.zmq_feed_endpoint)
        asyncio.create_task(self._recv_loop())

    async def stop(self) -> None:
        self._running = False
        if self._sock:
            self._sock.close()
        self._ctx.term()
        log.info("feed.subscriber.stopped")

    async def _recv_loop(self) -> None:
        while self._running:
            try:
                topic_b, payload_b = await self._sock.recv_multipart()
                topic   = topic_b.decode()
                payload = json.loads(payload_b)
            except zmq.ZMQError:
                break
            except (json.JSONDecodeError, ValueError) as exc:
                log.warning("feed.frame.invalid", error=str(exc))
                continue

            try:
                if topic == "snapshot":
                    await self._handle_snapshot(payload)
                elif topic == "trade":
                    await self._handle_trade(payload)
            except Exception as exc:
                log.error("feed.handler.error", topic=topic, error=str(exc))

    async def _handle_snapshot(self, data: dict) -> None:
        symbol = data.get("symbol", "").strip("\x00")
        if not symbol:
            return

        # Cache latest snapshot for REST lookup
        await self._redis.setex(f"cache:snapshot:{symbol}", 60, json.dumps(data))

        # Publish for WebSocket fanout
        await self._redis.publish(f"market:snapshot:{symbol}", json.dumps(data))
        await self._redis.publish("market:snapshot:*", json.dumps(data))

        # Dispatch quote event to QuantLab strategies
        if self._registry:
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            if bids and asks:
                ev = LabQuoteEvent(
                    symbol=symbol,
                    bid=bids[0]["price"], bid_qty=bids[0]["qty"],
                    ask=asks[0]["price"], ask_qty=asks[0]["qty"],
                )
                await self._registry.dispatch_quote(ev)

    async def _handle_trade(self, data: dict) -> None:
        symbol = data.get("symbol", "").strip("\x00")
        price  = data.get("price", 0.0)
        qty    = data.get("qty", 0)
        agg    = data.get("aggressor", "U")

        if not symbol or price == 0:
            return

        # ── Tape buffer (Times & Trade) ───────────────────────────────────────
        tape_entry = json.dumps({
            "symbol":    symbol,
            "price":     price,
            "qty":       qty,
            "aggressor": agg,
            "ts":        data.get("ts", 0),
        })
        await self._redis.lpush(f"tape:{symbol}", tape_entry)
        await self._redis.ltrim(f"tape:{symbol}", 0, 999)

        # ── Order flow delta accumulation ─────────────────────────────────────
        delta = self._deltas[symbol]
        delta.update(price, int(qty), agg)
        delta_payload = json.dumps({
            "symbol":     symbol,
            "buy_vol":    delta.buy_volume,
            "sell_vol":   delta.sell_volume,
            "delta":      delta.delta,
            "cum_delta":  delta.cumulative_delta,
            "buy_pct":    round(delta.buy_pct(), 1),
            "history":    delta.delta_history[-30:],
        })
        await self._redis.setex(f"orderflow:delta:{symbol}", 86400, delta_payload)
        await self._redis.publish(f"orderflow:delta:{symbol}", delta_payload)

        # ── Volume profile accumulation ───────────────────────────────────────
        vp = self._vprofile[symbol]
        vp.update(price, int(qty), agg)
        result = vp.result()
        if result:
            vp_payload = json.dumps({
                "symbol": symbol,
                "poc":    result.poc,
                "vah":    result.vah,
                "val":    result.val,
                "total_volume": result.total_volume,
                "total_delta":  result.total_delta,
                "levels": [
                    {"price": l.price, "buy": l.buy_vol, "sell": l.sell_vol,
                     "total": l.total, "delta": l.delta}
                    for l in result.levels
                ],
            })
            await self._redis.setex(f"orderflow:vprofile:{symbol}", 86400, vp_payload)
            await self._redis.publish(f"orderflow:vprofile:{symbol}", vp_payload)

        # ── Signal engine ─────────────────────────────────────────────────────
        signals = self._engine.on_trade(symbol, price, int(qty))
        await self._redis.publish(f"market:trade:{symbol}", json.dumps(data))

        for sig in signals:
            sig_payload = json.dumps({
                "symbol":    sig.symbol,
                "signal":    sig.signal,
                "direction": sig.direction,
                "strength":  round(sig.strength, 4),
                "ts":        sig.ts.isoformat(),
                "detail":    sig.detail,
            })
            await self._redis.publish(f"signal:{symbol}", sig_payload)
            await self._redis.lpush(f"signals:{symbol}", sig_payload)
            await self._redis.ltrim(f"signals:{symbol}", 0, 199)
            log.info("signal.triggered", symbol=sig.symbol, signal=sig.signal,
                     direction=sig.direction, strength=round(sig.strength, 4))

        # ── QuantLab strategies ───────────────────────────────────────────────
        if self._registry:
            ev = LabTradeEvent(symbol=symbol, price=price, qty=int(qty), aggressor=agg)
            await self._registry.dispatch_trade(ev)
