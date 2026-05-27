"""Admin endpoints — catalog onboarding.

The full Demucs + faster-whisper intake worker is invoked here as a
Celery task. The reviewer UI then PATCHes detected segment boundaries
before publish.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.auth import CurrentAdmin
from app.db import service
from app.services.tts import VoiceCloneRequest, get_tts_provider

router = APIRouter()


class IntakeCreate(BaseModel):
    source_audio_url: str
    title_ar: str


class IntakePatch(BaseModel):
    detected_segments: list[dict[str, Any]] | None = None
    reviewer_notes: str | None = None
    status: str | None = Field(default=None, pattern="^(awaiting_review|approved)$")


class PublishRequest(BaseModel):
    slug: str
    title_en: str | None = None
    artist_ar: str | None = None
    era: str
    price_sar: float = 49
    voice_model_id: str
    voice_engine: str = "elevenlabs"
    cover_image_url: str | None = None
    rights_status: str = "licensed"


@router.post("/intake")
def create_intake(req: IntakeCreate, _: CurrentAdmin) -> dict:
    row = (
        service()
        .table("catalog_intake")
        .insert({"source_audio_url": req.source_audio_url, "title_ar": req.title_ar})
        .execute()
    ).data[0]
    # Kick off Demucs + Whisper alignment in the background.
    from app.workers.tasks import run_intake_analysis

    run_intake_analysis.delay(row["id"])
    return row


@router.patch("/intake/{intake_id}")
def patch_intake(
    intake_id: UUID, req: IntakePatch, _: CurrentAdmin
) -> dict:
    update: dict[str, Any] = {}
    if req.detected_segments is not None:
        update["detected_segments"] = req.detected_segments
    if req.reviewer_notes is not None:
        update["reviewer_notes"] = req.reviewer_notes
    if req.status is not None:
        update["status"] = req.status
    if not update:
        raise HTTPException(400, "No fields to update.")
    row = (
        service()
        .table("catalog_intake")
        .update(update)
        .eq("id", str(intake_id))
        .execute()
    ).data
    if not row:
        raise HTTPException(404, "Intake not found.")
    return row[0]


@router.post("/intake/{intake_id}/train-voice")
async def train_voice(
    intake_id: UUID,
    _: CurrentAdmin,
    name: str = Form(...),
    description: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
) -> dict:
    """Upload 1+ vocal sample WAVs and create a cloned voice.

    Returns {voice_id, voice_engine}. The caller should store these on
    the published song row (or pass to /publish).
    """
    intake = (
        service()
        .table("catalog_intake")
        .select("id")
        .eq("id", str(intake_id))
        .single()
        .execute()
    ).data
    if not intake:
        raise HTTPException(404, "Intake not found.")
    if not files:
        raise HTTPException(400, "At least one sample file is required.")

    provider = get_tts_provider()
    if not provider.supports_cloning:
        raise HTTPException(
            501, f"Provider {provider.name!r} does not support cloning."
        )

    tmpdir = Path(tempfile.mkdtemp(prefix="farq_clone_"))
    sample_paths: list[Path] = []
    try:
        for idx, upload in enumerate(files):
            suffix = Path(upload.filename or f"sample_{idx}.wav").suffix or ".wav"
            dest = tmpdir / f"sample_{idx}{suffix}"
            content = await upload.read()
            if not content:
                raise HTTPException(400, f"Empty file: {upload.filename!r}")
            dest.write_bytes(content)
            sample_paths.append(dest)

        result = provider.clone_voice(
            VoiceCloneRequest(
                name=name,
                sample_paths=sample_paths,
                description=description,
            )
        )
    finally:
        for p in sample_paths:
            p.unlink(missing_ok=True)
        try:
            tmpdir.rmdir()
        except OSError:
            pass

    # Persist on the intake row so reviewers can re-use it on publish.
    service().table("catalog_intake").update(
        {"voice_model_id": result.voice_id, "voice_engine": provider.name}
    ).eq("id", str(intake_id)).execute()

    return {
        "voice_id": result.voice_id,
        "voice_engine": provider.name,
        "name": result.name,
    }


@router.post("/intake/{intake_id}/publish")
def publish_intake(
    intake_id: UUID, req: PublishRequest, _: CurrentAdmin
) -> dict:
    intake = (
        service()
        .table("catalog_intake")
        .select("*")
        .eq("id", str(intake_id))
        .single()
        .execute()
    ).data
    if not intake:
        raise HTTPException(404, "Intake not found.")
    if intake["status"] != "approved":
        raise HTTPException(409, "Intake must be approved before publish.")
    if not intake.get("detected_segments"):
        raise HTTPException(409, "Intake has no segments.")

    song_row = (
        service()
        .table("songs")
        .insert({
            "slug": req.slug,
            "title_ar": intake["title_ar"],
            "title_en": req.title_en,
            "artist_ar": req.artist_ar,
            "era": req.era,
            "price_sar": req.price_sar,
            "preview_url": intake["source_audio_url"],
            "full_original_url": intake["source_audio_url"],
            "instrumental_url": intake.get("source_audio_url"),
            "isolated_vocals_url": intake.get("source_audio_url"),
            "voice_model_id": req.voice_model_id,
            "voice_engine": req.voice_engine,
            "cover_image_url": req.cover_image_url,
            "rights_status": req.rights_status,
            "is_active": True,
        })
        .execute()
    ).data[0]

    # Persist segments.
    segs = []
    for seg in intake["detected_segments"]:
        segs.append({
            "song_id": song_row["id"],
            "role": seg["role"],
            "sequence_index": seg["sequence_index"],
            "start_ms": seg["start_ms"],
            "end_ms": seg["end_ms"],
            "original_text_ar": seg.get("original_text_ar", ""),
            "phonetic_hint": seg.get("phonetic_hint"),
            "prosody_note": seg.get("prosody_note"),
        })
    if segs:
        service().table("song_segments").insert(segs).execute()

    service().table("catalog_intake").update(
        {"status": "published"}
    ).eq("id", str(intake_id)).execute()

    return {"published_song_id": song_row["id"]}
