"""Centralized application configuration.

All settings are read from environment variables (see .env.example).
Model configuration is centralized here so a model name is never hard-coded
throughout the codebase.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # App
    environment: str = "development"
    demo_mode: bool = True
    app_name: str = "ComplyGraph"
    api_v1_prefix: str = "/api/v1"

    # Database
    # Default to a local SQLite file so the app runs with zero external services.
    # Docker Compose overrides this with a PostgreSQL DATABASE_URL.
    database_url: str = "sqlite:///./complygraph.db"
    demo_database_url: str = ""  # empty -> DemoConnector uses synthetic in-memory data

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Security
    secret_key: str = "dev-secret-key-change-me"
    app_encryption_key: str = "dev-encryption-key-change-me-0123456789abcdefABCDEF="
    session_ttl_hours: int = 12
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    cors_origins: str = "http://localhost:3000"

    # File uploads
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB
    storage_dir: str = "/data/storage"
    allowed_upload_extensions: str = "csv,json,pdf,txt"

    # AI
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"
    ai_mode: str = "deterministic"  # anthropic | deterministic
    ai_max_calls_per_session: int = 20

    @property
    def effective_ai_mode(self) -> str:
        """Fall back to deterministic mode when no API key is configured."""
        if self.ai_mode == "anthropic" and self.anthropic_api_key.strip():
            return "anthropic"
        return "deterministic"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {e.strip().lower().lstrip(".") for e in self.allowed_upload_extensions.split(",") if e.strip()}

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
