"""Supabase client wrappers.

Two clients are exposed:
- `anon()`  — uses the anon key, applies RLS as the authenticated user
              (when an Authorization header is forwarded).
- `service()` — uses the service role key, bypasses RLS. Use only for
                server-side trusted operations (worker pipeline, admin).
"""
from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

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
