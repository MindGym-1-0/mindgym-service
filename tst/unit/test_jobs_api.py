from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import src.api.job_id.jobs_id as jobs_id_module
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
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def api_client(fake_user_id: UUID, monkeypatch):
    client = TestClient(app)
    monkeypatch.setitem(app.dependency_overrides, require_current_user_id, lambda: fake_user_id)
    monkeypatch.setitem(app.dependency_overrides, require_current_user_token, lambda: "fake-token")

    mock_sb = MagicMock(name="supabase_client")
    monkeypatch.setattr(jobs_module, "get_supabase_user_client", lambda token: mock_sb)
    monkeypatch.setattr(jobs_id_module, "get_supabase_user_client", lambda token: mock_sb)

    qb = MagicMock(name="query_builder")
    mock_sb.table.return_value = qb

    qb.insert.return_value = qb
    qb.select.return_value = qb
    qb.eq.return_value = qb
    qb.order.return_value = qb
    qb.limit.return_value = qb
    qb.update.return_value = qb
    qb.delete.return_value = qb

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
    qb.insert.return_value.select.assert_called_once()


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