import Link from "next/link";
import { getTranslations } from "next-intl/server";

export async function SiteHeader() {
  const t = await getTranslations();
  return (
    <header className="border-b border-border bg-ivory/80 backdrop-blur sticky top-0 z-40">
      <div className="container flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2">
          <span className="font-display text-2xl text-navy">
            {t("brand.name")}
          </span>
          <span className="text-gold text-sm hidden sm:inline">
            — {t("brand.tagline")}
          </span>
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="/songs" className="hover:text-gold transition-colors">
            {t("nav.songs")}
          </Link>
          <Link href="/orders" className="hover:text-gold transition-colors">
            {t("nav.orders")}
          </Link>
        </nav>
      </div>
    </header>
  );
}
