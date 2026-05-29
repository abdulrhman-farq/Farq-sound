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

  const { data: order } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => api.getOrder(orderId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "rendering" ? 2_000 : false;
    },
  });

  useEffect(() => {
    if (order?.status !== "rendering") return;
    const id = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(id);
  }, [order?.status]);

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
