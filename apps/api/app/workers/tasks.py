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
                add_preview_watermark(mp3, wm, mp3)

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
