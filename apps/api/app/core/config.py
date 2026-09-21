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

    # Scheduled re-assessment: periodically re-run the control engine org-wide so
    # posture reflects new evidence/effective-dates without a manual trigger.
    scheduled_reassessment_enabled: bool = True
    scheduled_reassessment_interval_hours: int = 24

    # Reminders: generate in-app notifications for expiring evidence, overdue
    # findings/tasks/DSRs, risk reviews due, and controls due for re-assessment.
    reminders_enabled: bool = True
    reminders_interval_hours: int = 12
    reminder_evidence_expiry_days: int = 30  # warn this far ahead of evidence expiry
    reminder_dsr_due_days: int = 7  # warn this far ahead of a DSR statutory deadline
    control_reassess_interval_days: int = 90  # a control is "due" if last assessed longer ago

    # Email delivery is OPTIONAL and DORMANT until SMTP is configured. With no
    # smtp_host set, the notification service records in-app notifications only
    # and email dispatch is a no-op (nothing is sent, no error).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_address: str = "[email protected]"
    email_notifications_enabled: bool = False  # gate; also requires smtp_host

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

    # ------------------------------------------------------------------
    # Integrations (feature #10). Every integration below is fully real but
    # DORMANT by default: with no credentials configured the code paths are
    # inert (endpoints return a "not configured" state, dispatch is a no-op,
    # SSO/MFA are simply unavailable). Nothing here changes behaviour until
    # the corresponding environment variables are set.
    # ------------------------------------------------------------------

    # Outbound webhooks. Per-endpoint registration lives in the database
    # (org-scoped); this only bounds delivery behaviour. Webhooks are dispatched
    # only when at least one enabled endpoint exists, so no env flag is needed.
    webhooks_enabled: bool = True  # master kill-switch for outbound delivery
    webhook_timeout_seconds: float = 10.0
    webhook_max_attempts: int = 4  # initial try + retries with backoff
    webhook_retry_backoff_seconds: float = 2.0

    # Jira Cloud issue creation (findings/tasks/risks -> Jira issues).
    # Dormant until base_url + email + api_token + project_key are all set.
    jira_base_url: str = ""  # e.g. https://acme.atlassian.net
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""  # e.g. SEC
    jira_default_issue_type: str = "Task"
    jira_timeout_seconds: float = 15.0

    # ServiceNow incident creation (Table API).
    # Dormant until instance_url + username + password are all set.
    servicenow_instance_url: str = ""  # e.g. https://dev12345.service-now.com
    servicenow_username: str = ""
    servicenow_password: str = ""
    servicenow_timeout_seconds: float = 15.0

    # SSO - OpenID Connect (Authorization Code flow).
    # Dormant until issuer + client_id + client_secret are set.
    oidc_enabled: bool = True  # gate; also requires the fields below
    oidc_issuer: str = ""  # base issuer URL; discovery doc at /.well-known/openid-configuration
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_url: str = ""  # e.g. http://localhost:8000/api/v1/sso/oidc/callback
    oidc_scopes: str = "openid email profile"
    oidc_provider_name: str = "SSO"  # display label on the login button
    # Only pre-existing users (matched by verified email) may sign in via SSO
    # unless auto-provisioning is explicitly enabled.
    sso_auto_provision: bool = False
    sso_auto_provision_role: str = "VIEWER"
    # Org that auto-provisioned SSO users join. Empty => the first organization
    # (typical for a single-tenant enterprise SSO deployment).
    sso_default_org_slug: str = ""
    sso_post_login_redirect: str = "http://localhost:3000"

    # SSO - SAML 2.0 (SP-initiated, HTTP-Redirect AuthnRequest / HTTP-POST ACS).
    # Dormant until idp metadata (entity id, SSO URL, signing cert) + SP entity id are set.
    saml_enabled: bool = True  # gate; also requires the fields below
    saml_sp_entity_id: str = ""  # our SP entity id (audience)
    saml_sp_acs_url: str = ""  # Assertion Consumer Service URL (our callback)
    saml_idp_entity_id: str = ""
    saml_idp_sso_url: str = ""  # IdP SingleSignOn redirect endpoint
    saml_idp_x509_cert: str = ""  # IdP signing certificate (PEM body, base64 DER, or full PEM)
    saml_provider_name: str = "SAML SSO"

    # MFA - TOTP (RFC 6238). Users opt in individually; this only bounds policy.
    mfa_enabled: bool = True  # allow users to enrol in TOTP MFA
    mfa_issuer_name: str = "ComplyGraph"  # shown in authenticator apps
    mfa_totp_period_seconds: int = 30
    mfa_totp_digits: int = 6
    mfa_totp_valid_window: int = 1  # accept codes +/- this many periods (clock skew)
    mfa_challenge_ttl_seconds: int = 300  # how long a login MFA challenge stays valid
    mfa_backup_code_count: int = 10

    @property
    def effective_ai_mode(self) -> str:
        """Fall back to deterministic mode when no API key is configured."""
        if self.ai_mode == "anthropic" and self.anthropic_api_key.strip():
            return "anthropic"
        return "deterministic"

    @property
    def email_configured(self) -> bool:
        """Email dispatch is live only when explicitly enabled AND an SMTP host is set.

        Keeps the integration dormant (in-app notifications only) until real
        credentials are provided via the environment.
        """
        return self.email_notifications_enabled and bool(self.smtp_host.strip())

    @property
    def jira_configured(self) -> bool:
        """Jira issue creation is live only when all connection fields are set."""
        return bool(
            self.jira_base_url.strip()
            and self.jira_email.strip()
            and self.jira_api_token.strip()
            and self.jira_project_key.strip()
        )

    @property
    def servicenow_configured(self) -> bool:
        """ServiceNow incident creation is live only when all fields are set."""
        return bool(
            self.servicenow_instance_url.strip()
            and self.servicenow_username.strip()
            and self.servicenow_password.strip()
        )

    @property
    def oidc_configured(self) -> bool:
        """OIDC login is live only when enabled AND issuer/client credentials exist."""
        return bool(
            self.oidc_enabled
            and self.oidc_issuer.strip()
            and self.oidc_client_id.strip()
            and self.oidc_client_secret.strip()
            and self.oidc_redirect_url.strip()
        )

    @property
    def saml_configured(self) -> bool:
        """SAML login is live only when enabled AND IdP + SP metadata exist."""
        return bool(
            self.saml_enabled
            and self.saml_sp_entity_id.strip()
            and self.saml_sp_acs_url.strip()
            and self.saml_idp_sso_url.strip()
            and self.saml_idp_x509_cert.strip()
        )

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
