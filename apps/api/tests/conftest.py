"""Pytest configuration — populate env defaults so settings load."""
import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SUPABASE_URL", "https://stub.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "stub")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "stub")
os.environ.setdefault("SUPABASE_JWT_SECRET", "stub" * 8)
os.environ.setdefault("ELEVENLABS_API_KEY", "")
os.environ.setdefault("MOYASAR_API_KEY", "")
