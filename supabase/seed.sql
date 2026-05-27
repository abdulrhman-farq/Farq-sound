-- =============================================================
-- Farq Sound — demo catalog seed
-- =============================================================
-- All three entries are ROYALTY-FREE placeholders for the demo
-- build. Replace with licensed material via the admin intake
-- flow before going live.
--
-- `original_text_ar` values below are GENERIC ROLE DESCRIPTORS,
-- not lyrics. They tell the renderer which name slot maps to
-- which segment.
-- =============================================================

insert into songs (
  id, slug, title_ar, title_en, artist_ar, era,
  duration_seconds, preview_url, full_original_url,
  instrumental_url, isolated_vocals_url,
  voice_model_id, voice_engine, bpm, key,
  cover_image_url, rights_status, is_active, price_sar
) values
(
  '11111111-1111-1111-1111-111111111111',
  'demo-classic-1',
  'زفّة الفجر',
  'Demo Classic 1',
  'فنان تجريبي',
  'classic',
  180,
  '/samples/preview-demo-1.mp3',
  '/internal/full-demo-1.mp3',
  '/internal/instrumental-demo-1.wav',
  '/internal/vocals-demo-1.wav',
  'mock-voice-classic-1',
  'mock',
  92,
  'D minor',
  '/covers/demo-classic-1.jpg',
  'public_domain',
  true,
  49
),
(
  '22222222-2222-2222-2222-222222222222',
  'demo-classic-2',
  'زفّة العائلة',
  'Demo Classic 2',
  'فنان تجريبي',
  'classic',
  210,
  '/samples/preview-demo-2.mp3',
  '/internal/full-demo-2.mp3',
  '/internal/instrumental-demo-2.wav',
  '/internal/vocals-demo-2.wav',
  'mock-voice-classic-2',
  'mock',
  88,
  'A minor',
  '/covers/demo-classic-2.jpg',
  'public_domain',
  true,
  59
),
(
  '33333333-3333-3333-3333-333333333333',
  'demo-modern-1',
  'زفّة الحديثة',
  'Demo Modern 1',
  'فنان تجريبي',
  'modern',
  165,
  '/samples/preview-demo-3.mp3',
  '/internal/full-demo-3.mp3',
  '/internal/instrumental-demo-3.wav',
  '/internal/vocals-demo-3.wav',
  'mock-voice-modern-1',
  'mock',
  104,
  'G major',
  '/covers/demo-modern-1.jpg',
  'public_domain',
  true,
  69
)
on conflict (id) do nothing;

-- Demo Classic 1: groom, bride, mother_of_groom
insert into song_segments (song_id, role, sequence_index, start_ms, end_ms, original_text_ar, prosody_note) values
('11111111-1111-1111-1111-111111111111', 'groom',           1, 22000,  24500, '<اسم العريس>',         'sung'),
('11111111-1111-1111-1111-111111111111', 'bride',           2, 41000,  43200, '<اسم العروس>',         'sung'),
('11111111-1111-1111-1111-111111111111', 'mother_of_groom', 3, 96000,  99000, '<اسم أم العريس>',      'elongated')
on conflict do nothing;

-- Demo Classic 2: full family set
insert into song_segments (song_id, role, sequence_index, start_ms, end_ms, original_text_ar, prosody_note) values
('22222222-2222-2222-2222-222222222222', 'groom',            1, 18000,  20800, '<اسم العريس>',         'sung'),
('22222222-2222-2222-2222-222222222222', 'bride',            2, 35000,  37500, '<اسم العروس>',         'sung'),
('22222222-2222-2222-2222-222222222222', 'mother_of_groom',  3, 60000,  62800, '<اسم أم العريس>',      'sung'),
('22222222-2222-2222-2222-222222222222', 'father_of_groom',  4, 82000,  84800, '<اسم والد العريس>',    'sung'),
('22222222-2222-2222-2222-222222222222', 'mother_of_bride',  5, 110000, 112800,'<اسم أم العروس>',      'sung'),
('22222222-2222-2222-2222-222222222222', 'family_name',      6, 160000, 163000,'<اسم العائلة>',        'elongated')
on conflict do nothing;

-- Demo Modern 1: lighter set
insert into song_segments (song_id, role, sequence_index, start_ms, end_ms, original_text_ar, prosody_note) values
('33333333-3333-3333-3333-333333333333', 'groom',  1, 14000,  16200, '<اسم العريس>', 'sung'),
('33333333-3333-3333-3333-333333333333', 'bride',  2, 29000,  31200, '<اسم العروس>', 'sung'),
('33333333-3333-3333-3333-333333333333', 'family_name', 3, 88000, 91000, '<اسم العائلة>', 'elongated')
on conflict do nothing;
