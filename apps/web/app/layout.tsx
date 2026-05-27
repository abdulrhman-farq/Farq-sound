import type { Metadata, Viewport } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { Tajawal, Amiri } from "next/font/google";
import { ReactNode } from "react";

import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

import "./globals.css";

const tajawal = Tajawal({
  subsets: ["arabic", "latin"],
  weight: ["300", "400", "500", "700", "900"],
  variable: "--font-arabic",
  display: "swap",
});

const amiri = Amiri({
  subsets: ["arabic", "latin"],
  weight: ["400", "700"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_BASE_URL ?? "http://localhost:3000",
  ),
  title: {
    default: "فرق ساوند — زفّتكم بأساميكم",
    template: "%s · فرق ساوند",
  },
  description:
    "خصّصي زفّة عرسك بأسامي العائلة باستخدام الذكاء الاصطناعي. نسخة معاينة مجانية خلال دقيقة.",
  openGraph: {
    type: "website",
    title: "فرق ساوند",
    description: "زفّتكم بأساميكم",
  },
};

export const viewport: Viewport = {
  themeColor: "#F8F4EC",
  width: "device-width",
  initialScale: 1,
};

// next-intl reads request headers in `getLocale()`, so every page is
// already request-time. Opt out of static rendering globally.
export const dynamic = "force-dynamic";

export default async function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();
  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <html lang={locale} dir={dir} className={`${tajawal.variable} ${amiri.variable}`}>
      <body className="min-h-screen flex flex-col">
        <NextIntlClientProvider messages={messages}>
          <Providers>
            <SiteHeader />
            <main className="flex-1">{children}</main>
            <SiteFooter />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
