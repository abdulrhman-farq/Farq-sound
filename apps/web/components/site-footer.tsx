import { getTranslations } from "next-intl/server";

export async function SiteFooter() {
  const t = await getTranslations();
  return (
    <footer className="border-t border-border mt-16 py-10 bg-ivory-100">
      <div className="container flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
        <p className="font-display text-base text-navy">{t("brand.name")}</p>
        <p>© {new Date().getFullYear()} Farq Sound. كل الحقوق محفوظة.</p>
        <div className="flex gap-4">
          <a href="/ar" className="hover:text-gold">العربية</a>
          <a href="/en" className="hover:text-gold">English</a>
        </div>
      </div>
    </footer>
  );
}
