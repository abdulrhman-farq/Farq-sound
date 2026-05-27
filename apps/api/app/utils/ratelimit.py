"""Per-user rate limiting using slowapi (Redis-backed when REDIS_URL set).

Endpoints opt in with `@limiter.limit("N/period")`. The key extractor
prefers the authenticated user id (sub claim) so limits aren't shared
across users behind the same NAT.
"""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _key(request: Request) -> str:
    # Prefer the verified user id if present (set by auth dep below).
    user = getattr(request.state, "user", None)
    if user is not None:
        return f"user:{user.id}"
    return f"ip:{get_remote_address(request)}"


_settings = get_settings()
limiter = Limiter(
    key_func=_key,
    storage_uri=_settings.redis_url or "memory://",
    default_limits=[],
)
