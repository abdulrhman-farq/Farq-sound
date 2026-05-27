import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { WaveformPlayer } from "@/components/waveform-player";

interface Shared {
  id: string;
  song_title_ar: string;
  cover_image_url?: string | null;
  names: Record<string, string>;
  final_url: string;
}

async function getShared(token: string): Promise<Shared | null> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const r = await fetch(`${base}/api/share/${token}`, {
    next: { revalidate: 30 },
  });
  if (!r.ok) return null;
  return r.json();
}

export default async function SharePage({
  params,
}: {
  params: { token: string };
}) {
  const { token } = params;
  const t = await getTranslations();
  const data = await getShared(token);

  if (!data) {
    return <p className="container py-16 text-center">{t("errors.notFound")}</p>;
  }

  const couple = [data.names.groom, data.names.bride]
    .filter(Boolean)
    .join(" و ");

  return (
    <div className="container py-16 max-w-2xl text-center">
      <p className="ornament mb-6 mx-auto justify-center text-xs tracking-widest uppercase">
        فرق ساوند
      </p>
      <h1 className="heading-display mb-6">
        {t("share.headline", { couple })}
      </h1>
      <p className="font-display text-2xl text-gold mb-10">
        {data.song_title_ar}
      </p>

      <div className="rtl:text-right ltr:text-left">
        <WaveformPlayer url={data.final_url} />
      </div>

      <div className="mt-10">
        <Link href="/songs" className="btn-accent">
          {t("share.cta")}
        </Link>
      </div>
    </div>
  );
}
