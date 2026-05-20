from __future__ import annotations

from supabase import Client, create_client

from src.lib import config


def get_supabase_user_client(token: str) -> Client:
    url = config.supabase_url()
    anon_key = config.supabase_anon_key()
    
    if not url or not anon_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in the environment.")
        
    client = create_client(url, anon_key)
    client.postgrest.auth(token)
    
    return client