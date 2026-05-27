"""FastAPI entrypoint."""
from __future__ import annotations

import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.routers import admin, orders, share, songs, webhooks
from app.utils.ratelimit import limiter

settings = get_settings()

logging.basicConfig(level=settings.log_level.upper())

# Sentry — only initializes if SENTRY_DSN_API is set.
if settings.sentry_dsn_api:
    sentry_sdk.init(
        dsn=settings.sentry_dsn_api,
        environment=settings.app_env,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )

app = FastAPI(
    title="Farq Sound API",
    version="0.1.0",
    description="AI-personalized Arabic wedding songs.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "env": settings.app_env,
        "providers": {
            "tts": settings.tts_mode,
            "payments": settings.payments_mode,
            "whatsapp": settings.whatsapp_mode,
            "email": settings.email_mode,
        },
    }


if settings.app_env == "development":
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/storage",
        StaticFiles(directory=str(settings.storage_root)),
        name="storage",
    )

app.include_router(songs.router, prefix="/api/songs", tags=["songs"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(share.router, prefix="/api/share", tags=["share"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
