"""Inbound webhooks — currently just Moyasar payments."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from app.db import service
from app.services.payments import get_payment_provider

router = APIRouter()


@router.post("/moyasar")
async def moyasar_webhook(
    request: Request,
    x_moyasar_signature: str | None = Header(default=None),
) -> dict:
    provider = get_payment_provider()
    body = await request.body()
    if not provider.verify_webhook(x_moyasar_signature, body):
        raise HTTPException(401, "Invalid webhook signature.")

    event = provider.parse_webhook(body)
    if not event.order_id:
        raise HTTPException(400, "Webhook missing order_id metadata.")

    order = (
        service()
        .table("orders")
        .select("id, status")
        .eq("id", event.order_id)
        .single()
        .execute()
    ).data
    if not order:
        raise HTTPException(404, "Order not found.")

    if event.status == "paid":
        service().table("orders").update(
            {"status": "paid", "moyasar_payment_id": event.payment_id}
        ).eq("id", event.order_id).execute()

        # Trigger the final clean render.
        from app.workers.tasks import run_render_chain

        run_render_chain.delay(event.order_id, mode="final")
    else:
        service().table("orders").update(
            {"status": "failed", "error_message": "payment_failed"}
        ).eq("id", event.order_id).execute()

    return {"received": True}
