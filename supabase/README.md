# Supabase

This directory holds SQL migrations and the demo seed.

## Apply against a remote Supabase project

```bash
# 1. Get the connection string from Supabase → Project Settings → Database
export DATABASE_URL="postgres://postgres.<ref>:<password>@<host>:5432/postgres"

# 2. Apply migrations in order
psql "$DATABASE_URL" -f migrations/0001_init.sql
psql "$DATABASE_URL" -f migrations/0002_profile_autocreate.sql

# 3. Seed the demo catalog (royalty-free placeholders)
psql "$DATABASE_URL" -f seed.sql
```

## Storage bucket

Create a bucket named `farq-sound` (matching `SUPABASE_STORAGE_BUCKET`)
with private access. The API uses the service role to upload and
serves audio via short-lived signed URLs.

## Auth: SMS OTP

For Saudi SMS, configure the auth provider to use a regional gateway
(e.g. Twilio with Saudi number, or Unifonic). Set the OTP template to
support Arabic.

## Admin role

Mark admin users by adding a custom claim:

```sql
update auth.users
   set raw_app_meta_data = jsonb_set(
     coalesce(raw_app_meta_data, '{}'::jsonb),
     '{role}',
     '"admin"'
   )
 where email = 'you@example.com';
```

The FastAPI `require_admin` dependency reads this claim from the JWT.
