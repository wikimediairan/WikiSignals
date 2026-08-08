"""Shared HTTP client with User-Agent, rate limiting, and retries."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_UA_POLICY = (
    "https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy"
)


def validate_user_agent(user_agent: str) -> list[str]:
    """Return human-readable warnings about a User-Agent string."""
    warnings: list[str] = []
    ua = (user_agent or "").strip()
    if not ua:
        warnings.append("USER_AGENT is empty — Wikimedia will return HTTP 403.")
        return warnings
    generic = ("python-httpx", "python-requests", "curl/", "wget/", "httpx/")
    if any(ua.lower().startswith(g) or g in ua.lower() for g in generic):
        warnings.append("USER_AGENT looks generic; Wikimedia may reject it with 403.")
    if "@localhost" in ua.lower() or "example.com" in ua.lower() or "example.org" in ua.lower():
        warnings.append(
            "USER_AGENT contact looks fake (@localhost / example.com). "
            "Use a real email or a real URL you control."
        )
    if not re.search(r"https?://|\S+@\S+\.\S+", ua):
        warnings.append(
            "USER_AGENT should include contact info (https://… URL or email@domain)."
        )
    if len(ua) < 12:
        warnings.append("USER_AGENT is very short; include app name/version and contact.")
    return warnings


def log_user_agent_warnings(user_agent: str) -> None:
    for w in validate_user_agent(user_agent):
        logger.warning("User-Agent policy: %s See %s", w, _UA_POLICY)


class RateLimitedClient:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None):
        self.settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        log_user_agent_warnings(self.settings.user_agent)

    async def __aenter__(self) -> RateLimitedClient:
        if self._client is None:
            ua = self.settings.user_agent.strip()
            # MediaWiki etiquette: User-Agent + Api-User-Agent with contact.
            self._client = httpx.AsyncClient(
                timeout=self.settings.http_timeout_seconds,
                headers={
                    "User-Agent": ua,
                    "Api-User-Agent": ua,
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self.settings.http_min_interval_seconds - (now - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    def _policy_error(self, url: str, resp: httpx.Response) -> RuntimeError:
        body = (resp.text or "")[:500]
        hints = validate_user_agent(self.settings.user_agent)
        hint_txt = " ".join(hints) if hints else (
            "Check USER_AGENT includes a real contact URL or email, and slow down requests."
        )
        return RuntimeError(
            f"HTTP {resp.status_code} from {url}. {hint_txt} "
            f"Policy: {_UA_POLICY}. Response: {body!r}"
        )

    async def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        assert self._client is not None
        last_error: Exception | None = None
        for attempt in range(self.settings.http_max_retries + 1):
            await self._throttle()
            try:
                resp = await self._client.get(url, params=params)
                if resp.status_code == 404:
                    return None

                # Rate limits / temporary blocks: retry with backoff
                if resp.status_code in (429, 503):
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else min(60, 2**attempt)
                    logger.warning("Rate limited (%s) on %s; sleeping %.1fs", resp.status_code, url, delay)
                    await asyncio.sleep(delay)
                    continue

                if resp.status_code == 403:
                    body = (resp.text or "").lower()
                    # User-Agent policy failures are permanent for this UA — fail clearly
                    if "user-agent" in body or "user agent" in body:
                        raise self._policy_error(url, resp)
                    # Other 403s (edge/WAF/temporary) — retry a few times
                    delay = min(60, 3 * (2**attempt))
                    logger.warning(
                        "HTTP 403 on %s (attempt %s); body=%r; sleeping %.1fs",
                        url,
                        attempt + 1,
                        (resp.text or "")[:200],
                        delay,
                    )
                    if attempt >= self.settings.http_max_retries:
                        raise self._policy_error(url, resp)
                    await asyncio.sleep(delay)
                    continue

                if resp.status_code == 400:
                    raise RuntimeError(
                        f"HTTP 400 Bad Request for {url}: {(resp.text or '')[:300]!r}"
                    )

                resp.raise_for_status()
                return resp.json()
            except RuntimeError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = exc
                delay = min(60, 2**attempt)
                logger.warning("HTTP error attempt %s for %s: %s", attempt + 1, url, exc)
                await asyncio.sleep(delay)
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                delay = min(60, 2**attempt)
                logger.warning("HTTP error attempt %s for %s: %s", attempt + 1, url, exc)
                await asyncio.sleep(delay)
        raise RuntimeError(f"Failed GET {url}: {last_error}")
