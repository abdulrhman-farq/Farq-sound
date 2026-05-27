"""FastAPI entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import admin, orders, share, songs, webhooks

settings = get_settings()

logging.basicConfig(level=settings.log_level.upper())

app = FastAPI(
    title="Farq Sound API",
    version="0.1.0",
    description="AI-personalized Arabic wedding songs (زفّات).",
)

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


# In development, serve the local `storage/` directory directly so the
# preview-name endpoint URLs resolve without going through Supabase.
# In production, all audio is served via signed Supabase Storage URLs.
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
