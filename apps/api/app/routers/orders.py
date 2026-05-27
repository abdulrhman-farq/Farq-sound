"""Order lifecycle endpoints."""
from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.auth import CurrentUser
from app.db import service
from app.schemas import (
    CheckoutResponse,
    CreateOrderRequest,
    NamesPayload,
    OrderRead,
    OrderWithJobs,
    RenderJobRead,
    SampleNamePreviewRequest,
    SampleNamePreviewResponse,
)
from app.services.payments import CheckoutRequest, get_payment_provider

router = APIRouter()


def _share_token() -> str:
    return secrets.token_urlsafe(10)


@router.post("", response_model=OrderRead)
def create_order(req: CreateOrderRequest, user: CurrentUser) -> OrderRead:
    # Validate song exists.
    song = (
        service()
        .table("songs")
        .select("id, price_sar")
        .eq("id", str(req.song_id))
        .eq("is_active", True)
        .single()
        .execute()
    ).data
    if not song:
        raise HTTPException(404, "Song not found.")

    insert = {
        "user_id": user.id,
        "song_id": str(req.song_id),
        "names": req.names.model_dump(exclude_none=True),
        "amount_sar": song["price_sar"],
        "share_token": _share_token(),
    }
    row = (
        service().table("orders").insert(insert).execute()
    ).data[0]
    return OrderRead.model_validate(row)


class UpdateNamesRequest(__import__("pydantic").BaseModel):
    names: NamesPayload


@router.patch("/{order_id}/names", response_model=OrderRead)
def update_names(
    order_id: UUID, req: UpdateNamesRequest, user: CurrentUser
) -> OrderRead:
    row = (
        service()
        .table("orders")
        .select("id, status")
        .eq("id", str(order_id))
        .eq("user_id", user.id)
        .single()
        .execute()
    ).data
    if not row:
        raise HTTPException(404, "Order not found.")
    if row["status"] not in ("draft", "preview_ready", "failed"):
        raise HTTPException(409, "Cannot edit names after payment.")
    updated = (
        service()
        .table("orders")
        .update({"names": req.names.model_dump(exclude_none=True)})
        .eq("id", str(order_id))
        .execute()
    ).data[0]
    return OrderRead.model_validate(updated)


@router.get("/{order_id}", response_model=OrderWithJobs)
def get_order(order_id: UUID, user: CurrentUser) -> OrderWithJobs:
    row = (
        service()
        .table("orders")
        .select("*")
        .eq("id", str(order_id))
        .eq("user_id", user.id)
        .single()
        .execute()
    ).data
    if not row:
        raise HTTPException(404, "Order not found.")

    jobs_rows = (
        service()
        .table("render_jobs")
        .select("*")
        .eq("order_id", str(order_id))
        .order("started_at", desc=False)
        .execute()
    ).data or []
    jobs = [RenderJobRead.model_validate(j) for j in jobs_rows]
    return OrderWithJobs(**row, jobs=jobs)


@router.post("/{order_id}/render-preview", response_model=OrderRead)
def render_preview(
    order_id: UUID,
    user: CurrentUser,
    background: BackgroundTasks,
) -> OrderRead:
    row = (
        service()
        .table("orders")
        .select("*")
        .eq("id", str(order_id))
        .eq("user_id", user.id)
        .single()
        .execute()
    ).data
    if not row:
        raise HTTPException(404, "Order not found.")
    if row["status"] not in ("draft", "preview_ready", "failed"):
        raise HTTPException(
            409, f"Cannot re-render from status: {row['status']}"
        )

    updated = (
        service()
        .table("orders")
        .update({"status": "rendering", "error_message": None})
        .eq("id", str(order_id))
        .execute()
    ).data[0]

    # Enqueue the Celery chain.
    from app.workers.tasks import run_render_chain

    run_render_chain.delay(str(order_id), mode="preview")
    return OrderRead.model_validate(updated)


@router.post("/{order_id}/checkout", response_model=CheckoutResponse)
def checkout(order_id: UUID, user: CurrentUser) -> CheckoutResponse:
    row = (
        service()
        .table("orders")
        .select("id, user_id, status, amount_sar")
        .eq("id", str(order_id))
        .eq("user_id", user.id)
        .single()
        .execute()
    ).data
    if not row:
        raise HTTPException(404, "Order not found.")
    if row["status"] != "preview_ready":
        raise HTTPException(409, "Order is not ready for checkout.")

    profile = (
        service()
        .table("profiles")
        .select("phone")
        .eq("id", user.id)
        .single()
        .execute()
    ).data or {}

    provider = get_payment_provider()
    from app.config import get_settings

    s = get_settings()
    session = provider.create_checkout(
        CheckoutRequest(
            order_id=str(order_id),
            amount_sar=float(row["amount_sar"] or 0),
            description_ar="زفّتكم الخاصة من فرق ساوند",
            callback_url=f"{s.app_base_url}/orders/{order_id}",
            customer_email=user.email,
            customer_phone=profile.get("phone"),
        )
    )
    service().table("orders").update(
        {"moyasar_payment_id": session.payment_id}
    ).eq("id", str(order_id)).execute()
    return CheckoutResponse(
        payment_url=session.payment_url,
        payment_id=session.payment_id,
        mode=session.mode,
    )


@router.post("/preview-name", response_model=SampleNamePreviewResponse)
def preview_name(
    req: SampleNamePreviewRequest, user: CurrentUser
) -> SampleNamePreviewResponse:
    """Cheap single-name TTS preview for the customize wizard."""
    from pathlib import Path

    from app.config import get_settings
    from app.services.tts import TTSRequest, get_tts_provider

    if len(req.name_ar.strip()) < 2 or len(req.name_ar) > 40:
        raise HTTPException(400, "Name length must be 2-40 chars.")

    song = (
        service()
        .table("songs")
        .select("voice_model_id")
        .eq("id", str(req.song_id))
        .single()
        .execute()
    ).data
    if not song:
        raise HTTPException(404, "Song not found.")

    s = get_settings()
    out_dir = s.storage_root / "previews-name" / user.id
    out_path = out_dir / f"{req.role}-{secrets.token_hex(4)}.wav"
    provider = get_tts_provider()
    result = provider.synthesize(
        TTSRequest(
            voice_model_id=song["voice_model_id"] or "mock",
            text_ar=req.name_ar,
            target_duration_ms=1500,
        ),
        out_path=out_path,
    )
    # For dev, serve via API static route. For prod, upload to Supabase
    # Storage and return a signed URL — see services/storage.py.
    rel = out_path.relative_to(s.storage_root).as_posix()
    return SampleNamePreviewResponse(
        audio_url=f"{s.api_base_url}/storage/{rel}",
        duration_ms=result.duration_ms,
    )
