"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { supabaseBrowser } from "@/lib/api";

interface Intake {
  id: string;
  title_ar: string;
  source_audio_url: string;
  status: string;
  created_at: string;
}

export default function AdminConsole() {
  const supabase = supabaseBrowser();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "intake"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("catalog_intake")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) throw error;
      return (data ?? []) as Intake[];
    },
  });

  return (
    <div className="container py-12 max-w-5xl">
      <h1 className="font-display text-3xl mb-2">Admin Console</h1>
      <p className="text-muted-foreground mb-8">
        Catalog intake — review AI-detected name segments and publish.
      </p>

      {isLoading && <p>Loading...</p>}
      {data && data.length === 0 && (
        <div className="card">
          <p className="text-muted-foreground">
            No intake jobs yet. Upload a song to begin onboarding.
          </p>
        </div>
      )}

      {data && data.length > 0 && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-right border-b border-border">
              <th className="py-3">Title</th>
              <th>Status</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.map((i) => (
              <tr key={i.id} className="border-b border-border">
                <td className="py-3">{i.title_ar}</td>
                <td>
                  <span className="px-2 py-1 rounded bg-ivory-200 text-xs">
                    {i.status}
                  </span>
                </td>
                <td className="text-muted-foreground">
                  {new Date(i.created_at).toLocaleDateString("ar-SA")}
                </td>
                <td className="text-left">
                  <Link
                    href={`/admin/intake/${i.id}`}
                    className="text-gold hover:underline"
                  >
                    Review →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
