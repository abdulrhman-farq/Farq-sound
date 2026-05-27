"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

import { api, type Role } from "@/lib/api";
import { isArabic } from "@/lib/utils";

const ROLE_ORDER: Role[] = [
  "groom",
  "bride",
  "mother_of_groom",
  "father_of_groom",
  "mother_of_bride",
  "father_of_bride",
  "family_name",
];

export default function CustomizePage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = use(params);
  const t = useTranslations();
  const router = useRouter();

  const { data: order } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => api.getOrder(orderId),
  });
  const { data: song } = useQuery({
    queryKey: ["order-song", order?.song_id],
    queryFn: async () => {
      if (!order) return null;
      const songs = await api.listSongs();
      const found = songs.find((s) => s.id === order.song_id);
      if (!found) throw new Error("song not found");
      return api.getSong(found.slug);
    },
    enabled: !!order,
  });

  const requiredRoles = (song?.required_roles ?? []).sort(
    (a, b) => ROLE_ORDER.indexOf(a) - ROLE_ORDER.indexOf(b),
  );

  const [stepIdx, setStepIdx] = useState(0);
  const [values, setValues] = useState<Partial<Record<Role, string>>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    if (order) setValues((v) => ({ ...order.names, ...v }));
  }, [order]);

  const currentRole = requiredRoles[stepIdx];
  const currentValue = currentRole ? values[currentRole] ?? "" : "";

  const previewName = useMutation({
    mutationFn: async () => {
      if (!song || !currentRole || !currentValue) return null;
      return api.previewName(song.id, currentRole, currentValue);
    },
  });

  const renderPreview = useMutation({
    mutationFn: async () => {
      await api.updateNames(orderId, values);
      return api.renderPreview(orderId);
    },
    onSuccess: () => router.push(`/preview/${orderId}`),
  });

  const goNext = () => {
    if (!currentRole) return;
    const v = (values[currentRole] ?? "").trim();
    if (!v) return setError(t("customize.validation.required"));
    if (v.length < 2 || v.length > 40)
      return setError(t("customize.validation.length"));
    if (!isArabic(v)) return setError(t("customize.validation.arabicOnly"));
    setError("");
    if (stepIdx + 1 < requiredRoles.length) setStepIdx(stepIdx + 1);
    else renderPreview.mutate();
  };

  if (!order || !song || !currentRole) {
    return <p className="container py-12">{t("common.loading")}</p>;
  }

  return (
    <div className="container py-12 max-w-2xl">
      <p className="text-sm text-muted-foreground mb-2">
        {t("customize.step", {
          current: stepIdx + 1,
          total: requiredRoles.length,
        })}
      </p>
      <div className="h-1 bg-ivory-200 rounded mb-8 overflow-hidden">
        <div
          className="h-full bg-gold transition-all"
          style={{
            width: `${((stepIdx + 1) / requiredRoles.length) * 100}%`,
          }}
        />
      </div>

      <h1 className="font-display text-3xl mb-2">{t("customize.title")}</h1>
      <p className="text-muted-foreground mb-8">
        {t(`song.roles.${currentRole}` as never)}
      </p>

      <label className="label" htmlFor="name">
        {t(`song.roles.${currentRole}` as never)}
      </label>
      <input
        id="name"
        type="text"
        autoFocus
        dir="rtl"
        value={currentValue}
        onChange={(e) =>
          setValues({ ...values, [currentRole]: e.target.value })
        }
        placeholder={t("customize.namePlaceholder")}
        className="input text-2xl"
      />
      {error && <p className="text-red-600 mt-2 text-sm">{error}</p>}

      <div className="mt-4">
        <button
          type="button"
          onClick={() => previewName.mutate()}
          disabled={!currentValue || previewName.isPending}
          className="btn-ghost text-sm"
        >
          {previewName.isPending
            ? t("customize.loadingPreview")
            : t("customize.tryPreview")}
        </button>
        {previewName.data?.audio_url && (
          <audio
            controls
            src={previewName.data.audio_url}
            className="mt-3 w-full"
          />
        )}
      </div>

      <div className="mt-10 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setStepIdx(Math.max(0, stepIdx - 1))}
          disabled={stepIdx === 0}
          className="btn-ghost"
        >
          {t("customize.prev")}
        </button>
        <button
          type="button"
          onClick={goNext}
          disabled={renderPreview.isPending}
          className="btn-primary"
        >
          {stepIdx + 1 === requiredRoles.length
            ? renderPreview.isPending
              ? t("common.loading")
              : t("customize.submit")
            : t("customize.next")}
        </button>
      </div>
    </div>
  );
}
