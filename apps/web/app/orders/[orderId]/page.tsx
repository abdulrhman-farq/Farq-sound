"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { use } from "react";

import { api } from "@/lib/api";
import { WaveformPlayer } from "@/components/waveform-player";

export default function OrderDetail({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = use(params);
  const t = useTranslations();

  const { data: order } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => api.getOrder(orderId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "paid" || status === "rendering" ? 2_000 : false;
    },
  });

  if (!order) return <p className="container py-12">{t("common.loading")}</p>;

  return (
    <div className="container py-12 max-w-3xl">
      <p className="text-gold mb-2 text-sm tracking-widest uppercase">
        {t(`orders.status.${order.status}` as never)}
      </p>
      <h1 className="font-display text-3xl mb-8">
        {Object.values(order.names).filter(Boolean).join(" · ")}
      </h1>

      {(order.status === "paid" || order.status === "rendering") && (
        <p className="text-muted-foreground">{t("preview.stages.master")}</p>
      )}

      {order.status === "delivered" && order.final_url && (
        <>
          <WaveformPlayer url={order.final_url} />
          <div className="mt-6 flex gap-3 flex-wrap">
            <a href={order.final_url} download className="btn-accent">
              {t("orders.download")}
            </a>
            {order.share_token && (
              <Link
                href={`/share/${order.share_token}`}
                className="btn-ghost"
              >
                {t("orders.share")}
              </Link>
            )}
          </div>
        </>
      )}

      {order.status === "failed" && (
        <p className="text-red-600">
          {order.error_message ?? t("errors.generic")}
        </p>
      )}
    </div>
  );
}
