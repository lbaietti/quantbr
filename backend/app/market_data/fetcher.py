"""
Live market reference data fetcher — B3 public API + BCB open API.

Sources used (all public, no auth required):
  B3  — cotacao.b3.com.br/mds/api/v1/  (powers B3's own website)
  BCB — olinda.bcb.gov.br              (Banco Central do Brasil open data)
  BCB SGS — api.bcb.gov.br/dados/serie (Sistema Gerenciador de Séries)

Fetch cycle: every 30 seconds during trading hours (10:00–18:30 BRT).
Results are cached in Redis and served via GET /api/v1/reference/*.
"""
from __future__ import annotations

import asyncio
import json
import structlog
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

log = structlog.get_logger(__name__)

# ── B3 public endpoint (same API used by b3.com.br website) ──────────────────
_B3_QUOTE   = "https://cotacao.b3.com.br/mds/api/v1/instrumentQuotation/{symbol}"
_B3_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer":    "https://www.b3.com.br/",
    "Accept":     "application/json",
}

# BCB PTAX (official USD/BRL from Banco Central do Brasil)
_BCB_PTAX = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
    "CotacaoDolarDia(dataCotacao=@d)?@d='{date}'&$top=1&$format=json"
    "&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao"
)

# BCB SGS series for SELIC meta rate (series 432)
_BCB_SELIC = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"

# DI futures codes traded on B3
_DI_CODES = ["DI1F26", "DI1F27", "DI1F28", "DI1F29", "DI1F30", "DI1F31", "DI1F32", "DI1F33"]

# Index codes
_INDEX_CODES = ["IBOV", "IFIX", "SMLL", "IDIV"]

# World market instruments (B3 also quotes some international)
_WORLD_CODES = ["SPXB11", "EURB11"]  # ETFs on B3 tracking SPX and EUR


class MarketDataFetcher:
    def __init__(self, redis: Any) -> None:
        self._redis   = redis
        self._running = False
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client  = httpx.AsyncClient(timeout=10.0, headers=_B3_HEADERS)
        self._running = True
        asyncio.create_task(self._loop())
        log.info("market_data.fetcher.started")

    async def stop(self) -> None:
        self._running = False
        if self._client:
            await self._client.aclose()

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._fetch_all()
            except Exception as exc:
                log.warning("market_data.fetch_cycle.error", error=str(exc))
            await asyncio.sleep(30)

    async def _fetch_all(self) -> None:
        await asyncio.gather(
            self._fetch_indices(),
            self._fetch_di_futures(),
            self._fetch_ptax(),
            self._fetch_selic(),
            return_exceptions=True,
        )

    # ── Indices ───────────────────────────────────────────────────────────────

    async def _fetch_indices(self) -> None:
        results = []
        for code in _INDEX_CODES:
            try:
                data = await self._b3_quote(code)
                if not data:
                    continue
                close = data.get("SctyQt", {})
                results.append({
                    "label":  code,
                    "value":  _f(close.get("curPrc")),
                    "change": _f(close.get("pctChng")),
                    "max":    _f(close.get("maxPrc")),
                    "min":    _f(close.get("minPrc")),
                    "ts":     _now(),
                })
            except Exception as exc:
                log.debug("market_data.index.error", code=code, error=str(exc))

        if results:
            await self._redis.setex("ref:indices", 60, json.dumps(results))
            await self._redis.publish("ref:indices", json.dumps(results))

    # ── DI Futures ────────────────────────────────────────────────────────────

    async def _fetch_di_futures(self) -> None:
        results = []
        for code in _DI_CODES:
            try:
                data = await self._b3_quote(code)
                if not data:
                    continue
                close = data.get("SctyQt", {})
                results.append({
                    "code":   code,
                    "rate":   _f(close.get("curPrc")),
                    "change": _f(close.get("pctChng")),
                    "volume": _i(close.get("tradQty")),
                    "ts":     _now(),
                })
            except Exception as exc:
                log.debug("market_data.di.error", code=code, error=str(exc))

        if results:
            await self._redis.setex("ref:di_futures", 60, json.dumps(results))
            await self._redis.publish("ref:di_futures", json.dumps(results))

    # ── PTAX ─────────────────────────────────────────────────────────────────

    async def _fetch_ptax(self) -> None:
        try:
            today = datetime.now(tz=timezone(timedelta(hours=-3))).strftime("%m-%d-%Y")
            url   = _BCB_PTAX.format(date=today)
            resp  = await self._client.get(url)  # type: ignore[union-attr]
            resp.raise_for_status()
            value = resp.json().get("value", [])
            if value:
                entry = value[0]
                payload = {
                    "buy":  _f(entry.get("cotacaoCompra")),
                    "sell": _f(entry.get("cotacaoVenda")),
                    "ts":   entry.get("dataHoraCotacao", _now()),
                }
                await self._redis.setex("ref:ptax", 120, json.dumps(payload))
                await self._redis.publish("ref:ptax", json.dumps(payload))
        except Exception as exc:
            log.debug("market_data.ptax.error", error=str(exc))

    # ── SELIC meta rate ───────────────────────────────────────────────────────

    async def _fetch_selic(self) -> None:
        try:
            resp = await self._client.get(_BCB_SELIC)  # type: ignore[union-attr]
            resp.raise_for_status()
            data = resp.json()
            if data:
                entry = data[-1]
                payload = {
                    "rate": _f(entry.get("valor")),
                    "date": entry.get("data", ""),
                }
                await self._redis.setex("ref:selic", 3600, json.dumps(payload))
        except Exception as exc:
            log.debug("market_data.selic.error", error=str(exc))

    # ── B3 quote helper ───────────────────────────────────────────────────────

    async def _b3_quote(self, symbol: str) -> dict | None:
        url  = _B3_QUOTE.format(symbol=symbol)
        resp = await self._client.get(url)  # type: ignore[union-attr]
        if resp.status_code != 200:
            return None
        body = resp.json()
        # B3 wraps results in {"SctyQtn": {"SctyQtnItm": [...]}}
        items = (body.get("SctyQtn") or body.get("Scty") or {}).get("SctyQtnItm") or []
        return items[0] if items else body


# ── Helpers ───────────────────────────────────────────────────────────────────

def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _i(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
