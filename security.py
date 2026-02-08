"""
Security Utilities (SOTA 2026)
==============================
Shared security functions for Trinity and Angel.
"""

from fastapi import Request


# SOTA 2026: Trusted Proxies (Localhost only by default to prevent spoofing)
TRUSTED_PROXIES = {"127.0.0.1", "::1", "localhost"}


def get_real_ip(request: Request) -> str:
    """
    SOTA 2026: Extract real client IP behind reverse proxy (Caddy).
    SECURED: Only accepts X-Forwarded-For if request comes from trusted proxy.
    """
    client_host = request.client.host if request.client else ""

    # 1. Direct Connection (or untrusted proxy) -> Return immediate IP
    if client_host not in TRUSTED_PROXIES:
        return client_host

    # 2. Trusted Proxy -> Trust Headers
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        # X-Forwarded-For: client, proxy1, proxy2 → take first (real client)
        return xff.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP", "")
    if x_real_ip:
        return x_real_ip.strip()

    return client_host


def get_rate_limit_key(request: Request) -> str:
    """Rate limit key using real IP (works behind Caddy proxy)."""
    return get_real_ip(request)
