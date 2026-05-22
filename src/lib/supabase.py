"""Supabase integration helpers."""
from __future__ import annotations

from typing import Any

import httpx

from src.lib.config import settings


async def insert_onboarding_record(record: dict[str, Any]) -> dict[str, Any]:
    """Persist an onboarding record to Supabase using the REST API."""
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError(
            "Supabase URL and key are required to persist onboarding records"
        )

    url = f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.supabase_onboarding_table}"
    headers = {
        "apikey": settings.supabase_key,
        "Authorization": f"Bearer {settings.supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=record, headers=headers)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data[0] if data else {}
        return data
