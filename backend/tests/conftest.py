import os
os.environ.setdefault("SECRET_KEY", "test_secret_key_that_is_at_least_32_chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://quantbr:password@localhost:5432/quantbr_test")

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
