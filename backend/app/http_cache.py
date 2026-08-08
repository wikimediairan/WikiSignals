"""Shared Cache-Control helpers for public read API responses."""

from __future__ import annotations

from fastapi import Response

from app.config import Settings, get_settings


def set_public_cache(response: Response, settings: Settings | None = None) -> None:
    """
    Short max-age so metric charts refresh after collection jobs without a hard reload.
    stale-while-revalidate lets the browser show a brief stale copy while revalidating.
    """
    s = settings or get_settings()
    max_age = max(0, int(s.public_cache_max_age_seconds))
    swr = max(0, int(s.public_cache_stale_while_revalidate_seconds))
    parts = [f"public, max-age={max_age}"]
    if swr > 0:
        parts.append(f"stale-while-revalidate={swr}")
    response.headers["Cache-Control"] = ", ".join(parts)
