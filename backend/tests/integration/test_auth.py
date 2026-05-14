"""
Integration tests for auth endpoints.
ISO 25010 — Testability: auth flow covered end-to-end.
ISO 27001 A.9 — Verify access control enforcement.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_missing_body(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_credentials(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/market/instruments")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_protected_endpoint_bad_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/market/instruments",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
