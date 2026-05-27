"""Public catalog endpoints."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.db import anon
from app.schemas import SongDetail, SongSegment, SongSummary

router = APIRouter()


@router.get("", response_model=list[SongSummary])
def list_songs(
    era: Literal["classic", "modern"] | None = None,
    search: str | None = Query(None, min_length=1, max_length=64),
) -> list[SongSummary]:
    q = anon().table("songs").select(
        "id, slug, title_ar, title_en, artist_ar, era, "
        "duration_seconds, preview_url, cover_image_url, price_sar"
    ).eq("is_active", True)
    if era:
        q = q.eq("era", era)
    if search:
        q = q.ilike("title_ar", f"%{search}%")
    rows = q.order("created_at", desc=True).execute().data or []
    return [SongSummary.model_validate(r) for r in rows]


@router.get("/{slug}", response_model=SongDetail)
def get_song(slug: str) -> SongDetail:
    song_row = (
        anon()
        .table("songs")
        .select(
            "id, slug, title_ar, title_en, artist_ar, era, "
            "duration_seconds, preview_url, cover_image_url, price_sar"
        )
        .eq("slug", slug)
        .eq("is_active", True)
        .single()
        .execute()
    ).data
    if not song_row:
        raise HTTPException(404, "Song not found.")

    segments_rows = (
        anon()
        .table("song_segments")
        .select(
            "id, role, sequence_index, start_ms, end_ms, "
            "original_text_ar, phonetic_hint, prosody_note"
        )
        .eq("song_id", song_row["id"])
        .order("sequence_index")
        .execute()
    ).data or []

    segments = [SongSegment.model_validate(s) for s in segments_rows]
    required_roles = sorted({s.role for s in segments})
    return SongDetail(
        **song_row,
        segments=segments,
        required_roles=required_roles,  # type: ignore[arg-type]
    )
