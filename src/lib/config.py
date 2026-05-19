"""Load `.env` from repo root and expose configuration."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").strip()


def supabase_anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "").strip()


def supabase_service_role_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


def cors_origins_raw() -> str:
    return os.getenv("CORS_ORIGINS", "").strip()


def auth_api_key() -> str:
    """Value for `apikey` when calling Supabase Auth `/auth/v1/user`."""
    return supabase_anon_key() or supabase_service_role_key()


def cors_origin_list() -> list[str]:
    raw = cors_origins_raw()
    if not raw or raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]
