"""Delivery notifications — WhatsApp Cloud API + Resend email fallback.

Both fall back to no-op mock mode when credentials are absent.
"""
from __future__ import annotations

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

log = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=False,
)
def send_whatsapp_delivery(
    phone_e164: str,
    couple_label: str,
    download_url: str,
    share_url: str,
) -> bool:
    s = get_settings()
    if s.whatsapp_mode == "mock":
        log.info(
            "[whatsapp:mock] would notify %s — couple=%s url=%s",
            phone_e164,
            couple_label,
            download_url,
        )
        return True

    url = (
        f"https://graph.facebook.com/v20.0/"
        f"{s.whatsapp_phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_e164.lstrip("+"),
        "type": "template",
        "template": {
            "name": s.whatsapp_template_delivery,
            "language": {"code": "ar"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": couple_label},
                    ],
                },
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {"type": "text", "text": download_url},
                    ],
                },
            ],
        },
    }
    headers = {
        "Authorization": f"Bearer {s.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
    return True


@retry(
    retry=retry_if_exception_type(httpx.HTTPError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=False,
)
def send_email_delivery(
    to_email: str,
    couple_label: str,
    download_url: str,
    share_url: str,
) -> bool:
    s = get_settings()
    if s.email_mode == "mock":
        log.info(
            "[email:mock] would send to %s — couple=%s url=%s",
            to_email,
            couple_label,
            download_url,
        )
        return True

    payload = {
        "from": s.resend_from,
        "to": [to_email],
        "subject": f"زفّتكم جاهزة — {couple_label}",
        "html": (
            f"<div dir=\"rtl\" style=\"font-family:Tajawal,system-ui;\">"
            f"<h1>مبروك {couple_label}!</h1>"
            f"<p>زفّتكم الخاصة جاهزة. تقدرين تنزّلينها من الرابط:</p>"
            f"<p><a href=\"{download_url}\">تحميل الزفّة</a></p>"
            f"<p>وللمشاركة مع الأهل والأصحاب:</p>"
            f"<p><a href=\"{share_url}\">رابط المشاركة</a></p>"
            f"<p style=\"margin-top:32px;color:#888\">— فرق ساوند</p>"
            f"</div>"
        ),
    }
    headers = {
        "Authorization": f"Bearer {s.resend_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15) as client:
        r = client.post(
            "https://api.resend.com/emails",
            json=payload,
            headers=headers,
        )
        r.raise_for_status()
    return True
