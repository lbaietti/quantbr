"""
QuantBR Backend — FastAPI application entry point.

ISO 25010:
  - Functional Suitability: complete REST + WebSocket API
  - Performance Efficiency: async I/O throughout, Redis caching
  - Reliability: lifespan manages all resources; graceful shutdown
  - Security: CORS, rate-limiting, JWT auth on all routes
  - Maintainability: modular routers, dependency injection

ISO 27001:
  - A.9  Access Control: JWT + RBAC on every endpoint
  - A.10 Cryptography: bcrypt passwords, HS256 JWT
  - A.12 Logging & Monitoring: structured audit log
  - A.14 Secure Development: CORS whitelist, input validation via Pydantic
"""
import structlog
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette_prometheus import PrometheusMiddleware, metrics

from app.config import get_settings
from app.api.v1 import router as v1_router
from app.api.health import router as health_router
from app.feed.subscriber import FeedSubscriber
from app.signals.engine import SignalEngine
from app.quantlab.registry import StrategyRegistry
from app.market_data.fetcher import MarketDataFetcher
from app.market_data.news_fetcher import NewsFetcher

# ── Structured logging setup (ISO 27001 A.12.4) ──────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logging.basicConfig(level=logging.INFO)
log = structlog.get_logger(__name__)


# ── Application lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Redis
    redis = aioredis.from_url(
        settings.redis_url,
        password=settings.redis_password or None,
        encoding="utf-8",
        decode_responses=True,
    )
    app.state.redis = redis

    # Signal engine
    engine = SignalEngine()
    app.state.signal_engine = engine

    # QuantLab strategy registry
    strategy_registry = StrategyRegistry(redis=redis)
    app.state.strategy_registry = strategy_registry

    # ZMQ feed subscriber
    subscriber = FeedSubscriber(redis=redis, signal_engine=engine, strategy_registry=strategy_registry)
    await subscriber.start()
    app.state.feed_subscriber = subscriber

    # Live B3/BCB reference data fetcher
    market_fetcher = MarketDataFetcher(redis=redis)
    await market_fetcher.start()
    app.state.market_fetcher = market_fetcher

    # News aggregator (Reuters, Infomoney, Valor, CVM, BCB…)
    news_fetcher = NewsFetcher(redis=redis)
    await news_fetcher.start()
    app.state.news_fetcher = news_fetcher

    log.info("app.started", version=settings.app_version, env=settings.app_env)
    yield

    # Shutdown
    await subscriber.stop()
    await market_fetcher.stop()
    await news_fetcher.stop()
    await redis.aclose()
    log.info("app.stopped")


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="QuantBR API",
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # CORS — ISO 27001 A.14 (whitelist only; explicit methods — no wildcard)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Prometheus metrics — ISO 25010 Performance Efficiency
    # /metrics is restricted to loopback in production via reverse proxy (nginx allow 127.0.0.1)
    app.add_middleware(PrometheusMiddleware)
    if not settings.is_production:
        app.add_route("/metrics", metrics)

    # Routers
    app.include_router(health_router)
    app.include_router(v1_router, prefix="/api")

    # Global exception handler — never leak stack traces in production
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            {"detail": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return app


app = create_app()
