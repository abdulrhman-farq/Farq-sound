# Farq Sound — فرق ساوند

> اختاري زفّتك المفضلة، اكتبي أساميكم، خذي النسخة الخاصة فيكم خلال دقايق.

Farq Sound is an Arabic-first SaaS platform that personalizes traditional
Saudi / Khaleeji wedding songs (زفّات) by replacing the names sung in the
original tracks with the names of the bride, groom, and their families —
using AI voice cloning and pitch-matched splicing.

The catalog is pre-processed once (vocal isolation + name segment
alignment + cloned-singer voice model), so end-user renders complete in
under 60 seconds.

[العربية في الأسفل ↓](#نظرة-عامة-بالعربي)

---

## Tech stack

| Layer | Choice |
|---|---|
| Web | Next.js 14 (App Router), TypeScript strict, Tailwind, shadcn/ui, next-intl, WaveSurfer.js, Framer Motion, TanStack Query, React Hook Form + Zod |
| API | FastAPI (Python 3.11), Pydantic v2 |
| DB / Auth / Storage | Supabase (Postgres + RLS) |
| Queue | Celery + Redis |
| AI / Audio | Demucs, faster-whisper (large-v3), ElevenLabs Multilingual v2 (swappable to RVC v2), librosa / pyrubberband, pydub + ffmpeg |
| Payments | Moyasar (mada, Apple Pay, STC Pay) |
| Notify | WhatsApp Cloud API, Resend |
| Hosting | Vercel (web), Railway / Fly.io (api + workers), Supabase Storage |

## Repo layout

```
apps/
  web/        Next.js 14 app
  api/        FastAPI service + Celery workers
packages/
  types/      Shared TypeScript types (generated from Pydantic)
supabase/
  migrations/ SQL migrations
  seed.sql    Demo catalog seed (royalty-free placeholders)
infra/
  docker-compose.yml
```

## Local setup

Prereqs: Docker, Node 20+, pnpm 9+, Python 3.11+, ffmpeg.

```bash
# 1. clone and install
pnpm install
python -m venv apps/api/.venv
source apps/api/.venv/bin/activate
pip install -r apps/api/requirements.txt

# 2. env
cp .env.example .env
# Fill in Supabase project values. ElevenLabs / Moyasar keys are optional —
# the providers run in deterministic mock mode when keys are absent.

# 3. start infra
docker compose up -d redis

# 4. apply DB
# (Local Supabase or remote — see supabase/README.md)
psql "$DATABASE_URL" -f supabase/migrations/0001_init.sql
psql "$DATABASE_URL" -f supabase/seed.sql

# 5. run apps
pnpm --filter web dev          # http://localhost:3000
uvicorn app.main:app --reload --port 8000 --app-dir apps/api
celery -A app.workers.celery_app worker -l info --workdir apps/api
```

## Provider modes

The TTS and Payment services are behind abstract interfaces. With no API
keys present, they fall back to:

- **TTS (`tts.mock`)** — generates a short silent WAV per segment with
  the requested duration. Lets the rendering pipeline complete end to
  end without burning ElevenLabs credits.
- **Payments (`payments.mock`)** — instantly "approves" any checkout
  with a deterministic fake payment id. Webhook signature verification
  is bypassed in mock mode only.

Drop real `ELEVENLABS_API_KEY` / `MOYASAR_API_KEY` into the env to
switch to live providers automatically.

## Build order (current state)

1. ☑ Monorepo bootstrap (web + api + types + supabase)
2. ☑ Supabase schema, RLS, royalty-free placeholder seed
3. ☑ API skeleton with typed mocks
4. ☑ Frontend skeleton (RTL, Arabic font, brand palette)
5. ☑ Order flow E2E with mock renderer
6. ◯ Real AI pipeline stages — ElevenLabs / pitch-match / splice / mixdown
7. ☑ Moyasar integration (webhook + mock mode)
8. ☑ WhatsApp + email delivery (mock mode)
9. ☑ Admin catalog intake (skeleton)
10. ◯ Polish + Sentry + /health

---

## نظرة عامة بالعربي

**فرق ساوند** منصة سعودية تخصّص زفّات الأعراس باستخدام الذكاء
الاصطناعي. تختارين الزفّة من المعرض، تكتبين أساميكم بالعربي،
وتستلمين النسخة الخاصة بكم خلال دقايق — بنفس صوت المنشد الأصلي.

### كيف تشتغل؟
1. **المعرض** — اختاري زفّة من المعرض (كلاسيك أو حديثة).
2. **الأسامي** — اكتبي اسم العريس، العروس، الأم، الأب… بحسب
   النقاط اللي يذكر فيها أسامي في الزفّة.
3. **المعاينة** — نولّد لك نسخة معاينة مجانية خلال دقيقة.
4. **الدفع** — مدى، آبل باي، STC Pay عبر ميسر.
5. **التسليم** — رابط التحميل يوصلك واتساب وإيميل.

### للمطوّرين
طريقة التشغيل المحلي موضحة في الأعلى. أي مفاتيح API ناقصة — النظام
يشتغل بوضع المحاكاة تلقائياً، تقدرين تختبرين كل الواجهات بدون
استهلاك أي رصيد.
