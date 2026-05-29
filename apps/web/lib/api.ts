"use client";

import { createBrowserClient } from "@supabase/ssr";

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

export type RenderStage = "tts" | "pitch_match" | "splice" | "mixdown" | "master";
export type RenderStatus = "queued" | "running" | "done" | "failed";

export interface SongSummary {
  id: string;
  slug: string;
  title_ar: string;
  title_en?: string | null;
  artist_ar?: string | null;
  era?: "classic" | "modern" | null;
  duration_seconds?: number | null;
  preview_url: string;
  cover_image_url?: string | null;
  price_sar: number;
}

export interface SongSegment {
  id: string;
  role: Role;
  sequence_index: number;
  start_ms: number;
  end_ms: number;
  original_text_ar: string;
  phonetic_hint?: string | null;
  prosody_note?: "sung" | "spoken" | "elongated" | null;
}

export interface SongDetail extends SongSummary {
  segments: SongSegment[];
  required_roles: Role[];
}

export interface Order {
  id: string;
  song_id: string;
  status: OrderStatus;
  names: Partial<Record<Role, string>>;
  preview_url?: string | null;
  final_url?: string | null;
  share_token?: string | null;
  amount_sar?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RenderJob {
  id: string;
  stage: RenderStage;
  status: RenderStatus;
  started_at?: string | null;
  completed_at?: string | null;
  log?: string | null;
}

export interface OrderWithJobs extends Order {
  jobs: RenderJob[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function safeReq<T>(path: string, init: RequestInit = {}): Promise<T | null> {
  try {
    return await req<T>(path, init);
  } catch {
    return null;
  }
}

export const isSupabaseConfigured = () =>
  Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );

export const supabaseBrowser = () => {
  if (!isSupabaseConfigured()) {
    throw new Error(
      "Supabase is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in apps/web/.env.local.",
    );
  }
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
};

// Stable per-browser device id — gives every guest visitor a real
// identity on the backend without forcing a signup. Persists across
// reloads via localStorage.
const DEVICE_ID_KEY = "farq:device-id";

export function getDeviceId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

async function authHeaders(): Promise<HeadersInit> {
  // Prefer a Supabase session if present (post-login flow).
  if (isSupabaseConfigured()) {
    try {
      const supabase = supabaseBrowser();
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (token) return { Authorization: `Bearer ${token}` };
    } catch {
      // fall through to guest mode
    }
  }
  // Guest mode — stable device id, backend creates a synthetic profile.
  const deviceId = getDeviceId();
  return deviceId ? { "X-Device-Id": deviceId } : {};
}

async function req<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(await authHeaders()),
    ...(init.headers ?? {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

import { demoCatalog } from "./demo-catalog";

export const api = {
  listSongs: async (params?: { era?: "classic" | "modern"; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.era) qs.set("era", params.era);
    if (params?.search) qs.set("search", params.search);
    const s = qs.toString();
    const live = await safeReq<SongSummary[]>(`/api/songs${s ? `?${s}` : ""}`);
    return live ?? demoCatalog.list(params);
  },
  getSong: async (slug: string) => {
    const live = await safeReq<SongDetail>(`/api/songs/${slug}`);
    if (live) return live;
    const demo = demoCatalog.get(slug);
    if (!demo) throw new Error("Song not found");
    return demo;
  },
  createOrder: (song_id: string, names: Partial<Record<Role, string>>) =>
    req<Order>("/api/orders", {
      method: "POST",
      body: JSON.stringify({ song_id, names }),
    }),
  updateNames: (id: string, names: Partial<Record<Role, string>>) =>
    req<Order>(`/api/orders/${id}/names`, {
      method: "PATCH",
      body: JSON.stringify({ names }),
    }),
  getOrder: (id: string) => req<OrderWithJobs>(`/api/orders/${id}`),
  renderPreview: (id: string) =>
    req<Order>(`/api/orders/${id}/render-preview`, { method: "POST" }),
  checkout: (id: string) =>
    req<{ payment_url: string; payment_id: string; mode: "live" | "mock" }>(
      `/api/orders/${id}/checkout`,
      { method: "POST" },
    ),
  previewName: (song_id: string, role: Role, name_ar: string) =>
    req<{ audio_url: string; duration_ms: number }>(
      "/api/orders/preview-name",
      {
        method: "POST",
        body: JSON.stringify({ song_id, role, name_ar }),
      },
    ),
};
