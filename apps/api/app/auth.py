"""Auth: Supabase JWT first, X-Device-Id guest fallback.

`require_user`:
  - Authorization: Bearer <jwt>  → verified Supabase user (role=authenticated)
  - X-Device-Id: <uuid>          → synthetic guest (role=guest)
  - else                         → 401

For guests, a profile row is auto-upserted (no FK to auth.users since the
guest_mode migration dropped it). This lets the entire order flow work
without account creation, which is what we want for the "let me see if
this thing actually works" path.
"""
from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.config import get_settings

log = logging.getLogger(__name__)


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    role: str = "authenticated"

    @property
    def is_guest(self) -> bool:
        return self.role == "guest"


def _decode(token: str) -> dict:
    s = get_settings()
    if not s.supabase_jwt_secret:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "SUPABASE_JWT_SECRET not configured.",
        )
    try:
        return jwt.decode(
            token,
            s.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}"
        ) from exc


def _ensure_guest_profile(device_id: str) -> None:
    """Idempotently upsert a profiles row for a guest device id."""
    from app.db import service

    try:
        service().table("profiles").upsert(
            {"id": device_id}, on_conflict="id"
        ).execute()
    except Exception as exc:  # don't 500 if upsert fails — log and continue
        log.warning("guest profile upsert failed: %s", exc)


def require_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    x_device_id: Annotated[str | None, Header()] = None,
) -> AuthUser:
    # Path 1 — Supabase JWT
    if authorization and authorization.lower().startswith("bearer "):
        payload = _decode(authorization.split(" ", 1)[1])
        user = AuthUser(
            id=payload["sub"],
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
        )
        request.state.user = user
        return user

    # Path 2 — guest device id (any UUID-ish string of 16+ chars)
    if x_device_id and len(x_device_id) >= 16:
        _ensure_guest_profile(x_device_id)
        user = AuthUser(id=x_device_id, role="guest")
        request.state.user = user
        return user

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Missing Authorization header or X-Device-Id.",
    )


def require_admin(
    user: Annotated[AuthUser, Depends(require_user)],
) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only.")
    return user


CurrentUser = Annotated[AuthUser, Depends(require_user)]
CurrentAdmin = Annotated[AuthUser, Depends(require_admin)]
