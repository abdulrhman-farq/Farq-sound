"""Mock Moyasar — auto-approves and returns a local /mock-checkout URL."""
from __future__ import annotations

import uuid

from app.config import get_settings

from .base import (
    CheckoutRequest,
    CheckoutSession,
    PaymentEvent,
    PaymentProvider,
)


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        payment_id = f"mock_{uuid.uuid4().hex[:12]}"
        # Frontend mock-checkout page POSTs to /api/webhooks/moyasar with
        # `{ "id": <payment_id>, "status": "paid", "metadata": { "order_id" }}`
        # to simulate an approved payment.
        s = get_settings()
        url = (
            f"{s.app_base_url}/mock-checkout"
            f"?order_id={request.order_id}&payment_id={payment_id}"
        )
        return CheckoutSession(
            payment_id=payment_id,
            payment_url=url,
            mode="mock",
        )

    def verify_webhook(self, signature: str | None, body: bytes) -> bool:
        # Trust everything in mock mode; clearly NOT for production.
        return True

    def parse_webhook(self, body: bytes) -> PaymentEvent:
        import json

        data = json.loads(body or b"{}")
        return PaymentEvent(
            payment_id=data.get("id", ""),
            order_id=(data.get("metadata") or {}).get("order_id", ""),
            status=data.get("status", "paid"),
            amount_sar=data.get("amount_sar"),
        )
