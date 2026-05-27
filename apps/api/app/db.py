"""Supabase client wrappers.

Three flavors:

- `service()`  — service-role key, bypasses RLS. Reserved for trusted
                 server-side operations: worker pipeline, admin tasks,
                 webhook handlers, share RPC.

- `anon()`     — anon key, no auth. Used for unauthenticated reads of
                 public tables (catalog).

- `user(jwt)`  — anon key + a user's JWT applied as Authorization. Every
                 query runs through RLS as that user. **Use this for any
                 endpoint that touches per-user data** so a missing
                 `.eq("user_id", ...)` filter can never leak.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from supabase import Client, ClientOptions, create_client

from app.config import get_settings


@lru_cache(maxsize=1)
def service() -> Client:
    s = get_settings()
    if not (s.supabase_url and s.supabase_service_role_key):
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set."
        )
    return create_client(s.supabase_url, s.supabase_service_role_key)


@lru_cache(maxsize=1)
def anon() -> Client:
    s = get_settings()
    if not (s.supabase_url and s.supabase_anon_key):
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set."
        )
    return create_client(s.supabase_url, s.supabase_anon_key)


def user_client(jwt: str) -> Client:
    """Build a per-request client that applies RLS as the JWT's owner."""
    s = get_settings()
    return create_client(
        s.supabase_url,
        s.supabase_anon_key,
        options=ClientOptions(
            headers={"Authorization": f"Bearer {jwt}"},
        ),
    )


def _extract_jwt(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Missing bearer token."
        )
    return authorization.split(" ", 1)[1]


def current_db(
    authorization: Annotated[str | None, Header()] = None,
) -> Client:
    """FastAPI dependency that yields an RLS-scoped Supabase client."""
    return user_client(_extract_jwt(authorization))


UserDB = Annotated[Client, Depends(current_db)]
