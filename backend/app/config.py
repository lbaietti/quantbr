from functools import lru_cache
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production"] = "production"
    app_debug: bool = False
    app_version: str = "1.0.0"

    # Security — ISO 27001 A.9 / A.10
    secret_key: str = Field(..., min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database — required; no default to prevent accidental production misconfiguration
    database_url: str = Field(..., min_length=10)
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = ""

    # ZMQ feed
    zmq_feed_endpoint: str = "tcp://localhost:5555"

    # CORS — ISO 27001 A.14
    cors_origins: list[str] = ["http://localhost:5173"]

    # Rate limiting
    rate_limit_per_minute: int = 120

    # AI Agents — Anthropic Claude API
    anthropic_api_key: str = ""          # required for agents feature; empty disables it
    anthropic_model: str = "claude-sonnet-4-6"
    agent_messages_per_hour: int = 20    # per-user hourly cap

    # Audit logging — ISO 27001 A.12
    audit_log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
