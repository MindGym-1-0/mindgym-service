# tst/unit/test_mood_logs_api.py

from __future__ import annotations
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Import the actual dependency functions to override them
from src.lib.auth import require_current_user_id, require_current_user_token
from src.main import app

client = TestClient(app)

# Generate a static consistent UUID for testing auth overrides
TEST_USER_UUID = uuid4()


@pytest.fixture
def mock_supabase():
    """Fixture to mock get_supabase_user_client in the mood_logs route module."""
    with patch("src.api.mood_logs.get_supabase_user_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """Bypasses custom Supabase auth checks by injection overriding callables."""
    app.dependency_overrides[require_current_user_token] = (
        lambda: "fake-mock-session-token"
    )
    app.dependency_overrides[require_current_user_id] = lambda: TEST_USER_UUID
    yield
    # Clear overrides after each test run to keep testing clean
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
        "created_at": datetime.utcnow().isoformat(),
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
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


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
    assert data["last_7_days"][0]["date"] == date.today().strftime("%Y-%m-%d")
    assert data["last_7_days"][0]["score"] is None


def test_get_mood_summary_with_logs(mock_supabase):
    """Verifies calculation metrics and chronological date structural positioning."""
    user_id = str(TEST_USER_UUID)
    today_str = date.today().strftime("%Y-%m-%d")
    yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    mock_records = [
        {"score": 10, "created_at": f"{today_str}T10:00:00+00:00"},
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
    assert data["total_logs"] == 2
    assert data["avg_score"] == 8.0

    assert data["last_7_days"][0]["date"] == today_str
    assert data["last_7_days"][0]["score"] == 10

    assert data["last_7_days"][1]["date"] == yesterday_str
    assert data["last_7_days"][1]["score"] == 6

    assert data["last_7_days"][2]["score"] is None
