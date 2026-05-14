"""
News aggregator — pulls RSS/Atom feeds from official financial news sources
and classifies each item by market impact (HOT / WARM / COLD).

Sources:
  Reuters Brasil  — reuters.com/business/finance  (EN, global)
  Infomoney       — infomoney.com.br               (PT-BR, B3 focus)
  Valor Econômico — valor.com.br                   (PT-BR, macro)
  CVM notices     — gov.br/cvm                     (PT-BR, regulatory)
  BCB notes       — bcb.gov.br                     (PT-BR, monetary policy)

Impact classification is rule-based on source weight + keyword matching.
HOT  = SELIC, COPOM, IPCA, Fed, earnings surprise, geopolitical shock
WARM = company news, GDP, trade balance, sector data
COLD = general commentary, analyst notes, minor moves
"""
from __future__ import annotations

import asyncio
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from xml.etree.ElementTree import Element  # type only; parsing uses defusedxml

import defusedxml.ElementTree as ET  # safe against XML entity expansion attacks
import httpx
import structlog

log = structlog.get_logger(__name__)


# ── Feed definitions ──────────────────────────────────────────────────────────

@dataclass
class FeedSource:
    name: str
    url: str
    language: str     # "pt-BR" | "en"
    base_weight: int  # 1=low, 2=mid, 3=high source authority


FEEDS: list[FeedSource] = [
    FeedSource("Reuters Mercados",   "https://feeds.reuters.com/reuters/businessNews",           "en",    3),
    FeedSource("Reuters Brasil",     "https://br.reuters.com/rssFeed/economicsNews",             "pt-BR", 3),
    FeedSource("Infomoney",          "https://www.infomoney.com.br/feed/",                       "pt-BR", 2),
    FeedSource("Valor Econômico",    "https://valor.globo.com/rss/financas/index.xml",           "pt-BR", 3),
    FeedSource("CVM Notícias",       "https://www.gov.br/cvm/pt-br/assuntos/noticias/RSS",       "pt-BR", 3),
    FeedSource("BCB Notas",          "https://www.bcb.gov.br/api/feed/noticias",                 "pt-BR", 3),
    FeedSource("Broadcast Agência",  "https://www.moneytimes.com.br/feed/",                      "pt-BR", 2),
    FeedSource("Investing.com BR",   "https://br.investing.com/rss/news_301.rss",                "pt-BR", 2),
]


# ── Impact keyword rules ──────────────────────────────────────────────────────

_HOT_KEYWORDS = {
    # Monetary policy
    "selic", "copom", "fed", "federal reserve", "juros", "taxa básica",
    "hawkish", "dovish", "hike", "cut", "pivot",
    # Inflation
    "ipca", "igpm", "inflação", "inflation", "cpi",
    # Macro shocks
    "recessão", "recession", "default", "calote", "crise", "crisis",
    "guerra", "war", "sanção", "sanction", "eleição", "election",
    # Earnings / corporate
    "resultado surpreende", "lucro acima", "lucro abaixo", "prejuízo",
    "guidance", "revisão para cima", "revisão para baixo",
    # Commodity shocks
    "petróleo dispara", "oil surge", "minério de ferro",
}

_WARM_KEYWORDS = {
    "resultado", "lucro", "receita", "ebitda", "dividendo", "proventos",
    "pib", "gdp", "balança comercial", "exportações", "produção industrial",
    "ibovespa", "dólar", "câmbio", "bolsa", "ações", "mercado",
    "petróleo", "oil", "minério", "iron ore", "commodities",
    "analista", "analyst", "target", "preço-alvo", "recomendação",
    "ipo", "oferta pública", "follow-on", "debênture",
    "fusão", "aquisição", "merger", "acquisition", "m&a",
}

_COLD_KEYWORDS: set[str] = set()   # default — everything else


def classify_impact(title: str, summary: str, source_weight: int) -> str:
    text = (title + " " + summary).lower()

    hot_hits  = sum(1 for kw in _HOT_KEYWORDS  if kw in text)
    warm_hits = sum(1 for kw in _WARM_KEYWORDS if kw in text)

    if hot_hits >= 1 or (source_weight == 3 and hot_hits >= 1):
        return "HOT"
    if warm_hits >= 2 or (source_weight >= 2 and warm_hits >= 1):
        return "WARM"
    return "COLD"


# ── News item ─────────────────────────────────────────────────────────────────

@dataclass
class NewsItem:
    id: str                          # sha1 of url
    source: str
    language: str
    title: str
    summary: str
    url: str
    published: str                   # ISO8601
    impact: str                      # HOT | WARM | COLD
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "source":    self.source,
            "language":  self.language,
            "title":     self.title,
            "summary":   self.summary,
            "url":       self.url,
            "published": self.published,
            "impact":    self.impact,
            "keywords":  self.keywords,
        }


# ── Fetcher ───────────────────────────────────────────────────────────────────

class NewsFetcher:
    def __init__(self, redis: Any) -> None:
        self._redis   = redis
        self._running = False
        self._client: httpx.AsyncClient | None = None
        self._seen: set[str] = set()       # deduplicate across cycles

    async def start(self) -> None:
        self._client  = httpx.AsyncClient(timeout=15.0, follow_redirects=True,
                                          headers={"User-Agent": "QuantBR/1.0"})
        self._running = True
        asyncio.create_task(self._loop())
        log.info("news_fetcher.started", sources=len(FEEDS))

    async def stop(self) -> None:
        self._running = False
        if self._client:
            await self._client.aclose()

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._fetch_all()
            except Exception as exc:
                log.warning("news_fetcher.cycle.error", error=str(exc))
            await asyncio.sleep(120)   # refresh every 2 minutes

    async def _fetch_all(self) -> None:
        tasks = [self._fetch_feed(src) for src in FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items: list[NewsItem] = []
        for r in results:
            if isinstance(r, list):
                items.extend(r)

        if not items:
            return

        # Sort newest first
        items.sort(key=lambda x: x.published, reverse=True)

        # Store all items list
        payload = json.dumps([i.to_dict() for i in items[:200]])
        await self._redis.setex("news:all", 300, payload)

        # Separate by impact
        for impact in ("HOT", "WARM", "COLD"):
            filtered = [i.to_dict() for i in items if i.impact == impact]
            await self._redis.setex(f"news:{impact.lower()}", 300, json.dumps(filtered))

        # Publish new HOT items
        for item in items:
            if item.impact == "HOT" and item.id not in self._seen:
                await self._redis.publish("news:hot", json.dumps(item.to_dict()))
            self._seen.add(item.id)

        # Keep seen set bounded
        if len(self._seen) > 5000:
            self._seen = set(list(self._seen)[-2000:])

        log.info("news_fetcher.cycle.done", total=len(items),
                 hot=sum(1 for i in items if i.impact == "HOT"))

    async def _fetch_feed(self, src: FeedSource) -> list[NewsItem]:
        try:
            resp = await self._client.get(src.url, timeout=10)  # type: ignore[union-attr]
            resp.raise_for_status()
            return self._parse_rss(resp.text, src)
        except Exception as exc:
            log.debug("news_fetcher.feed.error", source=src.name, error=str(exc))
            return []

    def _parse_rss(self, xml_text: str, src: FeedSource) -> list[NewsItem]:
        items: list[NewsItem] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        # Handle both RSS 2.0 and Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = (
            root.findall(".//item") or
            root.findall(".//atom:entry", ns)
        )

        for entry in entries[:20]:
            title   = _tag(entry, "title")
            link    = _tag(entry, "link") or _tag(entry, "atom:link", ns) or ""
            summary = _tag(entry, "description") or _tag(entry, "atom:summary", ns) or ""
            pubdate = _tag(entry, "pubDate") or _tag(entry, "atom:published", ns) or ""

            if not title or not link:
                continue

            item_id = hashlib.sha1(link.encode()).hexdigest()[:16]
            impact  = classify_impact(title, summary, src.base_weight)
            kws     = _extract_keywords(title + " " + summary)

            items.append(NewsItem(
                id=item_id,
                source=src.name,
                language=src.language,
                title=title.strip(),
                summary=_strip_html(summary)[:300],
                url=link.strip(),
                published=_normalise_date(pubdate),
                impact=impact,
                keywords=kws,
            ))

        return items


# ── XML helpers ───────────────────────────────────────────────────────────────

def _tag(el: Element, tag: str, ns: dict | None = None) -> str:
    child = el.find(tag, ns) if ns else el.find(tag)
    if child is None:
        return ""
    return (child.text or "").strip()


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


def _normalise_date(raw: str) -> str:
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    # Try common formats
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(raw.strip(), fmt).isoformat()
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat()


def _extract_keywords(text: str) -> list[str]:
    text_lower = text.lower()
    hits = [kw for kw in (_HOT_KEYWORDS | _WARM_KEYWORDS) if kw in text_lower]
    return hits[:10]
