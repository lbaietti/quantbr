from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    pool_size=_settings.database_pool_size,
    max_overflow=_settings.database_max_overflow,
    echo=_settings.app_debug,
    future=True,
)


class Base(DeclarativeBase):
    pass
