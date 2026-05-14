"""
ISO 25010 — Reliability / Availability: liveness and readiness probes.
Kubernetes / load-balancer friendly.
"""
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(request: Request) -> JSONResponse:
    checks: dict[str, str] = {}

    # Redis ping
    try:
        await request.app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    code    = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse({"status": "ok" if healthy else "degraded", "checks": checks}, status_code=code)
