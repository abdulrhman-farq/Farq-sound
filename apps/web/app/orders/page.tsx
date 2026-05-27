"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useEffect, useState } from "react";

import { isSupabaseConfigured, type Order, supabaseBrowser } from "@/lib/api";

export default function OrdersPage() {
  const t = useTranslations();
  const configured = isSupabaseConfigured();
  const supabase = configured ? supabaseBrowser() : null;

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders", "mine"],
    queryFn: async () => {
      if (!supabase) return [] as Order[];
      const { data, error } = await supabase
        .from("orders")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return (data ?? []) as Order[];
    },
    enabled: !!supabase,
  });

  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getUser().then((u) => setUserId(u.data.user?.id ?? null));
  }, [supabase]);

  if (!configured) {
    return (
      <div className="container py-12 max-w-xl text-center">
        <h1 className="font-display text-2xl mb-3">{t("orders.title")}</h1>
        <p className="text-muted-foreground">
          هذه الصفحة تتطلب تسجيل الدخول، وهو غير مفعّل في وضع المعاينة. أضف
          مفاتيح Supabase في <code>apps/web/.env.local</code> لتفعيلها.
        </p>
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="container py-12 text-center">
        <p className="mb-4">{t("nav.login")}</p>
      </div>
    );
  }

  if (isLoading) return <p className="container py-12">{t("common.loading")}</p>;
  if (!orders || orders.length === 0) {
    return (
      <div className="container py-12 text-center">
        <p className="text-muted-foreground mb-4">{t("orders.empty")}</p>
        <Link href="/songs" className="btn-accent">
          {t("songs.title")}
        </Link>
      </div>
    );
  }

  return (
    <div className="container py-12 max-w-3xl">
      <h1 className="font-display text-3xl mb-8">{t("orders.title")}</h1>
      <ul className="space-y-4">
        {orders.map((o) => (
          <li key={o.id} className="card flex items-center justify-between">
            <div>
              <p className="font-medium">
                {Object.values(o.names).filter(Boolean).join(" · ")}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {t(`orders.status.${o.status}` as never)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {o.status === "delivered" && o.final_url && (
                <a href={o.final_url} download className="btn-accent text-sm">
                  {t("orders.download")}
                </a>
              )}
              {o.status === "delivered" && o.share_token && (
                <Link
                  href={`/share/${o.share_token}`}
                  className="btn-ghost text-sm"
                >
                  {t("orders.share")}
                </Link>
              )}
              {o.status === "preview_ready" && (
                <Link
                  href={`/preview/${o.id}`}
                  className="btn-primary text-sm"
                >
                  {t("preview.title")}
                </Link>
              )}
              {o.status === "rendering" && (
                <Link href={`/preview/${o.id}`} className="btn-ghost text-sm">
                  {t("common.loading")}
                </Link>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
