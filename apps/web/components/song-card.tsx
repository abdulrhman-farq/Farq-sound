"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import type { SongSummary } from "@/lib/api";
import { formatSAR } from "@/lib/utils";

export function SongCard({ song }: { song: SongSummary }) {
  const t = useTranslations();
  return (
    <Link
      href={`/songs/${song.slug}`}
      className="card hover:border-gold transition-colors block group"
    >
      <div className="aspect-square rounded-md bg-ivory-200 overflow-hidden mb-4 relative">
        {song.cover_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={song.cover_image_url}
            alt={song.title_ar}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gold font-display text-4xl">
            {song.title_ar.slice(0, 1)}
          </div>
        )}
        {song.era && (
          <span className="absolute top-3 right-3 text-xs px-2 py-1 rounded bg-ivory/90 text-navy">
            {song.era === "classic" ? "كلاسيك" : "حديثة"}
          </span>
        )}
      </div>
      <h3 className="font-display text-xl mb-1">{song.title_ar}</h3>
      <p className="text-sm text-muted-foreground mb-3">
        {song.artist_ar ?? ""}
      </p>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gold">{t("songs.personalize")} ←</span>
        <span className="text-sm font-medium">{formatSAR(song.price_sar)}</span>
      </div>
    </Link>
  );
}
