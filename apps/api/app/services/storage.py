"""Supabase Storage wrapper — uploads files and returns signed URLs."""
from __future__ import annotations

import logging
from pathlib import Path

from app.config import get_settings
from app.db import service

log = logging.getLogger(__name__)


def upload_audio(local_path: Path, key: str, content_type: str = "audio/mpeg") -> str:
    """Upload local file to the configured Supabase Storage bucket and
    return a signed URL valid for 7 days.
    """
    s = get_settings()
    client = service()
    bucket = client.storage.from_(s.supabase_storage_bucket)
    with open(local_path, "rb") as fh:
        bucket.upload(
            path=key,
            file=fh,
            file_options={"content-type": content_type, "upsert": "true"},
        )
    signed = bucket.create_signed_url(key, expires_in=60 * 60 * 24 * 7)
    return signed["signedURL"]


def signed_url(key: str, expires_in_seconds: int = 3600) -> str:
    s = get_settings()
    client = service()
    bucket = client.storage.from_(s.supabase_storage_bucket)
    return bucket.create_signed_url(key, expires_in=expires_in_seconds)["signedURL"]
