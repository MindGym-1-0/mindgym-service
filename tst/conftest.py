"""Pytest configuration: test env defaults and Supabase client cache resets."""

from __future__ import annotations

import os


def _ensure_test_env() -> None:
    if not os.getenv("SUPABASE_URL", "").strip():
        os.environ["SUPABASE_URL"] = "https://test.supabase.co"
    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip():
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
    if not os.getenv("SUPABASE_ANON_KEY", "").strip():
        os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"


_ensure_test_env()

import pytest

from src.lib.supabase import clear_supabase_client_cache


@pytest.fixture(autouse=True)
def reset_supabase_cache():
    clear_supabase_client_cache()
    yield
    clear_supabase_client_cache()
