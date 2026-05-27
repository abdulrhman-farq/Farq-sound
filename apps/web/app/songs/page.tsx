"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { api } from "@/lib/api";
import { SongCard } from "@/components/song-card";

export default function CatalogPage() {
  const t = useTranslations();
  const [era, setEra] = useState<"classic" | "modern" | undefined>();
  const [search, setSearch] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["songs", era, search],
    queryFn: () => api.listSongs({ era, search: search || undefined }),
  });

  return (
    <div className="container py-12">
      <h1 className="font-display text-4xl mb-2">{t("songs.title")}</h1>
      <p className="text-muted-foreground mb-8">{t("home.heroSubtitle")}</p>

      <div className="flex flex-wrap gap-3 mb-8">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("songs.filters.search")}
          className="input max-w-sm"
        />
        <div className="flex gap-2">
          {(
            [
              { v: undefined, label: t("songs.filters.all") },
              { v: "classic" as const, label: t("songs.filters.classic") },
              { v: "modern" as const, label: t("songs.filters.modern") },
            ] as const
          ).map((opt, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setEra(opt.v)}
              className={`px-4 py-2 rounded-md text-sm transition-colors ${
                era === opt.v
                  ? "bg-navy text-ivory"
                  : "bg-ivory-200 text-navy hover:bg-ivory-300"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-muted-foreground">{t("common.loading")}</p>}
      {error && <p className="text-red-600">{t("errors.generic")}</p>}
      {data && data.length === 0 && (
        <p className="text-muted-foreground">{t("errors.notFound")}</p>
      )}
      {data && data.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.map((s) => (
            <SongCard key={s.id} song={s} />
          ))}
        </div>
      )}
    </div>
  );
}
