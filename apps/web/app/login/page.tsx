"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { supabaseBrowser } from "@/lib/api";

function LoginInner() {
  const supabase = supabaseBrowser();
  const router = useRouter();
  const params = useSearchParams();
  const returnTo = params.get("returnTo") || "/songs";

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  const sendCode = async () => {
    if (!supabase) {
      setError("Supabase غير مفعّل — تأكّدي من متغيّرات البيئة في Vercel.");
      return;
    }
    setWorking(true);
    setError("");
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { shouldCreateUser: true },
    });
    setWorking(false);
    if (error) return setError(error.message);
    setStep("code");
  };

  const verifyCode = async () => {
    if (!supabase) return;
    setWorking(true);
    setError("");
    const { error } = await supabase.auth.verifyOtp({
      email,
      token: code.trim(),
      type: "email",
    });
    setWorking(false);
    if (error) return setError(error.message);
    router.push(returnTo);
  };

  return (
    <div className="container py-16 max-w-md">
      <h1 className="font-display text-3xl mb-2">تسجيل الدخول</h1>
      <p className="text-muted-foreground mb-8">
        {step === "email"
          ? "اكتبي إيميلك، نرسلك رمز تحقق ٦ أرقام."
          : `أرسلنا رمز إلى ${email} — افتحي إيميلك والصقي الرمز هنا.`}
      </p>

      {step === "email" ? (
        <>
          <label className="label" htmlFor="email">البريد الإلكتروني</label>
          <input
            id="email"
            type="email"
            dir="ltr"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="input"
          />
          <button
            type="button"
            onClick={sendCode}
            disabled={working || !email.includes("@")}
            className="btn-primary w-full mt-6"
          >
            {working ? "جاري الإرسال…" : "إرسال الرمز"}
          </button>
        </>
      ) : (
        <>
          <label className="label" htmlFor="code">الرمز (٦ أرقام)</label>
          <input
            id="code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            dir="ltr"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="123456"
            className="input tracking-widest text-center text-2xl"
          />
          <button
            type="button"
            onClick={verifyCode}
            disabled={working || code.length < 6}
            className="btn-accent w-full mt-6"
          >
            {working ? "جاري التحقق…" : "دخول"}
          </button>
          <button
            type="button"
            onClick={() => { setStep("email"); setError(""); setCode(""); }}
            className="btn-ghost w-full mt-2 text-sm"
          >
            تغيير الإيميل
          </button>
        </>
      )}

      {error && (
        <p className="text-red-600 mt-4 text-sm" dir="ltr">{error}</p>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="container py-12">جاري التحميل…</p>}>
      <LoginInner />
    </Suspense>
  );
}
