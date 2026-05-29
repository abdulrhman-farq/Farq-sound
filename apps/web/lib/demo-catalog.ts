// Local fallback catalog used when the backend API is unavailable
// (e.g. you are just browsing the UI without booting uvicorn).

import type { SongDetail, SongSummary } from "./api";

const songs: SongSummary[] = [
  {
    id: "00000000-0000-0000-0000-00000000beef",
    slug: "yamarhaba",
    title_ar: "يا مرحبا يا كل حاضر",
    title_en: "Welcome to Everyone Here",
    artist_ar: "فرقة فرق ساوند",
    era: "classic",
    duration_seconds: 220,
    preview_url: "/samples/yamarhaba.mp3",
    cover_image_url: null,
    price_sar: 49,
  },
  {
    id: "00000000-0000-0000-0000-000000000001",
    slug: "demo-classic-1",
    title_ar: "زفّة العروس الكلاسيكية",
    title_en: "Classic Bridal Entrance",
    artist_ar: "فرقة فرق ساوند",
    era: "classic",
    duration_seconds: 180,
    preview_url: "/samples/preview-demo-classic-1.mp3",
    cover_image_url: null,
    price_sar: 49,
  },
  {
    id: "00000000-0000-0000-0000-000000000002",
    slug: "demo-classic-2",
    title_ar: "هلا بالعروس",
    title_en: "Welcome to the Bride",
    artist_ar: "فرقة فرق ساوند",
    era: "classic",
    duration_seconds: 160,
    preview_url: "/samples/preview-demo-classic-2.mp3",
    cover_image_url: null,
    price_sar: 49,
  },
  {
    id: "00000000-0000-0000-0000-000000000003",
    slug: "demo-modern-1",
    title_ar: "ليلتنا حلوة",
    title_en: "Our Beautiful Night",
    artist_ar: "فرقة فرق ساوند",
    era: "modern",
    duration_seconds: 200,
    preview_url: "/samples/preview-demo-modern-1.mp3",
    cover_image_url: null,
    price_sar: 59,
  },
];

const details: Record<string, SongDetail> = Object.fromEntries(
  songs.map((s) => [
    s.slug,
    {
      ...s,
      segments: [
        {
          id: `${s.id}-seg-1`,
          role: "bride",
          sequence_index: 0,
          start_ms: 12000,
          end_ms: 14500,
          original_text_ar: "[اسم العروس]",
          phonetic_hint: null,
          prosody_note: "sung",
        },
        {
          id: `${s.id}-seg-2`,
          role: "groom",
          sequence_index: 1,
          start_ms: 28000,
          end_ms: 30500,
          original_text_ar: "[اسم العريس]",
          phonetic_hint: null,
          prosody_note: "sung",
        },
      ],
      required_roles: ["bride", "groom"],
    },
  ]),
);

export const demoCatalog = {
  list(params?: { era?: "classic" | "modern"; search?: string }): SongSummary[] {
    let rows = [...songs];
    if (params?.era) rows = rows.filter((r) => r.era === params.era);
    if (params?.search) rows = rows.filter((r) => r.title_ar.includes(params.search!));
    return rows;
  },
  get(slug: string): SongDetail | null {
    return details[slug] ?? null;
  },
};
