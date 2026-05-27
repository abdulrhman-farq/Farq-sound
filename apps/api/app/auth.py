"""Supabase JWT verification — used as a FastAPI dependency.

The verified user is also stashed in `request.state.user` so the
slowapi key function can scope rate limits per user.
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.config import get_settings


class AuthUser(BaseModel):
    id: str
    email: str | None = None
    role: str = "authenticated"


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


def require_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Missing bearer token."
        )
    payload = _decode(authorization.split(" ", 1)[1])
    user = AuthUser(
        id=payload["sub"],
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )
    # Expose to rate limiter / observability middleware.
    request.state.user = user
    return user


def require_admin(
    user: Annotated[AuthUser, Depends(require_user)],
) -> AuthUser:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only.")
    return user


CurrentUser = Annotated[AuthUser, Depends(require_user)]
CurrentAdmin = Annotated[AuthUser, Depends(require_admin)]
