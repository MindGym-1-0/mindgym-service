from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import src.api.jobs_id as jobs_id_module
import src.api.jobs as jobs_module
from src.lib.auth import require_current_user_id, require_current_user_token
from src.main import app, create_app


@pytest.fixture
def fake_user_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_job_row(fake_user_id: UUID):
    jid = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    return {
        "id": str(jid),
        "user_id": str(fake_user_id),
        "company": "Acme",
        "role": "Engineer",
        "status": "applied",
        "applied_at": None,
        "notes": None,
        "last_moved_at": "2026-01-01T00:00:00+00:00",
        "outcome": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def api_client(fake_user_id: UUID, monkeypatch):
    client = TestClient(app)
    monkeypatch.setitem(
        app.dependency_overrides, require_current_user_id, lambda: fake_user_id
    )
    monkeypatch.setitem(
        app.dependency_overrides, require_current_user_token, lambda: "fake-token"
    )

    mock_sb = MagicMock(name="supabase_client")
    monkeypatch.setattr(jobs_module, "get_supabase_user_client", lambda token: mock_sb)
    monkeypatch.setattr(
        jobs_id_module, "get_supabase_user_client", lambda token: mock_sb
    )

    qb = MagicMock(name="query_builder")
    mock_sb.table.return_value = qb

    qb.insert.return_value = qb
    qb.select.return_value = qb
    qb.eq.return_value = qb
    qb.is_.return_value = qb
    qb.order.return_value = qb
    qb.limit.return_value = qb
    qb.update.return_value = qb
    qb.delete.return_value = qb
    qb.maybe_single.return_value = qb

    yield client, qb, mock_sb

    app.dependency_overrides.pop(require_current_user_id, None)
    app.dependency_overrides.pop(require_current_user_token, None)


def test_post_creates_job_201(api_client, sample_job_row: dict[str, object]):
    client, qb, _sb = api_client

    qb.execute.return_value = SimpleNamespace(data=[sample_job_row])

    resp = client.post(
        "/api/jobs",
        json={"company": " Acme ", "role": " Engineer "},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 201

    qb.insert.assert_called_once()
    qb.execute.assert_called()


def test_get_lists_jobs_ordered(api_client, sample_job_row: dict[str, object]):
    client, qb, _sb = api_client

    row2 = dict(sample_job_row)
    row2["id"] = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    qb.execute.return_value = SimpleNamespace(data=[row2, sample_job_row])

    resp = client.get("/api/jobs", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200

    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 2
    qb.order.assert_called()


def test_get_empty_returns_array(api_client):
    client, qb, _sb = api_client

    qb.execute.return_value = SimpleNamespace(data=[])

    resp = client.get("/api/jobs", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_post_invalid_status_400(api_client):
    client, qb, _sb = api_client

    resp = client.post(
        "/api/jobs",
        json={"company": "Acme", "role": "Engineer", "status": "nope"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 400
    qb.insert.assert_not_called()


def test_post_missing_company_400(api_client):
    client, qb, _sb = api_client

    resp = client.post(
        "/api/jobs",
        json={"role": "Engineer"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 400
    qb.insert.assert_not_called()


def test_post_only_whitespace_company_400(api_client):
    """Verifies that strings containing only blank spaces are rejected with a 400."""
    client, qb, _sb = api_client

    resp = client.post(
        "/api/jobs",
        json={"company": "     ", "role": "Backend Engineer"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 400
    qb.insert.assert_not_called()


def test_patch_updates_job(api_client, sample_job_row: dict[str, object]):
    client, qb, _sb = api_client

    updated = dict(sample_job_row)
    updated["status"] = "screen"

    qb.execute.return_value = SimpleNamespace(data=[updated])

    resp = client.patch(
        f"/api/jobs/{sample_job_row['id']}",
        json={"status": "screen"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "screen"
    qb.update.assert_called_once()


def test_patch_invalid_status_400(api_client, sample_job_row: dict[str, object]):
    client, qb, _sb = api_client

    resp = client.patch(
        f"/api/jobs/{sample_job_row['id']}",
        json={"status": "nope"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 400
    qb.update.assert_not_called()


def test_patch_not_found_404(api_client, sample_job_row: dict[str, object]):
    client, qb, _sb = api_client

    qb.execute.return_value = SimpleNamespace(data=[])

    resp = client.patch(
        f"/api/jobs/{sample_job_row['id']}",
        json={"status": "screen"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 404


def test_delete_ok(api_client, sample_job_row: dict[str, object]):
    client, qb, _sb = api_client

    qb.execute.return_value = SimpleNamespace(data=[{"id": sample_job_row["id"]}])

    resp = client.delete(
        f"/api/jobs/{sample_job_row['id']}",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"success": True}


def test_delete_not_found_404(api_client, sample_job_row: dict[str, object]):
    client, qb, _sb = api_client

    qb.execute.return_value = SimpleNamespace(data=[])

    resp = client.delete(
        f"/api/jobs/{sample_job_row['id']}",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 404


def test_unauthenticated_401():
    client = TestClient(create_app())
    resp = client.get("/api/jobs")
    assert resp.status_code == 401


# =============================================================
# NEW TESTS: STEP 1 — STAGE ADVANCEMENT
# =============================================================


def test_advance_stage_sequential_success(api_client, sample_job_row):
    """Should successfully advance when moving strictly down the next state node line."""
    client, qb, _sb = api_client

    updated_row = dict(sample_job_row)
    updated_row["status"] = "screen"

    # Mock sequence chain responses: 1st for maybe_single select, 2nd for update return
    qb.execute.side_effect = [
        SimpleNamespace(data=sample_job_row),
        SimpleNamespace(data=[updated_row]),
    ]

    resp = client.patch(
        f"/api/jobs/{sample_job_row['id']}/advance",
        json={"new_stage": "screen"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "screen"


def test_advance_stage_illegal_skip_400(api_client, sample_job_row):
    """Should block transitions that attempt to hop over required sequence steps."""
    client, qb, _sb = api_client

    qb.execute.return_value = SimpleNamespace(data=sample_job_row)

    resp = client.patch(
        f"/api/jobs/{sample_job_row['id']}/advance",
        json={"new_stage": "hm"},  # Skipping screen status node entirely
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 400
    assert "Illegal transition" in resp.json()["detail"]


# =============================================================
# NEW TESTS: STEP 2 — OUTCOME LOGGING
# =============================================================


def test_log_outcome_terminal_success(api_client, sample_job_row):
    """Should close the loop cleanly and flag linked elements for recovery upon negative state logs."""
    client, qb, sb = api_client

    closed_row = dict(sample_job_row)
    closed_row["status"] = "closed"
    closed_row["outcome"] = "rejected"

    # Sequence return layout: 1. Confirm Job exists, 2. Return updated row, 3. Find target interview to trigger
    qb.execute.side_effect = [
        SimpleNamespace(data={"id": sample_job_row["id"]}),
        SimpleNamespace(data=[closed_row]),
        SimpleNamespace(data={"id": "interview-uuid-123"}),
    ]

    resp = client.post(
        f"/api/jobs/{sample_job_row['id']}/outcome",
        json={"outcome": "rejected"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
    assert resp.json()["outcome"] == "rejected"
    # Verify cascade update to target interview table executed properly
    sb.table.assert_any_call("interviews")


# =============================================================
# NEW TESTS: STEP 3 — STALE DETECTION
# =============================================================


def test_get_stale_jobs_filtration(api_client, sample_job_row):
    """Should correctly classify entries inactive for over 28 days as stale, sorting cleanly."""
    client, qb, _sb = api_client

    stale_date = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
    fresh_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    row_stale = dict(sample_job_row)
    row_stale["last_moved_at"] = stale_date

    row_fresh = dict(sample_job_row)
    row_fresh["last_moved_at"] = fresh_date

    qb.execute.return_value = SimpleNamespace(data=[row_stale, row_fresh])

    resp = client.get("/api/jobs/stale", headers={"Authorization": "Bearer fake-token"})

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["days_since_moved"] == 35
