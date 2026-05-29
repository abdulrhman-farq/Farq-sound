"""Admin endpoints — catalog onboarding.

The full Demucs + faster-whisper intake worker is invoked here as a
Celery task. The reviewer UI then PATCHes detected segment boundaries
before publish.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

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


# ---------------------------------------------------------------------
# Voice cloning — upload singer samples, get back a voice_id.
# ---------------------------------------------------------------------
MAX_SAMPLE_BYTES = 25 * 1024 * 1024          # 25 MB per file
MAX_TOTAL_SAMPLES = 4
ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/flac", "audio/ogg", "audio/x-m4a",
}


@router.post("/voices")
def clone_voice(
    _: CurrentAdmin,
    name: str = Form(..., min_length=2, max_length=80),
    description: str | None = Form(default=None, max_length=400),
    files: list[UploadFile] = File(...),
) -> dict:
    """Train a singer voice from uploaded vocal samples.

    Returns `{ voice_id, provider, mode }`. Use the returned `voice_id`
    as `songs.voice_model_id` when publishing the song.

    The handler validates content type and size, then hands off to the
    configured TTS provider (ElevenLabs Instant Voice Clone in live
    mode, deterministic stub in mock mode).
    """
    if not files:
        raise HTTPException(400, "At least one sample is required.")
    if len(files) > MAX_TOTAL_SAMPLES:
        raise HTTPException(
            400, f"At most {MAX_TOTAL_SAMPLES} samples per request."
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix="voicelab-"))
    saved: list[Path] = []
    try:
        for upload in files:
            if upload.content_type not in ALLOWED_AUDIO_TYPES:
                raise HTTPException(
                    400, f"Unsupported file type: {upload.content_type}"
                )
            dest = tmp_dir / (upload.filename or "sample.wav")
            size = 0
            with open(dest, "wb") as fh:
                while chunk := upload.file.read(1 << 20):
                    size += len(chunk)
                    if size > MAX_SAMPLE_BYTES:
                        raise HTTPException(
                            413, "Sample exceeds 25 MB limit."
                        )
                    fh.write(chunk)
            saved.append(dest)

        provider = get_tts_provider()
        result = provider.clone_voice(
            VoiceCloneRequest(
                name=name,
                description=description,
                sample_paths=saved,
            )
        )
        return {
            "voice_id": result.voice_id,
            "provider": result.provider,
            "mode": "mock" if result.provider == "mock" else "live",
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------
# One-shot song intake from a URL. Triggers prepare_song_from_url on
# the worker (Demucs + upsert). Currently un-gated so we can onboard
# the first real song before a full admin auth flow exists; lock down
# before any wider exposure (TODO: require CurrentAdmin).
# ---------------------------------------------------------------------
class SongIntakeSegment(BaseModel):
    role: str = "primary_name"
    start_ms: int
    end_ms: int
    original_text_ar: str = ""
    prosody_note: str = "sung"


class SongIntakeRequest(BaseModel):
    slug: str
    title_ar: str
    artist_ar: str = ""
    era: str = "classic"
    source_url: str
    voice_model_id: str
    segment: SongIntakeSegment
    rights_status: str = "licensed"
    price_sar: float = 49


@router.post("/songs/intake-from-url")
def intake_song_from_url(req: SongIntakeRequest) -> dict:
    if req.segment.end_ms <= req.segment.start_ms:
        raise HTTPException(400, "segment end_ms must be > start_ms")
    if req.segment.start_ms <= 0 or req.segment.end_ms <= 0:
        raise HTTPException(400, "segment timings must be > 0")

    from app.workers.tasks import prepare_song_from_url

    task = prepare_song_from_url.delay(
        slug=req.slug,
        title_ar=req.title_ar,
        artist_ar=req.artist_ar,
        era=req.era,
        source_url=req.source_url,
        voice_model_id=req.voice_model_id,
        segment=req.segment.model_dump(),
        rights_status=req.rights_status,
        price_sar=req.price_sar,
    )
    return {"task_id": task.id, "slug": req.slug, "status": "queued"}
