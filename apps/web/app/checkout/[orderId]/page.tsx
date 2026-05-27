"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { use } from "react";

import { api } from "@/lib/api";
import { formatSAR } from "@/lib/utils";

export default function CheckoutPage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = use(params);
  const t = useTranslations();

  const { data: order } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => api.getOrder(orderId),
  });

  const pay = useMutation({
    mutationFn: () => api.checkout(orderId),
    onSuccess: (s) => {
      window.location.assign(s.payment_url);
    },
  });

  if (!order) return <p className="container py-12">{t("common.loading")}</p>;

  return (
    <div className="container py-12 max-w-xl">
      <h1 className="font-display text-3xl mb-8">{t("checkout.title")}</h1>

      <div className="card mb-6">
        <h2 className="font-medium mb-4">{t("checkout.summary")}</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted-foreground">
              {t("checkout.songLabel")}
            </dt>
            <dd>{order.song_id.slice(0, 8)}...</dd>
          </div>
          {Object.entries(order.names).map(([role, name]) => (
            <div key={role} className="flex justify-between">
              <dt className="text-muted-foreground">
                {t(`song.roles.${role}` as never)}
              </dt>
              <dd>{name}</dd>
            </div>
          ))}
          <div className="flex justify-between border-t border-border pt-3 mt-3 text-lg">
            <dt>{t("checkout.total")}</dt>
            <dd className="font-medium">
              {formatSAR(order.amount_sar ?? 0)}
            </dd>
          </div>
        </dl>
      </div>

      <button
        type="button"
        className="btn-accent w-full text-lg"
        onClick={() => pay.mutate()}
        disabled={pay.isPending}
      >
        {pay.isPending ? t("common.loading") : t("checkout.pay")}
      </button>
      <p className="text-xs text-muted-foreground text-center mt-4">
        {t("checkout.secure")}
      </p>
    </div>
  );
}
