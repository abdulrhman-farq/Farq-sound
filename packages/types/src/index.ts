// Shared TS types for Farq Sound.
// Generated copies of these should be produced from FastAPI's OpenAPI
// schema via `pnpm types:gen` — this file is the hand-curated subset
// the web app currently consumes.

export type Era = "classic" | "modern";

export type Role =
  | "groom"
  | "bride"
  | "mother_of_groom"
  | "father_of_groom"
  | "mother_of_bride"
  | "father_of_bride"
  | "family_name";

export type OrderStatus =
  | "draft"
  | "rendering"
  | "preview_ready"
  | "paid"
  | "delivered"
  | "failed";

export type RenderStage =
  | "tts"
  | "pitch_match"
  | "splice"
  | "mixdown"
  | "master";

export type RenderStatus = "queued" | "running" | "done" | "failed";

export interface SongSummary {
  id: string;
  slug: string;
  title_ar: string;
  title_en?: string | null;
  artist_ar?: string | null;
  era?: Era | null;
  duration_seconds?: number | null;
  preview_url: string;
  cover_image_url?: string | null;
  price_sar: number;
}
