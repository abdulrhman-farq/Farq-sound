"""Payment provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class CheckoutRequest:
    order_id: str
    amount_sar: float
    description_ar: str
    callback_url: str
    customer_email: str | None = None
    customer_phone: str | None = None


@dataclass
class CheckoutSession:
    payment_id: str
    payment_url: str
    mode: Literal["live", "mock"]


@dataclass
class PaymentEvent:
    payment_id: str
    order_id: str
    status: Literal["paid", "failed"]
    amount_sar: float | None = None


class PaymentProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        """Begin a payment session; return URL to redirect the user to."""

    @abstractmethod
    def verify_webhook(self, signature: str | None, body: bytes) -> bool:
        """Validate webhook signature."""

    @abstractmethod
    def parse_webhook(self, body: bytes) -> PaymentEvent:
        """Extract a normalized event from a webhook body."""
