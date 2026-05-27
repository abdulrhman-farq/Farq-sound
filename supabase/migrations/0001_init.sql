-- =============================================================
-- Farq Sound — initial schema
-- =============================================================
-- Run against a Supabase Postgres database. The `auth.users` table
-- is provided by Supabase Auth; we reference it from `profiles`.
-- =============================================================

create extension if not exists "pgcrypto";

-- -----------------------------
-- profiles
-- -----------------------------
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name_ar text,
  phone text unique,
  created_at timestamptz default now()
);

-- -----------------------------
-- songs (catalog)
-- -----------------------------
create table if not exists songs (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  title_ar text not null,
  title_en text,
  artist_ar text,
  era text check (era in ('classic','modern')),
  duration_seconds int,
  preview_url text not null,
  full_original_url text not null,
  instrumental_url text not null,
  isolated_vocals_url text not null,
  voice_model_id text,
  voice_engine text default 'elevenlabs' check (voice_engine in ('elevenlabs','rvc','mock')),
  bpm numeric,
  key text,
  cover_image_url text,
  rights_status text default 'pending' check (rights_status in ('licensed','public_domain','pending')),
  is_active boolean default true,
  price_sar numeric not null default 49,
  created_at timestamptz default now()
);

create index if not exists songs_active_idx on songs (is_active);
create index if not exists songs_era_idx on songs (era);

-- -----------------------------
-- song_segments
-- -----------------------------
create table if not exists song_segments (
  id uuid primary key default gen_random_uuid(),
  song_id uuid not null references songs(id) on delete cascade,
  role text not null check (role in (
    'groom','bride',
    'mother_of_groom','father_of_groom',
    'mother_of_bride','father_of_bride',
    'family_name'
  )),
  sequence_index int not null,
  start_ms int not null,
  end_ms int not null,
  original_text_ar text not null,
  phonetic_hint text,
  prosody_note text check (prosody_note in ('sung','spoken','elongated'))
);

create index if not exists song_segments_seq_idx
  on song_segments (song_id, sequence_index);

-- -----------------------------
-- orders
-- -----------------------------
create table if not exists orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id),
  song_id uuid not null references songs(id),
  names jsonb not null,
  status text not null default 'draft'
    check (status in ('draft','rendering','preview_ready','paid','delivered','failed')),
  preview_url text,
  final_url text,
  share_token text unique,
  whatsapp_sent_at timestamptz,
  amount_sar numeric,
  moyasar_payment_id text,
  error_message text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists orders_user_idx on orders (user_id, created_at desc);
create index if not exists orders_share_idx on orders (share_token);

-- -----------------------------
-- render_jobs
-- -----------------------------
create table if not exists render_jobs (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references orders(id) on delete cascade,
  stage text not null check (stage in ('tts','pitch_match','splice','mixdown','master')),
  status text not null check (status in ('queued','running','done','failed')),
  started_at timestamptz,
  completed_at timestamptz,
  log text
);

create index if not exists render_jobs_order_idx on render_jobs (order_id);

-- -----------------------------
-- catalog_intake (admin)
-- -----------------------------
create table if not exists catalog_intake (
  id uuid primary key default gen_random_uuid(),
  source_audio_url text not null,
  title_ar text,
  asr_transcript jsonb,
  detected_segments jsonb,
  status text default 'awaiting_review'
    check (status in ('awaiting_review','approved','published')),
  reviewer_notes text,
  created_at timestamptz default now()
);

-- -----------------------------
-- updated_at trigger for orders
-- -----------------------------
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists orders_set_updated_at on orders;
create trigger orders_set_updated_at
before update on orders
for each row execute function set_updated_at();

-- -----------------------------
-- Row Level Security
-- -----------------------------
alter table profiles       enable row level security;
alter table orders         enable row level security;
alter table render_jobs    enable row level security;
alter table songs          enable row level security;
alter table song_segments  enable row level security;
alter table catalog_intake enable row level security;

-- profiles: a user can read/write their own row
drop policy if exists "profiles self read"   on profiles;
drop policy if exists "profiles self update" on profiles;
drop policy if exists "profiles self insert" on profiles;
create policy "profiles self read"   on profiles for select using (auth.uid() = id);
create policy "profiles self update" on profiles for update using (auth.uid() = id);
create policy "profiles self insert" on profiles for insert with check (auth.uid() = id);

-- songs / segments: public read for active songs
drop policy if exists "songs public read"     on songs;
drop policy if exists "segments public read"  on song_segments;
create policy "songs public read" on songs
  for select using (is_active = true);
create policy "segments public read" on song_segments
  for select using (
    exists (select 1 from songs s where s.id = song_id and s.is_active = true)
  );

-- orders: a user only sees and mutates their own; share_token row is
-- exposed via a server-side RPC, not a direct SELECT.
drop policy if exists "orders self read"   on orders;
drop policy if exists "orders self insert" on orders;
drop policy if exists "orders self update" on orders;
create policy "orders self read"   on orders for select using (auth.uid() = user_id);
create policy "orders self insert" on orders for insert with check (auth.uid() = user_id);
create policy "orders self update" on orders for update using (auth.uid() = user_id);

-- render_jobs: a user can read jobs that belong to one of their orders
drop policy if exists "render_jobs self read" on render_jobs;
create policy "render_jobs self read" on render_jobs
  for select using (
    exists (select 1 from orders o where o.id = order_id and o.user_id = auth.uid())
  );

-- catalog_intake: admin-only (no policies => only service_role can access)

-- -----------------------------
-- Public share RPC (bypasses RLS via SECURITY DEFINER)
-- -----------------------------
create or replace function public.get_shared_order(token text)
returns table (
  id uuid,
  song_id uuid,
  names jsonb,
  final_url text,
  song_title_ar text,
  song_cover_image_url text
)
language sql
security definer
set search_path = public
as $$
  select o.id, o.song_id, o.names, o.final_url,
         s.title_ar, s.cover_image_url
    from orders o
    join songs s on s.id = o.song_id
   where o.share_token = token
     and o.status = 'delivered';
$$;

grant execute on function public.get_shared_order(text) to anon, authenticated;
