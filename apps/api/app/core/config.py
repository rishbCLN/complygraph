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

    # Scheduled rescans (celery-beat). Set interval to 0 to disable.
    scheduled_rescan_enabled: bool = True
    scheduled_rescan_interval_hours: int = 24
    scheduled_rescan_min_age_hours: int = 20  # only rescan connectors idle at least this long

    # Security
    secret_key: str = "dev-secret-key-change-me"
    app_encryption_key: str = "dev-encryption-key-change-me-0123456789abcdefABCDEF="
    session_ttl_hours: int = 12
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    # Public Privacy Center portal: per-identifier write throttle (grant/withdraw/DSR).
    privacy_center_enabled: bool = True
    privacy_center_rate_limit_attempts: int = 20
    privacy_center_rate_limit_window_seconds: int = 300
    cors_origins: str = "http://localhost:3000"

    # File uploads
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB
    storage_dir: str = "/data/storage"
    allowed_upload_extensions: str = "csv,json,pdf,txt"

    # Scanner network safety (SSRF protection).
    # When False (recommended in production), connectors may not target loopback,
    # private, link-local, or otherwise-reserved IP addresses.
    allow_private_scan_targets: bool = True

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

    # Values that must never be used in production.
    _DEV_SECRET_KEY = "dev-secret-key-change-me"
    _DEV_ENCRYPTION_KEY = "dev-encryption-key-change-me-0123456789abcdefABCDEF="

    def validate_production_safety(self) -> list[str]:
        """Return a list of fatal misconfigurations for a production deployment.

        Empty list means safe. Callers (startup) should refuse to boot if non-empty.
        """
        problems: list[str] = []
        if not self.is_production:
            return problems
        if self.secret_key == self._DEV_SECRET_KEY:
            problems.append("SECRET_KEY is still the development default.")
        if self.app_encryption_key == self._DEV_ENCRYPTION_KEY:
            problems.append("APP_ENCRYPTION_KEY is still the development default.")
        if self.allow_private_scan_targets:
            problems.append(
                "ALLOW_PRIVATE_SCAN_TARGETS is enabled; set it to false in production "
                "to prevent connectors from reaching internal/private hosts (SSRF)."
            )
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
