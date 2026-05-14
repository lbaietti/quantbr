from fastapi import APIRouter
from .auth import router as auth_router
from .market import router as market_router
from .signals import router as signals_router
from .ws import router as ws_router
from .orderflow import router as orderflow_router
from .lab import router as lab_router
from .news import router as news_router
from .reference import router as reference_router
from .agents import router as agents_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router,      prefix="/auth",       tags=["auth"])
router.include_router(market_router,    prefix="/market",     tags=["market"])
router.include_router(signals_router,   prefix="/signals",    tags=["signals"])
router.include_router(orderflow_router, prefix="/orderflow",  tags=["order-flow"])
router.include_router(lab_router,       prefix="/lab",        tags=["quant-lab"])
router.include_router(news_router,      prefix="/news",       tags=["news"])
router.include_router(reference_router, prefix="/reference",  tags=["reference"])
router.include_router(agents_router,    prefix="/agents",     tags=["agents"])
router.include_router(ws_router,                              tags=["websocket"])
