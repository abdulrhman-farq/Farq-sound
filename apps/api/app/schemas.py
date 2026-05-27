"""Pydantic request / response models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Era = Literal["classic", "modern"]
Role = Literal[
    "groom",
    "bride",
    "mother_of_groom",
    "father_of_groom",
    "mother_of_bride",
    "father_of_bride",
    "family_name",
]
OrderStatus = Literal[
    "draft", "rendering", "preview_ready", "paid", "delivered", "failed"
]
RenderStage = Literal["tts", "pitch_match", "splice", "mixdown", "master"]
RenderStatus = Literal["queued", "running", "done", "failed"]


class SongSegment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: Role
    sequence_index: int
    start_ms: int
    end_ms: int
    original_text_ar: str
    phonetic_hint: str | None = None
    prosody_note: Literal["sung", "spoken", "elongated"] | None = None


class SongSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    title_ar: str
    title_en: str | None = None
    artist_ar: str | None = None
    era: Era | None = None
    duration_seconds: int | None = None
    preview_url: str
    cover_image_url: str | None = None
    price_sar: float


class SongDetail(SongSummary):
    segments: list[SongSegment] = Field(default_factory=list)
    required_roles: list[Role] = Field(default_factory=list)


class NamesPayload(BaseModel):
    """Map of role → user-entered Arabic name."""

    groom: str | None = None
    bride: str | None = None
    mother_of_groom: str | None = None
    father_of_groom: str | None = None
    mother_of_bride: str | None = None
    father_of_bride: str | None = None
    family_name: str | None = None


class CreateOrderRequest(BaseModel):
    song_id: UUID
    names: NamesPayload


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    song_id: UUID
    status: OrderStatus
    names: dict
    preview_url: str | None = None
    final_url: str | None = None
    share_token: str | None = None
    amount_sar: float | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RenderJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stage: RenderStage
    status: RenderStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    log: str | None = None


class OrderWithJobs(OrderRead):
    jobs: list[RenderJobRead] = Field(default_factory=list)


class CheckoutResponse(BaseModel):
    payment_url: str
    payment_id: str
    mode: Literal["live", "mock"]


class SampleNamePreviewRequest(BaseModel):
    """Generate a single-name TTS clip for the wizard preview button."""

    song_id: UUID
    role: Role
    name_ar: str


class SampleNamePreviewResponse(BaseModel):
    audio_url: str
    duration_ms: int


class SharedOrderRead(BaseModel):
    id: UUID
    song_title_ar: str
    cover_image_url: str | None = None
    names: dict
    final_url: str
