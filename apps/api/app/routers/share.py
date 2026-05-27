"""Public share page payload — no auth required."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import anon
from app.schemas import SharedOrderRead

router = APIRouter()


@router.get("/{token}", response_model=SharedOrderRead)
def get_shared_order(token: str) -> SharedOrderRead:
    # Calls the SECURITY DEFINER RPC defined in migrations/0001_init.sql,
    # which only returns rows for delivered orders.
    rpc = anon().rpc("get_shared_order", {"token": token}).execute()
    rows = rpc.data or []
    if not rows:
        raise HTTPException(404, "Share link not found or order not delivered.")
    row = rows[0]
    return SharedOrderRead(
        id=row["id"],
        song_title_ar=row["song_title_ar"],
        cover_image_url=row.get("song_cover_image_url"),
        names=row["names"],
        final_url=row["final_url"],
    )
