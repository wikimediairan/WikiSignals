"""Security helpers: validation, headers, production safeguards."""

from __future__ import annotations

import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Project IDs are dotted wiki ids: fa.wikipedia, commons.wikimedia, wikidata
PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")
# Replica database names: fawiki, enwiki, commonswiki, …
DBNAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
METRIC_ID_RE = re.compile(r"^[a-z][a-z0-9._-]{0,127}$")


def is_safe_project_id(value: str) -> bool:
    return bool(value and PROJECT_ID_RE.match(value) and ".." not in value)


def is_safe_dbname(value: str) -> bool:
    """Whitelist-style validation for MediaWiki replica schema names."""
    if not value or not DBNAME_RE.match(value):
        return False
    # Refuse obvious injection / path tricks
    banned = (";", "-", " ", "/", "\\", "`", "'", '"', "%", "\x00")
    return not any(b in value for b in banned)


def is_safe_metric_id(value: str) -> bool:
    return bool(value and METRIC_ID_RE.match(value))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add conservative security headers for a public read-only analytics app."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        # Fallback only when handlers did not set Cache-Control (e.g. errors)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault(
                "Cache-Control", "public, max-age=60, stale-while-revalidate=300"
            )
        return response
