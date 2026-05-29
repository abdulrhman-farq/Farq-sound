"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { WaveformPlayer } from "@/components/waveform-player";
import { formatSAR } from "@/lib/utils";

export default function SongDetailPage({
  params,
}: {
  params: { slug: string };
}) {
  const { slug } = params;
  const t = useTranslations();
  const router = useRouter();

  const { data: song, isLoading } = useQuery({
    queryKey: ["song", slug],
    queryFn: () => api.getSong(slug),
  });

  const start = useMutation({
    mutationFn: async () => {
      if (!song) throw new Error("no song");
      // Guest mode is auto-applied by api.ts via X-Device-Id, so this
      // always creates a real backend order even without login.
      const order = await api.createOrder(song.id, {});
      return { id: order.id };
    },
    onSuccess: (order) => router.push(`/customize/${order.id}`),
  });

  if (isLoading) {
    return <p className="container py-12">{t("common.loading")}</p>;
  }
  if (!song) {
    return <p className="container py-12">{t("errors.notFound")}</p>;
  }

  const markers = song.segments.map((s) => ({
    start_ms: s.start_ms,
    end_ms: s.end_ms,
    label: t(`song.roles.${s.role}` as never),
  }));

  return (
    <div className="container py-12 max-w-4xl">
      <div className="grid md:grid-cols-3 gap-8 items-start mb-10">
        <div className="aspect-square rounded-lg overflow-hidden bg-ivory-200">
          {song.cover_image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={song.cover_image_url}
              alt={song.title_ar}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gold font-display text-6xl">
              {song.title_ar.slice(0, 1)}
            </div>
          )}
        </div>
        <div className="md:col-span-2">
          <p className="text-gold text-sm tracking-widest uppercase mb-2">
            {song.era === "classic" ? "كلاسيك" : "حديثة"}
          </p>
          <h1 className="font-display text-4xl mb-2">{song.title_ar}</h1>
          <p className="text-muted-foreground mb-6">{song.artist_ar ?? ""}</p>
          <p className="text-lg mb-6">
            {t("songs.priceFrom")}{" "}
            <span className="font-medium">{formatSAR(song.price_sar)}</span>
          </p>
          <button
            type="button"
            className="btn-accent text-lg"
            onClick={() => start.mutate()}
            disabled={start.isPending}
          >
            {start.isPending ? t("common.loading") : t("songs.personalize")}
          </button>
        </div>
      </div>

      <WaveformPlayer url={song.preview_url} markers={markers} />

      <section className="mt-10">
        <h2 className="font-display text-2xl mb-4">
          {t("song.segmentsTitle")}
        </h2>
        <ul className="grid sm:grid-cols-2 gap-3">
          {song.required_roles.map((role) => (
            <li
              key={role}
              className="card !p-4 flex items-center justify-between"
            >
              <span>{t(`song.roles.${role}` as never)}</span>
              <span className="text-gold text-sm">سيتغير</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
