"""Unit tests for scanner network safety (SSRF protection) and prod config guard."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.errors import ValidationError
from app.scanners import net_safety


def test_private_targets_allowed_when_flag_true(monkeypatch):
    monkeypatch.setattr(net_safety.settings, "allow_private_scan_targets", True)
    # Should not raise regardless of host.
    net_safety.assert_safe_host("localhost")
    net_safety.assert_safe_dsn("postgresql+psycopg://u:p@127.0.0.1:5432/db")


def test_localhost_blocked_when_flag_false(monkeypatch):
    monkeypatch.setattr(net_safety.settings, "allow_private_scan_targets", False)
    with pytest.raises(ValidationError):
        net_safety.assert_safe_host("localhost")


def test_private_ip_blocked_when_flag_false(monkeypatch):
    monkeypatch.setattr(net_safety.settings, "allow_private_scan_targets", False)
    for host in ("127.0.0.1", "10.0.0.5", "192.168.1.10", "169.254.169.254"):
        with pytest.raises(ValidationError):
            net_safety.assert_safe_host(host)


def test_dsn_host_extraction_blocks_private(monkeypatch):
    monkeypatch.setattr(net_safety.settings, "allow_private_scan_targets", False)
    with pytest.raises(ValidationError):
        net_safety.assert_safe_dsn("postgresql+psycopg://user:secret@10.1.2.3:5432/app")


def test_production_refuses_dev_secrets():
    prod = Settings(
        environment="production",
        secret_key="dev-secret-key-change-me",
        app_encryption_key="dev-encryption-key-change-me-0123456789abcdefABCDEF=",
        allow_private_scan_targets=True,
    )
    problems = prod.validate_production_safety()
    assert any("SECRET_KEY" in p for p in problems)
    assert any("APP_ENCRYPTION_KEY" in p for p in problems)
    assert any("ALLOW_PRIVATE_SCAN_TARGETS" in p for p in problems)


def test_production_ok_with_strong_secrets():
    prod = Settings(
        environment="production",
        secret_key="a-strong-unique-secret-value",
        app_encryption_key="another-strong-unique-encryption-key-value",
        allow_private_scan_targets=False,
    )
    assert prod.validate_production_safety() == []


def test_development_never_flags():
    dev = Settings(environment="development")
    assert dev.validate_production_safety() == []
