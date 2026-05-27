"""Moyasar payment provider (live).

API docs: https://docs.moyasar.com/

We use the Invoices API rather than the Payments API directly because
the hosted Invoice URL handles mada / Apple Pay / STC Pay UX out of
the box and posts back to our webhook on completion.
"""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import (
    CheckoutRequest,
    CheckoutSession,
    PaymentEvent,
    PaymentProvider,
)


class MoyasarProvider(PaymentProvider):
    name = "moyasar"
    base_url = "https://api.moyasar.com/v1"

    def __init__(
        self,
        api_key: str,
        publishable_key: str,
        webhook_secret: str,
    ) -> None:
        self.api_key = api_key
        self.publishable_key = publishable_key
        self.webhook_secret = webhook_secret

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        # Moyasar amounts are in halalas (1 SAR = 100 halalas).
        amount_halalas = int(round(request.amount_sar * 100))
        payload = {
            "amount": amount_halalas,
            "currency": "SAR",
            "description": request.description_ar,
            "callback_url": request.callback_url,
            "metadata": {"order_id": request.order_id},
        }
        with httpx.Client(timeout=30) as client:
            r = client.post(
                f"{self.base_url}/invoices",
                json=payload,
                auth=(self.api_key, ""),
            )
            r.raise_for_status()
            data = r.json()
        return CheckoutSession(
            payment_id=data["id"],
            payment_url=data["url"],
            mode="live",
        )

    def verify_webhook(self, signature: str | None, body: bytes) -> bool:
        if not self.webhook_secret or not signature:
            return False
        digest = hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(digest, signature)

    def parse_webhook(self, body: bytes) -> PaymentEvent:
        data = json.loads(body)
        payment = data.get("data", data)
        meta = payment.get("metadata", {}) or {}
        status = (
            "paid"
            if payment.get("status") in ("paid", "authorized")
            else "failed"
        )
        amount = payment.get("amount")
        return PaymentEvent(
            payment_id=payment["id"],
            order_id=meta.get("order_id", ""),
            status=status,
            amount_sar=(amount / 100.0) if amount is not None else None,
        )
