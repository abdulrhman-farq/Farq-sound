"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

export default function MockCheckout() {
  const t = useTranslations();
  const params = useSearchParams();
  const router = useRouter();
  const orderId = params.get("order_id");
  const paymentId = params.get("payment_id");
  const [working, setWorking] = useState(false);

  if (!orderId || !paymentId) {
    return <p className="container py-12">Missing payment params.</p>;
  }

  const approve = async () => {
    setWorking(true);
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    await fetch(`${apiBase}/api/webhooks/moyasar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: paymentId,
        status: "paid",
        metadata: { order_id: orderId },
      }),
    });
    router.push(`/orders/${orderId}`);
  };

  return (
    <div className="container py-16 max-w-md">
      <h1 className="font-display text-3xl mb-4">{t("checkout.pay")}</h1>
      <p className="text-muted-foreground mb-8">{t("checkout.mockNote")}</p>
      <div className="card mb-6 text-sm">
        <p className="text-muted-foreground">Order</p>
        <p className="font-mono">{orderId}</p>
        <p className="text-muted-foreground mt-3">Payment</p>
        <p className="font-mono">{paymentId}</p>
      </div>
      <button
        type="button"
        className="btn-accent w-full"
        onClick={approve}
        disabled={working}
      >
        {working ? t("common.loading") : t("checkout.pay")}
      </button>
    </div>
  );
}
