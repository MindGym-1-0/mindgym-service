"""E2E tests for complete user journeys — real Gemini, real Supabase, no mocks.

These tests exercise the full stack end-to-end. They are distinct from the
integration tests, which test individual endpoints in isolation. Here we test
multi-step journeys that span multiple features.

Scenarios covered:
  - Full journey: session start → complete → streak increment → streak state
  - Multi-session history ordering (newest first)
  - Mode 2 session (general_reset — no company or role required)
  - Profile update persists and is used in next session
  - Session replay preserves all five phases exactly
  - Mode 1 validation: company and role appear in phase3 and phase5

Prerequisites:
  SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY

Run manually:
    pytest tst/e2e/test_session_flow.py -q -m e2e
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=True)


# ---------------------------------------------------------------------------
# Env guard
# ---------------------------------------------------------------------------

def _real_env_value(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    value = value.strip()
    if not value or value.startswith("test-") or value == "https://test.supabase.co":
        return None
    return value


def _require_e2e_env() -> None:
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
        pytest.skip(f"Missing real env vars for E2E: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def e2e_app():
    """FastAPI app loaded after real .env values are confirmed present."""
    _require_e2e_env()

    from src.lib.config import get_settings
    from src.lib.supabase_client import get_supabase_admin_client, get_supabase_client

    get_settings.cache_clear()
    get_supabase_client.cache_clear()
    get_supabase_admin_client.cache_clear()

    from src.main import app

    return app


@pytest.fixture(scope="module")
def admin_db(e2e_app):
    """Service-role Supabase client for setup and teardown."""
    from src.lib.supabase_client import get_supabase_admin_client

    client = get_supabase_admin_client()
    if client is None:
        pytest.skip("SUPABASE_SERVICE_ROLE_KEY required for E2E tests")
    return client


@pytest.fixture()
def test_user(admin_db) -> Any:
    """Create a real auth user + public.users row, clean up after each test."""
    email = f"mindgym-e2e-{uuid.uuid4().hex}@example.com"
    password = f"MindGym-{uuid.uuid4().hex}!1"

    created = admin_db.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
    })
    user_id = str(created.user.id)

    admin_db.table("users").upsert({
        "id": user_id,
        "goal": "Land a senior product manager role",
        "stage": "interviewing",
    }).execute()

    try:
        yield {"id": user_id, "email": email}
    finally:
        admin_db.auth.admin.delete_user(user_id)


@pytest.fixture()
def api_client(e2e_app, test_user):
    """TestClient with auth pinned to the current test user."""
    from src.lib.auth_dependencies import get_current_user

    e2e_app.dependency_overrides[get_current_user] = lambda: test_user
    try:
        yield TestClient(e2e_app)
    finally:
        e2e_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

_MODE1_PAYLOAD = {
    "preparation_for": "interview_tomorrow",
    "current_feeling": "overwhelmed",
    "desired_feeling": ["confident"],
    "time_available": "10 min",
    "anxiety_level_before": 3,
    "company": "Stripe",
    "role": "Product Manager",
}

_MODE2_PAYLOAD = {
    "preparation_for": "general_reset",
    "current_feeling": "exhausted",
    "desired_feeling": ["calm"],
    "time_available": "5 min",
    "anxiety_level_before": 4,
}

_SCRIPT_PHASES = {"phase1", "phase2", "phase3", "phase4", "phase5"}


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------

@pytest.mark.e2e
def test_session_start_then_complete_then_streak(api_client, admin_db, test_user):
    """Full journey: start → complete → increment streak → read streak state.

    Verifies that real Gemini generates a valid script, Supabase persists it,
    anxiety_level_delta is computed correctly, and the streak service responds to the
    completed session by initialising a streak row.
    """
    start_resp = api_client.post("/api/sessions/start", json=_MODE1_PAYLOAD)
    assert start_resp.status_code == 201, start_resp.text

    body = start_resp.json()
    session_id = body["session_id"]
    script = body["script"]

    assert body["mode"] == "interview_tomorrow"
    assert set(script) == _SCRIPT_PHASES
    assert all(script[p].strip() for p in _SCRIPT_PHASES), "All phases must be non-empty"

    # Verify the row exists in ai_sessions before completion
    saved = (
        admin_db.table("ai_sessions")
        .select("id, user_id, preparation_for, company, role, anxiety_level_before")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    ).data
    assert saved is not None
    assert saved["user_id"] == test_user["id"]
    assert saved["company"] == "Stripe"
    assert saved["role"] == "Product Manager"
    assert saved["anxiety_level_before"] == 3

    # Complete the session
    complete_resp = api_client.post(
        "/api/sessions/complete",
        json={"session_id": session_id, "anxiety_level_after": 8},
    )
    assert complete_resp.status_code == 200, complete_resp.text
    complete_body = complete_resp.json()
    assert complete_body["anxiety_level_before"] == 3
    assert complete_body["anxiety_level_after"] == 8
    assert complete_body["anxiety_level_delta"] == 5

    # Verify anxiety_level_delta persisted to ai_sessions
    updated = (
        admin_db.table("ai_sessions")
        .select("anxiety_level_after, anxiety_level_delta, completed_at")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    ).data
    assert updated["anxiety_level_after"] == 8
    assert updated["anxiety_level_delta"] == 5
    assert updated["completed_at"] is not None

    # Increment streak — first action of the day creates the streak row
    streak_resp = api_client.post("/api/streaks/increment")
    assert streak_resp.status_code == 200, streak_resp.text
    streak_body = streak_resp.json()
    assert streak_body["current_streak"] == 1
    assert streak_body["longest_streak"] == 1

    # Read streak state via GET
    get_streak_resp = api_client.get(f"/api/streaks/{test_user['id']}")
    assert get_streak_resp.status_code == 200, get_streak_resp.text
    assert get_streak_resp.json()["current_streak"] == 1


@pytest.mark.e2e
def test_multiple_sessions_history_is_newest_first(api_client):
    """Two sessions completed in sequence — history must return newest first.

    Starts and completes session A, then session B.
    Verifies GET /api/sessions/history returns B before A.
    """
    resp_a = api_client.post("/api/sessions/start", json=_MODE1_PAYLOAD)
    assert resp_a.status_code == 201, resp_a.text
    session_a_id = resp_a.json()["session_id"]

    api_client.post(
        "/api/sessions/complete",
        json={"session_id": session_a_id, "anxiety_level_after": 6},
    )

    resp_b = api_client.post("/api/sessions/start", json=_MODE1_PAYLOAD)
    assert resp_b.status_code == 201, resp_b.text
    session_b_id = resp_b.json()["session_id"]

    api_client.post(
        "/api/sessions/complete",
        json={"session_id": session_b_id, "anxiety_level_after": 9},
    )

    history_resp = api_client.get("/api/sessions/history")
    assert history_resp.status_code == 200, history_resp.text
    history = history_resp.json()

    ids = [item["id"] for item in history]
    assert session_a_id in ids and session_b_id in ids
    assert ids.index(session_b_id) < ids.index(session_a_id), (
        "session B was completed after A and must appear first"
    )


@pytest.mark.e2e
def test_mode2_session_general_reset_full_flow(api_client):
    """Mode 2 (general_reset) — no company or role required.

    Starts a general_reset session, completes it, then verifies the detail
    endpoint returns the session with company=None, role=None, and all five
    phases populated by real Gemini output.
    """
    start_resp = api_client.post("/api/sessions/start", json=_MODE2_PAYLOAD)
    assert start_resp.status_code == 201, start_resp.text
    body = start_resp.json()
    session_id = body["session_id"]
    assert body["mode"] == "general_reset"
    assert set(body["script"]) == _SCRIPT_PHASES
    assert all(body["script"][p].strip() for p in _SCRIPT_PHASES)

    complete_resp = api_client.post(
        "/api/sessions/complete",
        json={"session_id": session_id, "anxiety_level_after": 7},
    )
    assert complete_resp.status_code == 200, complete_resp.text
    assert complete_resp.json()["anxiety_level_delta"] == 3  # 7 - 4

    detail_resp = api_client.get(f"/api/sessions/{session_id}")
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["company"] is None
    assert detail["role"] is None
    assert set(detail["script"]) == _SCRIPT_PHASES

    history_resp = api_client.get("/api/sessions/history")
    assert any(item["id"] == session_id for item in history_resp.json())


@pytest.mark.e2e
def test_profile_update_persists_before_next_session(api_client, admin_db, test_user):
    """PATCH /api/users/me updates the users row that session_service reads.

    Updates the user's goal, then starts a new session and verifies:
      - The users table was updated in Supabase
      - The session still generates successfully (no regression from profile change)
    """
    patch_resp = api_client.patch(
        "/api/users/me",
        json={"goal": "Become a principal PM at a Series B startup"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json() == {"updated": True}

    profile = (
        admin_db.table("users")
        .select("goal, stage")
        .eq("id", test_user["id"])
        .maybe_single()
        .execute()
    ).data
    assert profile["goal"] == "Become a principal PM at a Series B startup"
    assert profile["stage"] == "interviewing"  # unchanged

    # Session generation must still work after the profile update
    start_resp = api_client.post("/api/sessions/start", json=_MODE1_PAYLOAD)
    assert start_resp.status_code == 201, start_resp.text
    body = start_resp.json()
    assert set(body["script"]) == _SCRIPT_PHASES
    assert all(body["script"][p].strip() for p in _SCRIPT_PHASES)


@pytest.mark.e2e
def test_session_replay_preserves_all_five_phases_exactly(api_client):
    """GET /api/sessions/{id} returns the exact script written at creation time.

    Captures all five phase strings from the start response and verifies they
    are returned unchanged by the detail endpoint after completion.
    """
    start_resp = api_client.post("/api/sessions/start", json=_MODE1_PAYLOAD)
    assert start_resp.status_code == 201, start_resp.text
    start_body = start_resp.json()
    session_id = start_body["session_id"]
    created_script = start_body["script"]

    api_client.post(
        "/api/sessions/complete",
        json={"session_id": session_id, "anxiety_level_after": 8},
    )

    detail_resp = api_client.get(f"/api/sessions/{session_id}")
    assert detail_resp.status_code == 200, detail_resp.text
    replayed_script = detail_resp.json()["script"]

    for phase in _SCRIPT_PHASES:
        assert replayed_script[phase] == created_script[phase], (
            f"{phase} changed between creation and replay"
        )


@pytest.mark.e2e
def test_mode1_script_contains_company_and_role_in_key_phases(api_client):
    """Real Gemini output for interview_tomorrow must reference company and role.

    Phase 3 (Rehearse) and Phase 5 (Close) are the phases where Maya is
    instructed to name the company and role. Verifies the prompt is working.
    """
    start_resp = api_client.post("/api/sessions/start", json=_MODE1_PAYLOAD)
    assert start_resp.status_code == 201, start_resp.text
    script = start_resp.json()["script"]

    assert "Stripe" in script["phase3"], (
        "company 'Stripe' missing from phase3 — prompt instruction may be broken"
    )
    assert "Product Manager" in script["phase3"] or "PM" in script["phase3"], (
        "role missing from phase3 — prompt instruction may be broken"
    )
    assert "Stripe" in script["phase5"], (
        "company 'Stripe' missing from phase5 — prompt instruction may be broken"
    )
