"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api, type RenderStage } from "@/lib/api";
import { WaveformPlayer } from "@/components/waveform-player";

const STAGE_ORDER: RenderStage[] = [
  "tts",
  "pitch_match",
  "splice",
  "mixdown",
  "master",
];

export default function PreviewPage({
  params,
}: {
  params: { orderId: string };
}) {
  const { orderId } = params;
  const t = useTranslations();
  const [elapsed, setElapsed] = useState(0);
  const isDemo = orderId.startsWith("demo-");
  const demoNames = isDemo && typeof window !== "undefined"
    ? JSON.parse(window.localStorage.getItem(`farq:names:${orderId}`) ?? "{}")
    : null;

  const { data: order } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => api.getOrder(orderId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "rendering" ? 2_000 : false;
    },
    enabled: !isDemo,
  });

  useEffect(() => {
    if (order?.status !== "rendering") return;
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, [order?.status]);

  if (isDemo) {
    const couple = [demoNames?.groom, demoNames?.bride]
      .filter(Boolean)
      .join(" و ");
    return (
      <div className="container py-12 max-w-2xl text-center">
        <h1 className="font-display text-3xl mb-2">معاينة (وضع تجريبي)</h1>
        <p className="text-muted-foreground mb-6">
          هذه معاينة محلية — لتشغيل المعالجة الكاملة للصوت بالأسماء، يلزم تفعيل
          الـ Backend (راجع <code>SETUP.md</code>).
        </p>
        {couple && (
          <div className="card !p-6 mb-6">
            <p className="text-sm text-gold tracking-widest mb-2">الأسماء</p>
            <p className="font-display text-2xl">{couple}</p>
            <p className="text-sm text-muted-foreground mt-3">
              {Object.entries(demoNames ?? {})
                .filter(([k]) => k !== "groom" && k !== "bride")
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ")}
            </p>
          </div>
        )}
        <Link href="/songs" className="btn-primary">
          عودة للكتالوج
        </Link>
      </div>
    );
  }

  const currentStage = order
    ? (order.jobs.find((j) => j.status === "running")?.stage ??
        order.jobs[order.jobs.length - 1]?.stage ??
        "tts")
    : "tts";
  const completedCount = order
    ? order.jobs.filter((j) => j.status === "done").length
    : 0;

  if (!order) return <p className="container py-12">{t("common.loading")}</p>;

  if (order.status === "rendering") {
    return (
      <div className="container py-16 max-w-xl text-center">
        <h1 className="font-display text-3xl mb-2">{t("preview.title")}</h1>
        <p className="text-muted-foreground mb-8">
          {t(`preview.stages.${currentStage}` as never)}
        </p>
        <div className="h-2 bg-ivory-200 rounded overflow-hidden mb-6">
          <div
            className="h-full bg-gold transition-all"
            style={{
              width: `${(completedCount / STAGE_ORDER.length) * 100}%`,
            }}
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {elapsed}s · {completedCount}/{STAGE_ORDER.length}
        </p>
      </div>
    );
  }

  if (order.status === "failed") {
    return (
      <div className="container py-16 max-w-xl text-center">
        <h1 className="font-display text-3xl mb-2">
          {t("orders.status.failed")}
        </h1>
        <p className="text-muted-foreground mb-6">
          {order.error_message ?? t("errors.generic")}
        </p>
        <Link href={`/customize/${orderId}`} className="btn-primary">
          {t("preview.edit")}
        </Link>
      </div>
    );
  }

  if (!order.preview_url) {
    return (
      <div className="container py-12">
        <Link href={`/customize/${orderId}`} className="btn-primary">
          {t("preview.edit")}
        </Link>
      </div>
    );
  }

  return (
    <div className="container py-12 max-w-3xl">
      <h1 className="font-display text-3xl mb-2">{t("preview.title")}</h1>
      <p className="text-gold mb-8">{t("preview.ready")}</p>
      <WaveformPlayer url={order.preview_url} />
      <p className="mt-3 text-xs text-muted-foreground">
        {t("preview.watermarkNote")}
      </p>
      <div className="mt-8 flex items-center gap-3 flex-wrap">
        <Link href={`/checkout/${orderId}`} className="btn-accent">
          {t("preview.accept")}
        </Link>
        <Link href={`/customize/${orderId}`} className="btn-ghost">
          {t("preview.edit")}
        </Link>
      </div>
    </div>
  );
}
