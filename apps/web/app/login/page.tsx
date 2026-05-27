"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { supabaseBrowser } from "@/lib/api";

export default function LoginPage() {
  const t = useTranslations();
  const supabase = supabaseBrowser();
  const [phone, setPhone] = useState("+9665");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  const sendOtp = async () => {
    setWorking(true);
    setError("");
    const { error } = await supabase.auth.signInWithOtp({ phone });
    setWorking(false);
    if (error) setError(error.message);
    else setStep("otp");
  };

  const verifyOtp = async () => {
    setWorking(true);
    setError("");
    const { error } = await supabase.auth.verifyOtp({
      phone,
      token: otp,
      type: "sms",
    });
    setWorking(false);
    if (error) return setError(error.message);
    window.location.assign("/songs");
  };

  return (
    <div className="container py-16 max-w-md">
      <h1 className="font-display text-3xl mb-2">{t("nav.login")}</h1>
      <p className="text-muted-foreground mb-8">
        نرسلك رمز تحقق عبر SMS — جوالك بصيغة +9665XXXXXXXX.
      </p>

      {step === "phone" ? (
        <>
          <label className="label" htmlFor="phone">رقم الجوال</label>
          <input
            id="phone"
            type="tel"
            dir="ltr"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="input"
          />
          <button
            type="button"
            onClick={sendOtp}
            disabled={working}
            className="btn-primary w-full mt-6"
          >
            {working ? t("common.loading") : "إرسال الرمز"}
          </button>
        </>
      ) : (
        <>
          <label className="label" htmlFor="otp">الرمز</label>
          <input
            id="otp"
            type="text"
            inputMode="numeric"
            dir="ltr"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            className="input tracking-widest text-center text-2xl"
          />
          <button
            type="button"
            onClick={verifyOtp}
            disabled={working}
            className="btn-accent w-full mt-6"
          >
            {working ? t("common.loading") : "دخول"}
          </button>
        </>
      )}

      {error && <p className="text-red-600 mt-4 text-sm">{error}</p>}
    </div>
  );
}
