"""Integration smoke test for the real session flow.

These tests intentionally use real Supabase and Gemini credentials from `.env`.
Run them manually with:

    pytest tst/integration/test_sessions_flow.py -q
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)


def _real_env_value(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    value = value.strip()
    if not value or value.startswith("test-") or value == "https://test.supabase.co":
        return None
    return value


def _require_integration_env() -> None:
    missing = [
        name
        for name in (
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "SUPABASE_SERVICE_ROLE_KEY",
            "GEMINI_API_KEY",
        )
        if not _real_env_value(name)
    ]
    if missing:
        pytest.skip(f"Missing real integration env vars: {', '.join(missing)}")


@pytest.fixture()
def integration_app():
    """Import the app after real `.env` values have been loaded."""
    _require_integration_env()

    from src.lib.config import get_settings
    from src.lib.supabase_client import (
        get_supabase_admin_client,
        get_supabase_client,
    )

    get_settings.cache_clear()
    get_supabase_client.cache_clear()
    get_supabase_admin_client.cache_clear()

    from src.main import app

    return app


@pytest.fixture()
def admin_client(integration_app):
    """Return a service-role Supabase client for setup and cleanup."""
    from src.lib.supabase_client import get_supabase_admin_client

    client = get_supabase_admin_client()
    if client is None:
        pytest.skip("SUPABASE_SERVICE_ROLE_KEY is required for integration tests")
    return client


@pytest.fixture()
def test_user(admin_client) -> dict[str, Any]:
    """Create an auth user plus matching public.users profile, then clean up."""
    email = f"mindgym-it-{uuid.uuid4().hex}@example.com"
    password = f"MindGym-{uuid.uuid4().hex}!1"

    created = admin_client.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
        }
    )
    user = created.user
    user_id = str(user.id)

    admin_client.table("users").upsert(
        {
            "id": user_id,
            "goal": "Land a senior product manager role",
            "stage": "interviewing",
        }
    ).execute()

    try:
        yield {"id": user_id, "email": email}
    finally:
        admin_client.auth.admin.delete_user(user_id)


@pytest.fixture()
def other_test_user(admin_client) -> dict[str, Any]:
    """Create a second auth user for ownership/isolation checks."""
    email = f"mindgym-it-other-{uuid.uuid4().hex}@example.com"
    password = f"MindGym-{uuid.uuid4().hex}!1"

    created = admin_client.auth.admin.create_user(
        {
            "email": email,
            "password": password,
            "email_confirm": True,
        }
    )
    user = created.user
    user_id = str(user.id)

    admin_client.table("users").upsert(
        {
            "id": user_id,
            "goal": "Find a new design leadership role",
            "stage": "exploring",
        }
    ).execute()

    try:
        yield {"id": user_id, "email": email}
    finally:
        admin_client.auth.admin.delete_user(user_id)


@pytest.fixture()
def client(integration_app, test_user):
    """Use the real FastAPI app while pinning auth to the temporary test user."""
    from src.lib.auth_dependencies import get_current_user

    integration_app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        yield TestClient(integration_app)
    finally:
        integration_app.dependency_overrides.clear()


@pytest.mark.integration
def test_session_happy_path_real_supabase_real_gemini(client, admin_client, test_user):
    """Start, complete, list, and replay one real session.

    Flow covered by this test:
    1. create temporary Supabase auth user
    2. create matching public.users profile
    3. call POST /api/sessions/start with real Gemini
    4. verify ai_sessions row was saved
    5. call POST /api/sessions/complete
    6. verify anxiety_level_after, anxiety_level_delta, completed_at
    7. call GET /api/sessions/history
    8. call GET /api/sessions/{session_id}
    9. cleanup test auth user
    """
    start_payload = {
        "preparation_for": "interview_tomorrow",
        "current_feeling": "overwhelmed",
        "desired_feeling": ["confident"],
        "time_available": "5 min",
        "anxiety_level_before": 2,
        "company": "Stripe",
        "role": "Product Manager",
    }

    start_response = client.post("/api/sessions/start", json=start_payload)
    assert start_response.status_code == 201, start_response.text
    start_body = start_response.json()

    session_id = start_body["session_id"]
    script = start_body["script"]
    assert start_body["mode"] == "interview_tomorrow"
    assert set(script) == {"phase1", "phase2", "phase3", "phase4", "phase5"}
    assert all(script[phase].strip() for phase in script)

    saved = (
        admin_client.table("ai_sessions")
        .select(
            "id, user_id, preparation_for, company, role, anxiety_level_before, "
            "phase1, phase2, phase3, phase4, phase5"
        )
        .eq("id", session_id)
        .maybe_single()
        .execute()
    ).data
    assert saved is not None
    assert saved["user_id"] == test_user["id"]
    assert saved["company"] == "Stripe"
    assert saved["role"] == "Product Manager"
    assert saved["phase1"] == script["phase1"]

    complete_response = client.post(
        "/api/sessions/complete",
        json={"session_id": session_id, "anxiety_level_after": 7},
    )
    assert complete_response.status_code == 200, complete_response.text
    complete_body = complete_response.json()
    assert complete_body["anxiety_level_before"] == 2
    assert complete_body["anxiety_level_after"] == 7
    assert complete_body["anxiety_level_delta"] == 5

    updated = (
        admin_client.table("ai_sessions")
        .select("anxiety_level_after, anxiety_level_delta, completed_at")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    ).data
    assert updated is not None
    assert updated["anxiety_level_after"] == 7
    assert updated["anxiety_level_delta"] == 5
    assert updated["completed_at"] is not None

    history_response = client.get("/api/sessions/history")
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert any(item["id"] == session_id for item in history)

    detail_response = client.get(f"/api/sessions/{session_id}")
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["id"] == session_id
    assert detail["script"]["phase1"] == script["phase1"]


@pytest.mark.integration
def test_start_session_uses_fallback_when_gemini_returns_none(
    client, admin_client, test_user
):
    """Force Gemini failure and verify the fallback script is returned and saved.

    Flow covered by this test:
    1. create temporary Supabase auth user
    2. create matching public.users profile
    3. force generate_script() to return None
    4. call POST /api/sessions/start
    5. verify response still contains a 5-phase script
    6. verify ai_sessions row was saved with fallback phase text
    7. cleanup test auth user
    """
    start_payload = {
        "preparation_for": "interview_tomorrow",
        "current_feeling": "overwhelmed",
        "desired_feeling": ["confident"],
        "time_available": "5 min",
        "anxiety_level_before": 2,
        "company": "Stripe",
        "role": "Product Manager",
    }

    with patch("src.lib.session_service.generate_script", return_value=None):
        start_response = client.post("/api/sessions/start", json=start_payload)

    assert start_response.status_code == 201, start_response.text
    start_body = start_response.json()

    session_id = start_body["session_id"]
    script = start_body["script"]
    assert set(script) == {"phase1", "phase2", "phase3", "phase4", "phase5"}
    assert all(script[phase].strip() for phase in script)
    assert "Stripe" in script["phase3"]
    assert "Product Manager" in script["phase5"]

    saved = (
        admin_client.table("ai_sessions")
        .select("id, user_id, phase1, phase2, phase3, phase4, phase5")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    ).data
    assert saved is not None
    assert saved["user_id"] == test_user["id"]
    assert saved["phase1"] == script["phase1"]
    assert saved["phase2"] == script["phase2"]
    assert saved["phase3"] == script["phase3"]
    assert saved["phase4"] == script["phase4"]
    assert saved["phase5"] == script["phase5"]


@pytest.mark.integration
def test_user_cannot_view_or_complete_another_users_session(
    client, other_test_user
):
    """Verify one user cannot replay or complete another user's session.

    Flow covered by this test:
    1. create temporary User A
    2. create temporary User B
    3. User A starts a session
    4. switch request auth to User B
    5. User B calls GET /api/sessions/{session_id}
    6. API returns 404
    7. User B calls POST /api/sessions/complete for User A's session
    8. API returns 404
    9. cleanup both test users
    """
    from src.lib.auth_dependencies import get_current_user

    start_payload = {
        "preparation_for": "interview_tomorrow",
        "current_feeling": "overwhelmed",
        "desired_feeling": ["confident"],
        "time_available": "5 min",
        "anxiety_level_before": 2,
        "company": "Stripe",
        "role": "Product Manager",
    }

    start_response = client.post("/api/sessions/start", json=start_payload)
    assert start_response.status_code == 201, start_response.text
    session_id = start_response.json()["session_id"]

    client.app.dependency_overrides[get_current_user] = lambda: other_test_user

    detail_response = client.get(f"/api/sessions/{session_id}")
    assert detail_response.status_code == 404, detail_response.text

    complete_response = client.post(
        "/api/sessions/complete",
        json={"session_id": session_id, "anxiety_level_after": 7},
    )
    assert complete_response.status_code == 404, complete_response.text


@pytest.mark.integration
def test_event_specific_session_requires_company_and_role(client):
    """Verify backend validation rejects incomplete event-specific sessions.

    Flow covered by this test:
    1. create temporary Supabase auth user
    2. create matching public.users profile
    3. call POST /api/sessions/start for interview_tomorrow without company/role
    4. API returns 422 before Gemini or ai_sessions persistence
    5. cleanup test auth user
    """
    start_payload = {
        "preparation_for": "interview_tomorrow",
        "current_feeling": "overwhelmed",
        "desired_feeling": ["confident"],
        "time_available": "5 min",
        "anxiety_level_before": 2,
    }

    response = client.post("/api/sessions/start", json=start_payload)
    assert response.status_code == 422, response.text


@pytest.mark.integration
def test_missing_session_returns_404_for_detail_and_complete(client):
    """Verify missing sessions produce clean 404 responses.

    Flow covered by this test:
    1. create temporary Supabase auth user
    2. create matching public.users profile
    3. call GET /api/sessions/{fake_session_id}
    4. API returns 404
    5. call POST /api/sessions/complete for the same fake session
    6. API returns 404
    7. cleanup test auth user
    """
    fake_session_id = str(uuid.uuid4())

    detail_response = client.get(f"/api/sessions/{fake_session_id}")
    assert detail_response.status_code == 404, detail_response.text

    complete_response = client.post(
        "/api/sessions/complete",
        json={"session_id": fake_session_id, "anxiety_level_after": 7},
    )
    assert complete_response.status_code == 404, complete_response.text


@pytest.mark.integration
def test_patch_user_me_updates_only_provided_profile_fields(
    client, admin_client, test_user
):
    """Verify PATCH /api/users/me updates only fields provided in the body.

    Flow covered by this test:
    1. create temporary Supabase auth user
    2. create matching public.users profile
    3. call PATCH /api/users/me with only goal
    4. verify users.goal changed
    5. verify users.stage stayed the same
    6. cleanup test auth user
    """
    response = client.patch(
        "/api/users/me",
        json={"goal": "Land a principal product manager role"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"updated": True}

    profile = (
        admin_client.table("users")
        .select("goal, stage")
        .eq("id", test_user["id"])
        .maybe_single()
        .execute()
    ).data

    assert profile is not None
    assert profile["goal"] == "Land a principal product manager role"
    assert profile["stage"] == "interviewing"
