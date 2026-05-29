"""Celery tasks — the render chain + admin intake worker.

The render chain is staged:
  Stage 1 — tts          generate name audio per segment
  Stage 2 — pitch_match  match pitch + duration to original segments
  Stage 3 — splice       splice into isolated vocals with crossfade
  Stage 4 — mixdown      combine modified vocals with instrumental
  Stage 5 — master       master to MP3, watermark for preview, deliver
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.config import get_settings
from app.db import service
from app.services.pipeline import (
    add_preview_watermark,
    master_to_mp3,
    mixdown,
    pitch_and_time_match,
    slice_reference,
    splice_into_vocals,
)
from app.services.storage import upload_audio
from app.services.tts import TTSRequest, get_tts_provider
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _start_job(order_id: str, stage: str) -> str:
    row = (
        service().table("render_jobs").insert({
            "order_id": order_id,
            "stage": stage,
            "status": "running",
            "started_at": _now(),
        }).execute()
    ).data[0]
    return row["id"]


def _finish_job(job_id: str, *, status: str, log_msg: str = "") -> None:
    service().table("render_jobs").update({
        "status": status,
        "completed_at": _now(),
        "log": log_msg[:8000],
    }).eq("id", job_id).execute()


def _fail_order(order_id: str, error: str) -> None:
    service().table("orders").update({
        "status": "failed",
        "error_message": error[:500],
    }).eq("id", order_id).execute()


def _load_order(order_id: str) -> dict:
    row = (
        service().table("orders").select("*")
        .eq("id", order_id).single().execute()
    ).data
    if not row:
        raise RuntimeError(f"Order {order_id} not found.")
    return row


def _load_song_with_segments(song_id: str) -> tuple[dict, list[dict]]:
    song = (
        service().table("songs").select("*")
        .eq("id", song_id).single().execute()
    ).data
    segments = (
        service().table("song_segments").select("*")
        .eq("song_id", song_id).order("sequence_index").execute()
    ).data or []
    return song, segments


@celery_app.task(bind=True, max_retries=2)
def run_render_chain(
    self, order_id: str, mode: Literal["preview", "final"] = "preview"
) -> dict:
    """Drive the full render pipeline for one order."""
    settings = get_settings()
    work = settings.storage_root / "orders" / order_id
    work.mkdir(parents=True, exist_ok=True)

    try:
        order = _load_order(order_id)
        song, segments = _load_song_with_segments(order["song_id"])
        names = order["names"] or {}

        # --- Stage 1: TTS ---
        job_id = _start_job(order_id, "tts")
        try:
            tts = get_tts_provider()
            tts_out_paths: list[Path] = []
            for seg in segments:
                name = names.get(seg["role"])
                if not name:
                    raise RuntimeError(
                        f"Missing name for role {seg['role']}."
                    )
                target_ms = seg["end_ms"] - seg["start_ms"]
                tts_path = work / f"tts-{seg['sequence_index']}.wav"
                tts.synthesize(
                    TTSRequest(
                        voice_model_id=song["voice_model_id"] or "mock",
                        text_ar=name,
                        target_duration_ms=target_ms,
                        phonetic_hint=seg.get("phonetic_hint"),
                        prosody_note=seg.get("prosody_note"),
                    ),
                    out_path=tts_path,
                )
                tts_out_paths.append(tts_path)
            _finish_job(job_id, status="done", log_msg=f"{len(segments)} segments")
        except Exception as exc:
            _finish_job(job_id, status="failed", log_msg=str(exc))
            raise

        # --- Stage 2: pitch & time match ---
        job_id = _start_job(order_id, "pitch_match")
        matched_paths: list[Path] = []
        try:
            vocals_src = Path(song["isolated_vocals_url"])
            for seg, tts_path in zip(segments, tts_out_paths, strict=True):
                target_ms = seg["end_ms"] - seg["start_ms"]
                # Slice the original-singer segment as the pitch & timing
                # reference so the generated voice matches the source.
                ref = work / f"ref-{seg['sequence_index']}.wav"
                slice_reference(
                    source_path=vocals_src,
                    start_ms=seg["start_ms"],
                    end_ms=seg["end_ms"],
                    out_path=ref,
                )
                out = work / f"matched-{seg['sequence_index']}.wav"
                pitch_and_time_match(
                    generated_path=tts_path,
                    reference_path=ref,
                    target_duration_ms=target_ms,
                    out_path=out,
                )
                matched_paths.append(out)
            _finish_job(job_id, status="done")
        except Exception as exc:
            _finish_job(job_id, status="failed", log_msg=str(exc))
            raise

        # --- Stage 3: splice into isolated vocals ---
        job_id = _start_job(order_id, "splice")
        try:
            replacements = [
                (seg["start_ms"], seg["end_ms"], path)
                for seg, path in zip(segments, matched_paths, strict=True)
            ]
            spliced = work / "spliced-vocals.wav"
            splice_into_vocals(
                isolated_vocals_path=Path(song["isolated_vocals_url"]),
                replacements=replacements,
                out_path=spliced,
            )
            _finish_job(job_id, status="done")
        except Exception as exc:
            _finish_job(job_id, status="failed", log_msg=str(exc))
            raise

        # --- Stage 4: mixdown ---
        job_id = _start_job(order_id, "mixdown")
        try:
            mixed = work / "mix.wav"
            mixdown(
                vocals_path=spliced,
                instrumental_path=Path(song["instrumental_url"]),
                out_path=mixed,
            )
            _finish_job(job_id, status="done")
        except Exception as exc:
            _finish_job(job_id, status="failed", log_msg=str(exc))
            raise

        # --- Stage 5: master + deliver ---
        job_id = _start_job(order_id, "master")
        try:
            couple_label = " و ".join(
                v for v in (names.get("groom"), names.get("bride")) if v
            )
            title = f"{song['title_ar']} — {couple_label}".strip(" —")
            artist = song.get("artist_ar") or "Farq Sound"

            mp3 = work / ("preview.mp3" if mode == "preview" else "final.mp3")
            master_to_mp3(
                wav_path=mixed,
                out_path=mp3,
                bitrate="192k" if mode == "preview" else "320k",
                title=title,
                artist=artist,
            )
            if mode == "preview":
                wm = Path(__file__).resolve().parents[2] / "assets" / "watermark.wav"
                stamped = work / "preview-stamped.mp3"
                add_preview_watermark(mp3, wm, stamped)
                mp3 = stamped  # serve the watermarked version

            # Upload + sign.
            key = f"orders/{order_id}/{mp3.name}"
            url = upload_audio(mp3, key, content_type="audio/mpeg")

            update: dict = {}
            if mode == "preview":
                update = {"status": "preview_ready", "preview_url": url}
            else:
                update = {"status": "delivered", "final_url": url}
            service().table("orders").update(update).eq("id", order_id).execute()
            _finish_job(job_id, status="done", log_msg=url)
        except Exception as exc:
            _finish_job(job_id, status="failed", log_msg=str(exc))
            raise

        # Delivery notifications.
        if mode == "final":
            try:
                _send_delivery(order_id)
            except Exception as exc:  # delivery errors don't block fulfillment
                log.warning("delivery notify failed: %s", exc)

        return {"order_id": order_id, "mode": mode, "status": "ok"}

    except Exception as exc:
        log.exception("render chain failed for %s", order_id)
        _fail_order(order_id, str(exc))
        if self.request.retries < (self.max_retries or 0):
            raise self.retry(exc=exc, countdown=10) from exc
        return {"order_id": order_id, "mode": mode, "status": "failed"}


def _send_delivery(order_id: str) -> None:
    from app.config import get_settings
    from app.services.notify import send_email_delivery, send_whatsapp_delivery

    s = get_settings()
    order = _load_order(order_id)
    profile = (
        service().table("profiles").select("phone, full_name_ar")
        .eq("id", order["user_id"]).single().execute()
    ).data or {}

    names = order["names"] or {}
    couple = " و ".join(v for v in (names.get("groom"), names.get("bride")) if v)
    download_url = order.get("final_url") or ""
    share_url = f"{s.app_base_url}/share/{order.get('share_token', '')}"

    if profile.get("phone"):
        send_whatsapp_delivery(profile["phone"], couple, download_url, share_url)
        service().table("orders").update(
            {"whatsapp_sent_at": _now()}
        ).eq("id", order_id).execute()
    # Email fallback (uses auth.users email — fetched via service role)
    user_row = (
        service().auth.admin.get_user_by_id(order["user_id"]).user
    )
    if user_row and user_row.email:
        send_email_delivery(user_row.email, couple, download_url, share_url)


# ---------------------------------------------------------------------
# Admin intake — Demucs + faster-whisper alignment
# ---------------------------------------------------------------------
@celery_app.task
def run_intake_analysis(intake_id: str) -> dict:
    """One-time onboarding analysis for a candidate song.

    Runs Demucs to split vocals/instrumental, then faster-whisper to
    produce word-level timestamps, then a heuristic name detector that
    proposes segments for human review. The heavy ML imports are lazy
    so workers that never run intake jobs avoid the cost.
    """
    log.info("running intake analysis for %s", intake_id)

    # Lazy imports — heavy.
    try:
        from faster_whisper import WhisperModel  # noqa: F401
    except ImportError:
        log.warning("faster-whisper not installed; skipping intake analysis")
        return {"intake_id": intake_id, "status": "skipped"}

    # The actual implementation lives in services/intake.py once we wire
    # in the real Demucs + Whisper pipeline. For now we mark awaiting_review
    # so the admin UI can still drive the workflow with manual segments.
    service().table("catalog_intake").update({
        "status": "awaiting_review",
        "detected_segments": [],
    }).eq("id", intake_id).execute()
    return {"intake_id": intake_id, "status": "awaiting_review"}


# ---------------------------------------------------------------------
# One-shot song intake: download source MP3 -> demucs -> upload stems
# -> upsert songs row + one manual segment. Triggered by the admin
# endpoint POST /api/admin/songs/intake-from-url so we can onboard
# `يامرحبا ياكل حاضر` without leaving the production stack.
# ---------------------------------------------------------------------
@celery_app.task(bind=True)
def prepare_song_from_url(
    self,
    *,
    slug: str,
    title_ar: str,
    artist_ar: str,
    era: str,
    source_url: str,
    voice_model_id: str,
    segment: dict,
    rights_status: str = "licensed",
    price_sar: float = 49,
) -> dict:
    """Download, separate, upload, seed. Returns {song_id, ...}."""
    import httpx

    from app.services.separation import separate
    from app.services.storage import upload_audio

    s = get_settings()
    work = s.storage_root / "intake" / slug
    work.mkdir(parents=True, exist_ok=True)
    src = work / "original.mp3"

    log.info("[intake:%s] downloading %s", slug, source_url[:60])
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        with client.stream("GET", source_url) as r:
            r.raise_for_status()
            with open(src, "wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
    log.info("[intake:%s] downloaded %.1f MB", slug, src.stat().st_size / 1e6)

    vocals, instr = separate(src, work)
    log.info("[intake:%s] demucs done", slug)

    # Upload stems to Supabase Storage as private signed URLs.
    base = f"songs/{slug}"
    vocals_url = upload_audio(vocals, f"{base}/vocals.wav", "audio/wav")
    instr_url  = upload_audio(instr,  f"{base}/instrumental.wav", "audio/wav")
    src_url    = upload_audio(src,    f"{base}/original.mp3", "audio/mpeg")

    # Also place the stems at the on-disk paths the renderer expects
    # via the same path scheme used for demo songs, so the existing
    # pipeline can read them without a download step at render time.
    baked_dir = Path("/app/storage/songs") / slug
    baked_dir.mkdir(parents=True, exist_ok=True)
    import shutil as _sh
    _sh.copy(vocals, baked_dir / "vocals.wav")
    _sh.copy(instr,  baked_dir / "instrumental.wav")

    instrumental_path     = str(baked_dir / "instrumental.wav")
    isolated_vocals_path  = str(baked_dir / "vocals.wav")

    # Upsert the song row.
    row = (
        service().table("songs").upsert({
            "slug": slug,
            "title_ar": title_ar,
            "artist_ar": artist_ar,
            "era": era,
            "preview_url": src_url,           # served to users for browsing
            "full_original_url": src_url,
            "instrumental_url": instrumental_path,
            "isolated_vocals_url": isolated_vocals_path,
            "voice_model_id": voice_model_id,
            "voice_engine": "elevenlabs",
            "rights_status": rights_status,
            "is_active": True,
            "price_sar": price_sar,
        }, on_conflict="slug").execute()
    ).data[0]

    # Clear any old segments, then write the single manual segment.
    service().table("song_segments").delete().eq(
        "song_id", row["id"]
    ).execute()
    service().table("song_segments").insert({
        "song_id": row["id"],
        "role": segment["role"],
        "sequence_index": 1,
        "start_ms": int(segment["start_ms"]),
        "end_ms": int(segment["end_ms"]),
        "original_text_ar": segment.get("original_text_ar", ""),
        "prosody_note": segment.get("prosody_note", "sung"),
    }).execute()

    return {
        "song_id": row["id"],
        "slug": slug,
        "vocals_url": vocals_url,
        "instrumental_url": instr_url,
        "baked_at": str(baked_dir),
    }
