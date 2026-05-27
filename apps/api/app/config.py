"""Centralized settings — Pydantic v2 reads from environment + .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- app -----
    app_name: str = "farq-sound"
    app_env: Literal["development", "staging", "production"] = "development"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    log_level: str = "info"

    # ----- supabase -----
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_storage_bucket: str = "farq-sound"

    database_url: str = ""

    # ----- celery / redis -----
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ----- providers -----
    elevenlabs_api_key: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    moyasar_api_key: str = ""
    moyasar_publishable_key: str = ""
    moyasar_webhook_secret: str = ""

    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_template_delivery: str = "farq_sound_delivery"

    resend_api_key: str = ""
    resend_from: str = "Farq Sound <hello@farqsound.sa>"

    # ----- runtime -----
    storage_root: Path = Field(default_factory=lambda: Path("/storage"))

    # ----- derived flags -----
    @property
    def tts_mode(self) -> Literal["live", "mock"]:
        return "live" if self.elevenlabs_api_key else "mock"

    @property
    def payments_mode(self) -> Literal["live", "mock"]:
        return "live" if self.moyasar_api_key else "mock"

    @property
    def whatsapp_mode(self) -> Literal["live", "mock"]:
        return "live" if self.whatsapp_access_token else "mock"

    @property
    def email_mode(self) -> Literal["live", "mock"]:
        return "live" if self.resend_api_key else "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
