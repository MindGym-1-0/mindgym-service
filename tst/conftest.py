"""Pytest configuration: test env defaults."""

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