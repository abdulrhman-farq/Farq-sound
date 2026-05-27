"""In-memory demo catalog used when Supabase is not configured.

Lets the site run end-to-end against a `pnpm dev` / `uvicorn` boot with
zero external services, so reviewers can see the UI without provisioning
Supabase, ElevenLabs, or Moyasar.
"""
from __future__ import annotations

from uuid import UUID

from app.config import get_settings


def is_demo_mode() -> bool:
    s = get_settings()
    return not (s.supabase_url and s.supabase_service_role_key)


_SONGS: list[dict] = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "slug": "demo-classic-1",
        "title_ar": "زفّة العروس الكلاسيكية",
        "title_en": "Classic Bridal Entrance",
        "artist_ar": "فرقة فرق ساوند",
        "era": "classic",
        "duration_seconds": 180,
        "preview_url": "/samples/preview-demo-classic-1.mp3",
        "cover_image_url": None,
        "price_sar": 49,
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "slug": "demo-classic-2",
        "title_ar": "هلا بالعروس",
        "title_en": "Welcome to the Bride",
        "artist_ar": "فرقة فرق ساوند",
        "era": "classic",
        "duration_seconds": 160,
        "preview_url": "/samples/preview-demo-classic-2.mp3",
        "cover_image_url": None,
        "price_sar": 49,
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "slug": "demo-modern-1",
        "title_ar": "ليلتنا حلوة",
        "title_en": "Our Beautiful Night",
        "artist_ar": "فرقة فرق ساوند",
        "era": "modern",
        "duration_seconds": 200,
        "preview_url": "/samples/preview-demo-modern-1.mp3",
        "cover_image_url": None,
        "price_sar": 59,
    },
]


_SEGMENTS: dict[str, list[dict]] = {
    "00000000-0000-0000-0000-000000000001": [
        {
            "id": "10000000-0000-0000-0000-000000000001",
            "role": "bride",
            "sequence_index": 0,
            "start_ms": 12000,
            "end_ms": 14500,
            "original_text_ar": "[اسم العروس]",
            "phonetic_hint": None,
            "prosody_note": "sung",
        },
        {
            "id": "10000000-0000-0000-0000-000000000002",
            "role": "groom",
            "sequence_index": 1,
            "start_ms": 28000,
            "end_ms": 30500,
            "original_text_ar": "[اسم العريس]",
            "phonetic_hint": None,
            "prosody_note": "sung",
        },
    ],
    "00000000-0000-0000-0000-000000000002": [
        {
            "id": "10000000-0000-0000-0000-000000000003",
            "role": "bride",
            "sequence_index": 0,
            "start_ms": 8000,
            "end_ms": 10000,
            "original_text_ar": "[اسم العروس]",
            "phonetic_hint": None,
            "prosody_note": "sung",
        },
    ],
    "00000000-0000-0000-0000-000000000003": [
        {
            "id": "10000000-0000-0000-0000-000000000004",
            "role": "bride",
            "sequence_index": 0,
            "start_ms": 15000,
            "end_ms": 17500,
            "original_text_ar": "[اسم العروس]",
            "phonetic_hint": None,
            "prosody_note": "sung",
        },
        {
            "id": "10000000-0000-0000-0000-000000000005",
            "role": "groom",
            "sequence_index": 1,
            "start_ms": 32000,
            "end_ms": 34500,
            "original_text_ar": "[اسم العريس]",
            "phonetic_hint": None,
            "prosody_note": "sung",
        },
    ],
}


def list_songs(era: str | None = None, search: str | None = None) -> list[dict]:
    rows = list(_SONGS)
    if era:
        rows = [r for r in rows if r["era"] == era]
    if search:
        rows = [r for r in rows if search in r["title_ar"]]
    return rows


def get_song_by_slug(slug: str) -> dict | None:
    for r in _SONGS:
        if r["slug"] == slug:
            return r
    return None


def get_segments(song_id: str | UUID) -> list[dict]:
    return _SEGMENTS.get(str(song_id), [])
