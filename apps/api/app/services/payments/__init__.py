"""Payment provider abstraction.

`get_payment_provider()` returns Moyasar live when an API key is
present, otherwise a deterministic mock that auto-approves checkouts.
"""
from __future__ import annotations

from app.config import get_settings

from .base import (
    CheckoutRequest,
    CheckoutSession,
    PaymentEvent,
    PaymentProvider,
)
from .mock import MockPaymentProvider
from .moyasar import MoyasarProvider


def get_payment_provider() -> PaymentProvider:
    settings = get_settings()
    if settings.payments_mode == "live":
        return MoyasarProvider(
            api_key=settings.moyasar_api_key,
            publishable_key=settings.moyasar_publishable_key,
            webhook_secret=settings.moyasar_webhook_secret,
        )
    return MockPaymentProvider()


__all__ = [
    "CheckoutRequest",
    "CheckoutSession",
    "PaymentEvent",
    "PaymentProvider",
    "get_payment_provider",
]
