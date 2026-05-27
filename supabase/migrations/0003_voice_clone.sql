-- Voice clone metadata captured during catalog intake.
-- Populated by POST /api/admin/intake/{id}/train-voice.

alter table catalog_intake
  add column if not exists voice_model_id text,
  add column if not exists voice_engine text;
