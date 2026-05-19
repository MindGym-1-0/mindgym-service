"""Supabase service-role client for server-side CRUD after auth."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from src.lib import config


@lru_cache
def get_supabase_service_client() -> Client:
    url = config.supabase_url()
    key = config.supabase_service_role_key()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in the environment.")
    return create_client(url, key)


def clear_supabase_client_cache() -> None:
    get_supabase_service_client.cache_clear()
