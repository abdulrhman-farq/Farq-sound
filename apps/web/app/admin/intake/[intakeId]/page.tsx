"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy } from "lucide-react";
import { use, useEffect, useRef, useState } from "react";

import { isSupabaseConfigured, supabaseBrowser } from "@/lib/api";

type Segment = {
  role: string;
  sequence_index: number;
  start_ms: number;
  end_ms: number;
  original_text_ar: string;
  phonetic_hint?: string;
  prosody_note?: string;
};

const ROLES = [
  "groom",
  "bride",
  "mother_of_groom",
  "father_of_groom",
  "mother_of_bride",
  "father_of_bride",
  "family_name",
];

export default function IntakeReview({
  params,
}: {
  params: { intakeId: string };
}) {
  const { intakeId } = params;
  const supabase = isSupabaseConfigured() ? supabaseBrowser() : null;
  const qc = useQueryClient();
  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  const { data: intake } = useQuery({
    queryKey: ["intake", intakeId],
    queryFn: async () => {
      if (!supabase) throw new Error("Supabase not configured.");
      const { data, error } = await supabase
        .from("catalog_intake")
        .select("*")
        .eq("id", intakeId)
        .single();
      if (error) throw error;
      return data;
    },
    enabled: !!supabase,
  });

  const [segments, setSegments] = useState<Segment[]>([]);
  useEffect(() => {
    if (intake?.detected_segments) setSegments(intake.detected_segments);
  }, [intake]);

  // --- Voice cloning ---
  const fileRef = useRef<HTMLInputElement>(null);
  const [voiceName, setVoiceName] = useState("");
  const [voiceDesc, setVoiceDesc] = useState("");
  const [voiceId, setVoiceId] = useState<string | null>(null);
  const [voiceMode, setVoiceMode] = useState<"live" | "mock" | null>(null);
  const [voiceError, setVoiceError] = useState("");

  const train = useMutation({
    mutationFn: async () => {
      const files = fileRef.current?.files;
      if (!files || files.length === 0) throw new Error("اختاري ملف عيّنة");
      if (!voiceName.trim()) throw new Error("اكتبي اسم للصوت");

      const token = supabase
        ? (await supabase.auth.getSession()).data.session?.access_token
        : null;
      const form = new FormData();
      form.append("name", voiceName.trim());
      if (voiceDesc.trim()) form.append("description", voiceDesc.trim());
      for (const f of Array.from(files)) form.append("files", f);

      const r = await fetch(`${apiBase}/api/admin/voices`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!r.ok) throw new Error(await r.text());
      return (await r.json()) as {
        voice_id: string;
        mode: "live" | "mock";
        provider: string;
      };
    },
    onSuccess: (data) => {
      setVoiceId(data.voice_id);
      setVoiceMode(data.mode);
      setVoiceError("");
    },
    onError: (err: Error) => {
      setVoiceError(err.message);
      setVoiceId(null);
    },
  });

  const copyVoiceId = async () => {
    if (!voiceId) return;
    await navigator.clipboard.writeText(voiceId);
  };

  const save = useMutation({
    mutationFn: async () => {
      const token = supabase
        ? (await supabase.auth.getSession()).data.session?.access_token
        : null;
      const r = await fetch(`${apiBase}/api/admin/intake/${intakeId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          detected_segments: segments,
          status: "approved",
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["intake", intakeId] }),
  });

  if (!intake) return <p className="container py-12">Loading...</p>;

  const update = (i: number, patch: Partial<Segment>) =>
    setSegments(segments.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));

  const add = () =>
    setSegments([
      ...segments,
      {
        role: "groom",
        sequence_index: segments.length + 1,
        start_ms: 0,
        end_ms: 0,
        original_text_ar: "",
      },
    ]);

  return (
    <div className="container py-12 max-w-4xl">
      <h1 className="font-display text-3xl mb-2">{intake.title_ar}</h1>
      <p className="text-muted-foreground mb-6">
        Status: {intake.status}
      </p>

      <audio controls src={intake.source_audio_url} className="w-full mb-8" />

      {/* ─── Voice cloning ───────────────────────────────────────── */}
      <section className="card mb-8">
        <h2 className="font-medium mb-1">١. تدريب صوت المنشد</h2>
        <p className="text-sm text-muted-foreground mb-4">
          ارفعي عيّنة (أو أكثر) من الصوت النقي للمنشد — بدون موسيقى. هذي
          الخطوة مرة وحدة لكل منشد. عند الانتهاء نسخي الـ <code>voice_id</code>
          وألصقيه عند النشر بالأسفل.
        </p>

        <div className="grid sm:grid-cols-2 gap-3 mb-3">
          <input
            type="text"
            dir="rtl"
            value={voiceName}
            onChange={(e) => setVoiceName(e.target.value)}
            placeholder="اسم الصوت — مثال: farq-classic-1"
            className="input !py-2 !text-sm"
          />
          <input
            type="text"
            dir="rtl"
            value={voiceDesc}
            onChange={(e) => setVoiceDesc(e.target.value)}
            placeholder="وصف مختصر (اختياري)"
            className="input !py-2 !text-sm"
          />
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="audio/wav,audio/mpeg,audio/mp3,audio/flac,audio/ogg,audio/x-m4a"
          multiple
          className="block w-full text-sm mb-4
                     file:me-3 file:py-2 file:px-4 file:rounded-md
                     file:border-0 file:bg-navy file:text-ivory
                     hover:file:bg-navy/90 file:cursor-pointer"
        />

        <button
          type="button"
          onClick={() => train.mutate()}
          disabled={train.isPending}
          className="btn-accent text-sm"
        >
          {train.isPending ? "جاري التدريب..." : "درّبي الصوت"}
        </button>

        {voiceError && (
          <p className="text-red-600 text-sm mt-3">{voiceError}</p>
        )}

        {voiceId && (
          <div className="mt-4 p-3 rounded-md bg-gold/10 border border-gold">
            <div className="flex items-center justify-between gap-3">
              <code className="text-sm font-mono break-all">{voiceId}</code>
              <button
                type="button"
                onClick={copyVoiceId}
                className="btn-ghost !p-2 text-xs"
                aria-label="copy voice id"
              >
                <Copy size={14} />
              </button>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              المزود: <span className="font-medium">{voiceMode}</span>
              {voiceMode === "mock" && (
                <>
                  {" "}— وضع المحاكاة (ELEVENLABS_API_KEY غير مفعّل).
                </>
              )}
            </p>
          </div>
        )}
      </section>

      <h2 className="font-medium mb-3">٢. المقاطع المكتشفة (Detected segments)</h2>
      <div className="space-y-3 mb-6">
        {segments.map((seg, i) => (
          <div
            key={i}
            className="card !p-4 grid grid-cols-12 gap-3 items-center"
          >
            <select
              value={seg.role}
              onChange={(e) => update(i, { role: e.target.value })}
              className="col-span-3 input !py-2 !text-sm"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <input
              type="number"
              value={seg.start_ms}
              onChange={(e) => update(i, { start_ms: Number(e.target.value) })}
              className="col-span-2 input !py-2 !text-sm"
              placeholder="start ms"
            />
            <input
              type="number"
              value={seg.end_ms}
              onChange={(e) => update(i, { end_ms: Number(e.target.value) })}
              className="col-span-2 input !py-2 !text-sm"
              placeholder="end ms"
            />
            <input
              type="text"
              dir="rtl"
              value={seg.original_text_ar}
              onChange={(e) =>
                update(i, { original_text_ar: e.target.value })
              }
              className="col-span-4 input !py-2 !text-sm"
              placeholder="placeholder text"
            />
            <button
              type="button"
              onClick={() => setSegments(segments.filter((_, idx) => idx !== i))}
              className="col-span-1 text-red-600 text-xs"
            >
              delete
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button type="button" onClick={add} className="btn-ghost">
          + Add segment
        </button>
        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={save.isPending}
          className="btn-primary"
        >
          {save.isPending ? "Saving..." : "Save & Approve"}
        </button>
      </div>
    </div>
  );
}
