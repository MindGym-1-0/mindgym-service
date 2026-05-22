from functools import lru_cache

from supabase import Client, create_client

from src.lib.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Create and cache a Supabase client for reuse across requests."""

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError('SUPABASE_URL and SUPABASE_ANON_KEY must be configured')
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_admin_client() -> Client | None:
    """Create a Supabase admin-capable client when service role key is configured."""

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None

    return create_client(settings.supabase_url, settings.supabase_service_role_key)
