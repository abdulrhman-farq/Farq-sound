"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

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
      const { data, error } = await supabase
        .from("catalog_intake")
        .select("*")
        .eq("id", intakeId)
        .single();
      if (error) throw error;
      return data;
    },
  });

  const [segments, setSegments] = useState<Segment[]>([]);
  useEffect(() => {
    if (intake?.detected_segments) setSegments(intake.detected_segments);
  }, [intake]);

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

      <h2 className="font-medium mb-3">Detected segments</h2>
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
