"""Network-safety helpers for scanner connectors (SSRF protection).

Connectors accept user-supplied DSNs/URLs. In a multi-tenant deployment a
tenant could point a connector at an internal service (cloud metadata endpoints,
localhost, private ranges). These helpers validate a target host before any
connection is attempted.

Controlled by settings.allow_private_scan_targets: when True (dev default),
validation is skipped; when False (recommended in production), private/reserved
targets are rejected.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit

from app.core.config import settings
from app.core.errors import ValidationError


def _host_from_dsn(dsn: str) -> str | None:
    """Extract the host from a SQLAlchemy/URL-style DSN without leaking credentials."""
    # SQLAlchemy DSNs look like postgresql+psycopg://user:pass@host:port/db
    try:
        parsed = urlsplit(dsn)
    except ValueError:
        return None
    return parsed.hostname


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_safe_host(host: str | None) -> None:
    """Raise ValidationError if the host resolves to a private/reserved address.

    No-op when settings.allow_private_scan_targets is True.
    """
    if settings.allow_private_scan_targets:
        return
    if not host:
        raise ValidationError("Connector target host is missing or unparseable.")

    lowered = host.lower()
    if lowered in {"localhost", "localhost.localdomain"}:
        raise ValidationError("Connector target host is not permitted (loopback).")

    # Resolve every address the host maps to and reject if any is internal.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValidationError("Connector target host could not be resolved.") from exc

    for info in infos:
        addr = info[4][0].split("%", 1)[0]  # strip IPv6 scope id if present
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise ValidationError(
                "Connector target resolves to a private, loopback, or reserved "
                "address, which is not permitted."
            )


def assert_safe_dsn(dsn: str) -> None:
    """Validate the host portion of a database DSN."""
    assert_safe_host(_host_from_dsn(dsn))
