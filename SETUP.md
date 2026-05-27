# Farq Sound — Setup & Deployment Guide

دليل تشغيل المنصة من الصفر — من البيئة المحلية لين النشر الإنتاجي.

---

## ١. التشغيل المحلي (٥ دقايق)

### المتطلبات (مرّة وحدة)

```bash
# لينكس / WSL
sudo apt install -y ffmpeg rubberband-cli libsndfile1 redis-server

# ماك
brew install ffmpeg rubber-band libsndfile redis

# عام
# Node 20+ و pnpm 9+
node --version && pnpm --version
# Python 3.11+
python3 --version
```

### أول مرّة فقط

```bash
git clone <repo> && cd Farq-sound

# Web
pnpm install

# API
python3 -m venv apps/api/.venv
source apps/api/.venv/bin/activate
pip install -r apps/api/requirements.txt

# Generate placeholder audio for the 3 demo songs
python apps/api/assets/make_demo_audio.py

# Optional — bring up local Supabase (Studio + Auth + Storage + Postgres)
# Needs the supabase CLI: https://supabase.com/docs/guides/cli
supabase start
psql "postgres://postgres:postgres@localhost:54322/postgres" \
  -f supabase/migrations/0001_init.sql \
  -f supabase/migrations/0002_profile_autocreate.sql \
  -f supabase/seed.sql
```

### كل مرّة

```bash
./infra/local-up.sh
```

تطلع:
- **Web** → http://localhost:3000
- **API** → http://localhost:8000/health
- **Supabase Studio** → http://localhost:54323 (لو شغّلت `supabase start`)

`Ctrl+C` يوقف كل شي بأمان.

> **بدون أي keys** كل شي يشتغل بوضع المحاكاة (`mock`). تقدر تتصفّح الكتالوج، تكمّل ويزرد الأسامي، وتستلم MP3 بصوت تجريبي.

---

## ٢. النشر الإنتاجي (Production)

### الخدمات اللي تحتاجها

| الخدمة | الغرض | السعر التقريبي |
|---|---|---|
| **Supabase** (Pro) | DB + Auth + Storage | $25/شهر |
| **ElevenLabs** (Creator أو Pro) | استنساخ الصوت | $22-$99/شهر |
| **Moyasar** | الدفع | ٢.٧٥٪ + ١ ر.س لكل عملية |
| **WhatsApp Cloud API** | تسليم الرابط | مجاني لأول ١٠٠٠ محادثة/شهر |
| **Vercel** (Pro) | استضافة الويب | $20/شهر |
| **Railway** أو **Fly.io** | API + Worker | $15-30/شهر |
| **Resend** (اختياري) | إيميل احتياطي | مجاني لأول ٣٠٠٠/شهر |
| **Sentry** (اختياري) | مراقبة الأخطاء | مجاني tier |

**إجمالي تقريبي للبداية:** ~$80-150/شهر + ٢.٧٥٪ من كل عملية.

---

### الخطوة ١ — Supabase

١. أنشئ مشروع جديد في https://supabase.com/dashboard
٢. خذ من **Settings → API**: `URL` + `anon key` + `service_role key`
٣. خذ من **Settings → API → JWT Settings**: `JWT Secret`
٤. خذ من **Settings → Database**: connection string
٥. طبّق الـ migrations:

```bash
psql "$DATABASE_URL" \
  -f supabase/migrations/0001_init.sql \
  -f supabase/migrations/0002_profile_autocreate.sql \
  -f supabase/seed.sql
```

٦. **Storage**: أنشئ bucket باسم `farq-sound`، خاص (private)
٧. **Auth → Providers**: فعّل Phone (SMS). للسعودية اربط `Unifonic` أو `Twilio` (Saudi number)
٨. **Auth → URL Configuration**: 
   - Site URL: `https://farqsound.sa`
   - Redirect URLs: `https://farqsound.sa/**`

٩. **عيّن نفسك أدمن** (مرّة وحدة):
```sql
update auth.users
   set raw_app_meta_data = jsonb_set(
     coalesce(raw_app_meta_data, '{}'::jsonb),
     '{role}', '"admin"'
   )
 where email = 'you@example.com';
```

---

### الخطوة ٢ — ElevenLabs

١. اشترك بباقة Creator على الأقل (للـ Instant Voice Clone) — أو Pro لو تبي Professional Voice Clone
٢. أنشئ API key من **Profile → API Keys**
٣. خزّن المفتاح في env متغير `ELEVENLABS_API_KEY`

**ما تحط المفتاح في أي ملف يُلتزم بالـ git.**

---

### الخطوة ٣ — Moyasar

١. سجّل حساب تاجر على https://moyasar.com
٢. خذ **Secret API key** من Dashboard → Developers
٣. خذ **Publishable API key** (للفرونت)
٤. أنشئ webhook على: `https://api.farqsound.sa/api/webhooks/moyasar`
٥. احفظ الـ webhook secret
٦. فعّل: mada, Apple Pay, STC Pay

---

### الخطوة ٤ — WhatsApp Cloud API

١. أنشئ Meta Developer App: https://developers.facebook.com
٢. أضف WhatsApp product، خذ `Phone Number ID` و `Access Token`
٣. أنشئ template approved اسمه `farq_sound_delivery` بالعربي:

```
مبروك {{1}}! زفّتكم الخاصة جاهزة 🎉

حمّلوها من هنا: {{2}}
```

٤. احفظ الـ template name + IDs

---

### الخطوة ٥ — نشر الويب (Vercel)

```bash
cd apps/web
vercel link
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel env add NEXT_PUBLIC_API_BASE_URL production
vercel env add NEXT_PUBLIC_BRAND_NAME production
vercel env add NEXT_PUBLIC_BRAND_NAME_AR production
vercel --prod
```

أو من Dashboard: اربط GitHub repo → Root directory: `apps/web` → نفس متغيرات البيئة.

اربط domain: `farqsound.sa` → اتبع تعليمات Vercel للـ DNS.

---

### الخطوة ٦ — نشر الـ API + Worker (Render — موصى به)

`infra/render.yaml` فيه Blueprint جاهز ينشر:
- **farq-sound-api** (FastAPI، HTTP، فيه healthcheck)
- **farq-sound-worker** (Celery، خلفية)
- **farq-redis** (Managed Redis، شبكة خاصة)

**خطوات النشر** (٥ دقايق):

1. ادخلي https://dashboard.render.com → **New** → **Blueprint**
2. اربطي GitHub، اختاري repo `Farq-sound`، Branch: `main` (أو الفرع اللي تنشرين منه)
3. Render يقرأ `infra/render.yaml` تلقائياً ويعرض الـ ٣ خدمات
4. اضغطي **Apply** — بيبدأ بناء كل شي
5. بعد ما تطلع الخدمات "Live":
   - افتحي `farq-sound-api` → **Environment** → عبّي القيم `sync: false`:
     - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
     - `ELEVENLABS_API_KEY` (لو متوفّر)
     - `APP_BASE_URL` = رابط Vercel (من الخطوة الجاية)
     - `API_BASE_URL` = `https://farq-sound-api.onrender.com`
   - نفس الشي لـ `farq-sound-worker` (Supabase + ElevenLabs)
6. بعد عبّي المتغيّرات، Render يعيد النشر تلقائياً
7. اختبري: `https://farq-sound-api.onrender.com/health` لازم يرجع `200 OK` مع `"tts": "live"` لو ElevenLabs مظبوط

**ملاحظات Render مهمّة:**
- `Starter` plan: $7/شهر للـ web، $7/شهر للـ worker، $10/شهر للـ Redis = **~$24/شهر**
- خطّة الـ Free تشتغل لكن تنام بعد ١٥ دقيقة من الخمول — مش مناسبة للإنتاج
- المنطقة `frankfurt` هي الأقرب للسعودية (~٨٠ms latency)

**بدائل** (لو تفضّلين منصّة ثانية):

- **Railway** → `infra/railway.json` + `railway.worker.json`
- **Fly.io** → `infra/fly.toml` + `fly.worker.toml`

---

### الخطوة ٧ — DNS + Domain

| Subdomain | يشير إلى |
|---|---|
| `farqsound.sa` | Vercel (web) |
| `www.farqsound.sa` | Vercel (web) |
| `api.farqsound.sa` | Railway/Fly (api) |

---

## ٣. إدخال أول زفّة حقيقية

بعد ما تنشر، تحتاج زفّة وحدة على الأقل في الكتالوج:

١. احصل على ترخيص من صاحب الزفّة (المنشد + شركة الإنتاج)
٢. شغّل Demucs على الملف الأصلي:
   ```bash
   pip install demucs
   demucs --two-stems vocals original.mp3
   # يطلع: separated/htdemucs/<name>/{vocals,no_vocals}.wav
   ```
٣. ارفع الملفات لـ Supabase Storage `farq-sound/songs/<slug>/`:
   - `vocals.wav` (من Demucs)
   - `instrumental.wav` (`no_vocals.wav` من Demucs)
   - `preview.mp3` (٣٠ ثانية تعريفية)
   - `cover.jpg`

٤. ادخل `/admin` كأدمن → "New intake"
٥. ارفع `vocals.wav` → اضغط "درّبي الصوت" → انسخ الـ `voice_id`
٦. راجع المقاطع المكتشفة (start_ms / end_ms / role لكل اسم في الزفّة)
٧. اضغط Publish — مع لصق الـ `voice_id`

أو SQL مباشر لو تستعجل:

```sql
insert into songs (slug, title_ar, artist_ar, era, voice_model_id, voice_engine,
                   preview_url, full_original_url, instrumental_url, isolated_vocals_url,
                   cover_image_url, rights_status, price_sar)
values (
  'my-first-song', 'عنوان الزفّة', 'اسم المنشد', 'classic',
  '<voice_id_من_elevenlabs>', 'elevenlabs',
  'https://<project>.supabase.co/storage/v1/object/sign/farq-sound/songs/my-first-song/preview.mp3',
  '...full.mp3', '...instrumental.wav', '...vocals.wav',
  '...cover.jpg', 'licensed', 49
);

insert into song_segments (song_id, role, sequence_index, start_ms, end_ms,
                           original_text_ar, prosody_note)
values
  ((select id from songs where slug = 'my-first-song'),
   'groom', 1, 22000, 24500, '<اسم العريس>', 'sung');
```

---

## ٤. اختبار end-to-end بعد النشر

```bash
# ١. تأكد إن الـ API يرجع live providers (مش mock)
curl https://api.farqsound.sa/health
# توقع: { "providers": { "tts": "live", "payments": "live", ... } }

# ٢. سجّل دخول من /login بجوالك
# ٣. اطلب زفّة، اكتب أسامي، شوف المعاينة
# ٤. ادفع بكرت اختبار (Moyasar test mode)
# ٥. شوف وصول رسالة واتساب مع رابط التحميل
```

---

## ٥. التشخيص والمشاكل الشائعة

### `/api/songs` يرجع 500

- تأكد إن `SUPABASE_URL` + `SUPABASE_ANON_KEY` صحيحة
- تأكد إن RLS policies مطبّقة (`0001_init.sql`)

### المعاينة ما تخلص (status = `rendering` للأبد)

- شوف لوقز الـ worker: `railway logs --service worker` أو `fly logs -a farq-sound-worker`
- الأرجح: ffmpeg مش متوفّر في صورة الـ worker — تأكد إنك تستخدم `Dockerfile.worker`

### ElevenLabs يرجع 401

- المفتاح منتهي أو ملغي — أنشئ جديد + ضع `ELEVENLABS_API_KEY` في الـ env

### الـ pitch match يطلع نشاز

- معناه الـ TTS بعيد جداً عن نغمة المنشد. خفّض `style` في `voice_settings` لـ `0.2`، أو وسّع نطاق الـ `pitch_shift` في `pipeline.py` (لكن انتبه — أكثر من ±3 أنصاف نغمات تطلع artifacts).

### الـ webhook ما يستجيب

- تأكد إن signature secret في Moyasar = `MOYASAR_WEBHOOK_SECRET` في env
- شغّل `curl -X POST` يدوياً على endpoint ك`/api/webhooks/moyasar` للتجربة

---

## ٦. CI

GitHub Actions يشتغل تلقائياً على كل PR:
- Web: typecheck + build
- API: ruff + unit tests + integration tests (يولّد عيّنات ويختبر السلسلة كاملة)

شوف `.github/workflows/ci.yml`.

---

## مرجع متغيرات البيئة

كلها موجودة في `.env.example`. **اللي ضروري للإنتاج:**

```bash
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
REDIS_URL=...
ELEVENLABS_API_KEY=...
MOYASAR_API_KEY=...
MOYASAR_WEBHOOK_SECRET=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
APP_BASE_URL=https://farqsound.sa
API_BASE_URL=https://api.farqsound.sa
```

---

أي خطوة عالقة، افتح issue أو راجع `BRIEF.ar.md` للمواصفة الكاملة.
