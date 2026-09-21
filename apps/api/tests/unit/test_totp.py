"""Unit tests for the RFC 6238 TOTP primitives (feature #10, MFA).

Includes the canonical RFC 6238 Appendix B test vectors for the SHA-1 variant,
which is what authenticator apps use, so we know the implementation is correct
and interoperable rather than merely self-consistent.
"""

from __future__ import annotations

from app.security import totp

# RFC 6238 Appendix B secret: the ASCII string "12345678901234567890".
RFC_SECRET_B32 = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

# (unix time, expected 8-digit SHA-1 TOTP) from the RFC.
RFC_VECTORS = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]


def test_rfc6238_test_vectors():
    for at, expected in RFC_VECTORS:
        got = totp.generate_totp(RFC_SECRET_B32, digits=8, period=30, at=at)
        assert got == expected, f"at={at} expected {expected} got {got}"


def test_generate_secret_is_valid_base32():
    import base64

    secret = totp.generate_secret()
    padding = "=" * (-len(secret) % 8)
    # Should decode without error.
    raw = base64.b32decode(secret + padding, casefold=True)
    assert len(raw) == 20


def test_verify_accepts_current_code():
    secret = totp.generate_secret()
    code = totp.generate_totp(secret, at=1000.0)
    assert totp.verify_totp(secret, code, at=1000.0)


def test_verify_tolerates_skew_within_window():
    secret = totp.generate_secret()
    # code from the previous 30s step should still verify with valid_window=1
    prev = totp.generate_totp(secret, at=1000.0)
    assert totp.verify_totp(secret, prev, at=1035.0, valid_window=1)


def test_verify_rejects_code_outside_window():
    secret = totp.generate_secret()
    old = totp.generate_totp(secret, at=1000.0)
    # 5 minutes later, well outside a +/-1 step window
    assert not totp.verify_totp(secret, old, at=1300.0, valid_window=1)


def test_verify_rejects_malformed_codes():
    secret = totp.generate_secret()
    assert not totp.verify_totp(secret, "", at=1000.0)
    assert not totp.verify_totp(secret, "abc", at=1000.0)
    assert not totp.verify_totp(secret, "12345", at=1000.0)  # wrong length


def test_provisioning_uri_shape():
    secret = "JBSWY3DPEHPK3PXP"
    uri = totp.provisioning_uri(secret, account_name="[email protected]", issuer="ComplyGraph")
    assert uri.startswith("otpauth://totp/")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "issuer=ComplyGraph" in uri


def test_backup_codes_unique_and_hashable():
    codes = totp.generate_backup_codes(10)
    assert len(codes) == 10
    assert len(set(codes)) == 10
    # normalization + hashing is stable and case/space-insensitive
    h1 = totp.hash_backup_code(codes[0].upper())
    h2 = totp.hash_backup_code(f"  {codes[0]}  ")
    assert h1 == h2
