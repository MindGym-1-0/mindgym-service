from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.interviews as interviews_module
from src.lib.auth import require_current_user_id, require_current_user_token


@pytest.fixture
def fake_user_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def sample_interview_row(fake_user_id: UUID) -> dict[str, object]:
    return {
        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "user_id": str(fake_user_id),
        "company": "Acme",
        "role": "Engineer",
        "interview_date": "2026-06-10T12:00:00+00:00",
        "event_type": "onsite",
        "job_id": None,
        "notes": None,
        "outcome": "pending",
        "check_in_attempts": 0,
        "next_check_in_at": None,
        "created_at": "2026-06-01T00:00:00+00:00",
    }


def create_mock_chain() -> MagicMock:
    mock_query_layer = MagicMock(name="fluent_query_layer")
    mock_query_layer.select.return_value = mock_query_layer
    mock_query_layer.eq.return_value = mock_query_layer
    mock_query_layer.gte.return_value = mock_query_layer
    mock_query_layer.lt.return_value = mock_query_layer
    mock_query_layer.order.return_value = mock_query_layer
    mock_query_layer.limit.return_value = mock_query_layer
    mock_query_layer.insert.return_value = mock_query_layer
    mock_query_layer.update.return_value = mock_query_layer
    mock_query_layer.delete.return_value = mock_query_layer
    return mock_query_layer


@pytest.fixture
def api_client(fake_user_id: UUID, monkeypatch):
    test_app = FastAPI()
    test_app.include_router(
        interviews_module.router, prefix="/api/interviews", tags=["interviews"]
    )
    client = TestClient(test_app)

    monkeypatch.setitem(
        test_app.dependency_overrides, require_current_user_id, lambda: fake_user_id
    )
    monkeypatch.setitem(
        test_app.dependency_overrides, require_current_user_token, lambda: "fake-token"
    )

    mock_sb = MagicMock(name="supabase_client")
    monkeypatch.setattr(
        interviews_module, "get_supabase_user_client", lambda token: mock_sb
    )

    qb = create_mock_chain()
    mock_sb.table.return_value = qb

    yield client, qb, mock_sb

    test_app.dependency_overrides.clear()


@pytest.mark.parametrize("outcome", ["offer", "awaiting", "pending", "no_offer"])
def test_patch_interview_outcome_success(
    api_client, sample_interview_row: dict[str, object], outcome: str
):
    client, qb, _sb = api_client

    updated_row = dict(sample_interview_row)
    updated_row["outcome"] = outcome

    qb.execute.side_effect = [
        SimpleNamespace(data=[sample_interview_row]),
        SimpleNamespace(data=[updated_row]),
    ]

    resp = client.patch(
        f"/api/interviews/{sample_interview_row['id']}/outcome",
        json={"outcome": outcome},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sample_interview_row["id"]
    assert body["outcome"] == outcome
    assert body["check_in_attempts"] == updated_row["check_in_attempts"]
    assert body["next_check_in_at"] == updated_row["next_check_in_at"]


def test_patch_interview_outcome_from_not_ready_increments_attempts(
    api_client, sample_interview_row: dict[str, object]
):
    client, qb, _sb = api_client

    existing_row = dict(sample_interview_row)
    existing_row["outcome"] = "awaiting"

    updated_row = dict(existing_row)
    updated_row["outcome"] = "awaiting"
    updated_row["check_in_attempts"] = 1
    updated_row["next_check_in_at"] = "2026-06-04T12:00:00+00:00"

    qb.execute.side_effect = [
        SimpleNamespace(data=[existing_row]),
        SimpleNamespace(data=[updated_row]),
    ]

    resp = client.patch(
        f"/api/interviews/{sample_interview_row['id']}/outcome",
        json={"outcome": "no_offer", "from_not_ready": True},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["check_in_attempts"] == 1
    assert body["outcome"] == "awaiting"
    assert body["next_check_in_at"] is not None


def test_patch_interview_outcome_from_not_ready_threshold_sets_no_offer(
    api_client, sample_interview_row: dict[str, object]
):
    client, qb, _sb = api_client

    existing_row = dict(sample_interview_row)
    existing_row["check_in_attempts"] = 2
    existing_row["outcome"] = "awaiting"

    updated_row = dict(existing_row)
    updated_row["check_in_attempts"] = 3
    updated_row["outcome"] = "no_offer"
    updated_row["next_check_in_at"] = None

    qb.execute.side_effect = [
        SimpleNamespace(data=[existing_row]),
        SimpleNamespace(data=[updated_row]),
    ]

    resp = client.patch(
        f"/api/interviews/{sample_interview_row['id']}/outcome",
        json={"outcome": "no_offer", "from_not_ready": True},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["check_in_attempts"] == 3
    assert body["outcome"] == "no_offer"
    assert body["next_check_in_at"] is None


def test_patch_interview_outcome_missing_or_not_owned_returns_404(
    api_client, sample_interview_row: dict[str, object]
):
    client, qb, _sb = api_client

    qb.execute.return_value = SimpleNamespace(data=[])

    resp = client.patch(
        f"/api/interviews/{sample_interview_row['id']}/outcome",
        json={"outcome": "offer"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 404


def test_patch_interview_outcome_invalid_outcome_returns_422(
    api_client, sample_interview_row: dict[str, object]
):
    client, qb, _sb = api_client

    resp = client.patch(
        f"/api/interviews/{sample_interview_row['id']}/outcome",
        json={"outcome": "invalid"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 422
    qb.execute.assert_not_called()


def test_patch_interview_outcome_from_not_ready_requires_no_offer(
    api_client, sample_interview_row: dict[str, object]
):
    client, qb, _sb = api_client

    resp = client.patch(
        f"/api/interviews/{sample_interview_row['id']}/outcome",
        json={"outcome": "offer", "from_not_ready": True},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 422
    assert (
        resp.json()["detail"]
        == "from_not_ready can only be used with outcome='no_offer'."
    )
    qb.update.assert_not_called()
    qb.execute.assert_not_called()


@pytest.mark.parametrize("outcome", ["offer", "awaiting", "pending"])
def test_patch_interview_outcome_rejects_from_not_ready_for_non_no_offer(
    api_client, sample_interview_row: dict[str, object], outcome: str
):
    client, qb, _sb = api_client

    resp = client.patch(
        f"/api/interviews/{sample_interview_row['id']}/outcome",
        json={"outcome": outcome, "from_not_ready": True},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 422
    assert (
        resp.json()["detail"]
        == "from_not_ready can only be used with outcome='no_offer'."
    )
    qb.execute.assert_not_called()


def test_patch_interview_outcome_invalid_uuid_path_returns_422(api_client):
    client, qb, _sb = api_client

    resp = client.patch(
        "/api/interviews/not-a-uuid/outcome",
        json={"outcome": "offer"},
        headers={"Authorization": "Bearer fake-token"},
    )

    assert resp.status_code == 422
    qb.execute.assert_not_called()
