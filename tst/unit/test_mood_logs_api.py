# tst/unit/test_mood_logs_api.py

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# IMPORT THE ACTUAL FUNCTION IMPLEMENTATIONS EXECUTED BY FASTAPI
from src.lib.auth import require_current_user_id, require_current_user_token
from src.main import app

client = TestClient(app)

# Generate consistent static UUIDs for multi-tenant isolation testing
TEST_USER_UUID = uuid4()
MALICIOUS_USER_UUID = uuid4()


@pytest.fixture
def mock_supabase():
    """Fixture to mock get_supabase_user_client in the mood_logs route module."""
    with patch("src.api.mood_logs.get_supabase_user_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """
    Bypasses FastAPI auth constraints globally by overriding the shared
    functional implementations tracking across sub-routers.
    """
    # Force overrides on the concrete callable execution blocks
    app.dependency_overrides[require_current_user_id] = lambda: TEST_USER_UUID
    app.dependency_overrides[require_current_user_token] = (
        lambda: "fake-mock-session-token"
    )

    yield

    # Clean up overrides cleanly after each individual test run
    app.dependency_overrides.clear()


# =====================================================================
# STEP 1: POST /api/mood-logs UNIT TESTS
# =====================================================================


def test_create_mood_log_success(mock_supabase):
    """Verifies valid payloads return a 201 status and the parsed record."""
    user_id = str(TEST_USER_UUID)
    mock_record = {
        "id": str(uuid4()),
        "user_id": user_id,
        "score": 8,
        "note": "Feeling productive today!",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    mock_query_result = MagicMock()
    mock_query_result.data = [mock_record]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        mock_query_result
    )

    payload = {"user_id": user_id, "score": 8, "note": "Feeling productive today!"}

    response = client.post("/api/mood-logs", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["score"] == 8
    assert response.json()["user_id"] == user_id


@pytest.mark.parametrize("invalid_score", [0, 11, -5, 4.5])
def test_create_mood_log_validation_error(mock_supabase, invalid_score):
    """Verifies Pydantic catches scores outside the 1-10 integer range."""
    payload = {
        "user_id": str(TEST_USER_UUID),
        "score": invalid_score,
        "note": "Testing boundary limits",
    }
    response = client.post("/api/mood-logs", json=payload)
    assert response.status_code in [
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_422_UNPROCESSABLE_CONTENT,
    ]


# =====================================================================
# STEP 2: GET /api/mood-logs/summary UNIT TESTS
# =====================================================================


def test_get_mood_summary_empty_history(mock_supabase):
    """Verifies a brand new user with no logs returns zero total counts and null items."""
    user_id = str(TEST_USER_UUID)

    mock_query_result = MagicMock()
    mock_query_result.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        mock_query_result
    )

    response = client.get(f"/api/mood-logs/summary?user_id={user_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_logs"] == 0
    assert data["avg_score"] is None
    assert len(data["last_7_days"]) == 7

    today_utc_str = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    assert data["last_7_days"][0]["date"] == today_utc_str
    assert data["last_7_days"][0]["score"] is None


def test_get_mood_summary_with_logs_deduplication(mock_supabase):
    """
    Verifies metric calculation accuracy and asserts that if a user submits multiple
    logs on the same day, the newest chronologically is kept while deduplicating historical arrays.
    """
    user_id = str(TEST_USER_UUID)
    today_str = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )

    # Mocks return dataset ordered DESC (newest timestamp first)
    mock_records = [
        {
            "score": 10,
            "created_at": f"{today_str}T18:00:00+00:00",
        },  # Newest entry for today
        {
            "score": 4,
            "created_at": f"{today_str}T08:00:00+00:00",
        },  # Older entry for today (should be skipped in graph)
        {"score": 6, "created_at": f"{yesterday_str}T15:30:00+00:00"},
    ]

    mock_query_result = MagicMock()
    mock_query_result.data = mock_records
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        mock_query_result
    )

    response = client.get(f"/api/mood-logs/summary?user_id={user_id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_logs"] == 3
    assert data["avg_score"] == round((10 + 4 + 6) / 3, 1)

    assert data["last_7_days"][0]["date"] == today_str
    assert (
        data["last_7_days"][0]["score"] == 10
    )  # Confirms deduplication saved the newest entry

    assert data["last_7_days"][1]["date"] == yesterday_str
    assert data["last_7_days"][1]["score"] == 6


def test_get_mood_summary_with_period_filters(mock_supabase):
    """Verifies that shifting the period filter query limits the data row average computations cleanly."""
    user_id = str(TEST_USER_UUID)
    today = datetime.now(timezone.utc).date()

    today_str = today.strftime("%Y-%m-%d")
    twelve_days_ago_str = (today - timedelta(days=12)).strftime("%Y-%m-%d")

    mock_records = [
        {"score": 8, "created_at": f"{today_str}T12:00:00+00:00"},
        {"score": 2, "created_at": f"{twelve_days_ago_str}T12:00:00+00:00"},
    ]

    mock_query_result = MagicMock()
    mock_query_result.data = mock_records
    mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = (
        mock_query_result
    )

    # 1. Test week period filtering logic
    res_week = client.get(f"/api/mood-logs/summary?user_id={user_id}&period=week")
    assert res_week.status_code == status.HTTP_200_OK
    assert res_week.json()["total_logs"] == 1
    assert res_week.json()["avg_score"] == 8.0

    # 2. Test month period filtering logic
    res_month = client.get(f"/api/mood-logs/summary?user_id={user_id}&period=month")
    assert res_month.status_code == status.HTTP_200_OK
    assert res_month.json()["total_logs"] == 2
    assert res_month.json()["avg_score"] == round((8 + 2) / 2, 1)


def test_get_mood_summary_cross_tenant_unauthorized(mock_supabase):
    """
    CRITICAL SECURITY TEST: Verifies that an authenticated caller attempting to supply
    another user's UUID into the parameters is immediately blocked with a 403 Forbidden status code.
    """
    malicious_target_id = str(MALICIOUS_USER_UUID)

    response = client.get(f"/api/mood-logs/summary?user_id={malicious_target_id}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Access to requested profile metrics is denied."

    # Assert database collection was intercepted completely
    mock_supabase.table.assert_not_called()
