import { getTranslations } from "next-intl/server";

interface Health {
  status: string;
  env: string;
  providers: Record<string, "live" | "mock">;
}

async function getHealth(): Promise<Health | null> {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  try {
    const r = await fetch(`${base}/health`, { cache: "no-store" });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}

export default async function HealthPage() {
  const t = await getTranslations();
  const health = await getHealth();

  return (
    <div className="container py-12 max-w-md">
      <h1 className="font-display text-3xl mb-6">Health</h1>
      {!health ? (
        <p className="text-red-600">API unreachable.</p>
      ) : (
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between border-b border-border pb-2">
            <dt className="text-muted-foreground">Status</dt>
            <dd>{health.status}</dd>
          </div>
          <div className="flex justify-between border-b border-border pb-2">
            <dt className="text-muted-foreground">Env</dt>
            <dd>{health.env}</dd>
          </div>
          {Object.entries(health.providers).map(([k, v]) => (
            <div key={k} className="flex justify-between border-b border-border pb-2">
              <dt className="text-muted-foreground">{k}</dt>
              <dd>
                <span
                  className={`px-2 py-0.5 rounded text-xs ${
                    v === "live"
                      ? "bg-green-100 text-green-800"
                      : "bg-ivory-200 text-muted-foreground"
                  }`}
                >
                  {v}
                </span>
              </dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-8 text-xs text-muted-foreground">{t("brand.name")}</p>
    </div>
  );
}
