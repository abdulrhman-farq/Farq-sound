import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ArrowLeft, Music, PenLine, Sparkles } from "lucide-react";

import { api } from "@/lib/api";
import { SongCard } from "@/components/song-card";

export default async function HomePage() {
  const t = await getTranslations();
  let featured: Awaited<ReturnType<typeof api.listSongs>> = [];
  try {
    featured = await fetchFeatured();
  } catch {
    /* API may not be running at build time — fail soft. */
  }

  return (
    <>
      {/* Hero */}
      <section className="container py-20 md:py-28 text-center">
        <p className="ornament mb-6 mx-auto justify-center text-sm tracking-widest uppercase">
          {t("brand.name")}
        </p>
        <h1 className="heading-display text-navy mx-auto max-w-3xl">
          {t("home.heroTitle")}
        </h1>
        <p className="mt-6 text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          {t("home.heroSubtitle")}
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/songs" className="btn-accent text-lg">
            {t("home.heroCta")}
            <ArrowLeft size={20} className="rtl:rotate-180" />
          </Link>
        </div>
      </section>

      {/* Three steps */}
      <section className="bg-ivory-100 py-20">
        <div className="container">
          <h2 className="font-display text-3xl text-center mb-12">
            {t("home.stepsTitle")}
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: Music, key: "one" },
              { icon: PenLine, key: "two" },
              { icon: Sparkles, key: "three" },
            ].map(({ icon: Icon, key }, i) => (
              <div key={key} className="card text-center">
                <div className="mx-auto w-14 h-14 rounded-full bg-gold/15 text-gold flex items-center justify-center mb-4">
                  <Icon size={24} />
                </div>
                <p className="text-gold text-sm mb-2">٠{i + 1}</p>
                <h3 className="font-display text-2xl mb-2">
                  {t(`home.steps.${key}.title` as never)}
                </h3>
                <p className="text-muted-foreground">
                  {t(`home.steps.${key}.body` as never)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Featured */}
      <section className="container py-20">
        <h2 className="font-display text-3xl mb-8 flex items-center gap-4">
          <span>{t("home.featuredTitle")}</span>
          <span className="h-px flex-1 bg-border" />
        </h2>
        {featured.length === 0 ? (
          <p className="text-muted-foreground">{t("common.loading")}</p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {featured.slice(0, 6).map((s) => (
              <SongCard key={s.id} song={s} />
            ))}
          </div>
        )}
      </section>

      {/* Trust */}
      <section className="bg-navy text-ivory py-14">
        <div className="container text-center">
          <p className="text-sm tracking-widest uppercase text-gold mb-3">
            {t("home.trustTitle")}
          </p>
          <div className="flex items-center justify-center gap-6 flex-wrap opacity-90 text-sm">
            <span>mada</span>
            <span>·</span>
            <span>Visa</span>
            <span>·</span>
            <span>Mastercard</span>
            <span>·</span>
            <span>Apple Pay</span>
            <span>·</span>
            <span>STC Pay</span>
          </div>
        </div>
      </section>
    </>
  );
}

async function fetchFeatured() {
  // Server-side fetch via API base URL.
  const url = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/songs`;
  const r = await fetch(url, { next: { revalidate: 60 } });
  if (!r.ok) throw new Error("API not available");
  return (await r.json()) as Awaited<ReturnType<typeof api.listSongs>>;
}
