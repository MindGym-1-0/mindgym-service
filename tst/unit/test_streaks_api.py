from __future__ import annotations
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.lib.auth import require_current_user_id, require_current_user_token
from src.main import app

client = TestClient(app)

TEST_USER_ID = "test-user-123-uuid"
TEST_TOKEN = "fake-jwt-token"


@pytest.fixture
def mock_supabase():
    """Fixture to dynamically patch get_supabase_user_client inside the streaks route module."""
    with patch("src.api.streaks.get_supabase_user_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """Bypasses FastAPI auth constraints by overriding dependencies on the application instance."""
    app.dependency_overrides[require_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[require_current_user_token] = lambda: TEST_TOKEN
    yield
    app.dependency_overrides.clear()


def create_mock_chain(return_data: list) -> MagicMock:
    """Helper utility to mimic fluent builders common in Supabase Postgrest queries.

    Ensures safe operations across background thread workers using asyncio.to_thread.
    """
    mock_query_layer = MagicMock()

    mock_execution_result = MagicMock()
    mock_execution_result.data = return_data

    mock_query_layer.execute.return_value = mock_execution_result
    mock_query_layer.execute.data = return_data

    # Chain all common fluent query operators back onto the builder mock
    mock_query_layer.select.return_value = mock_query_layer
    mock_query_layer.eq.return_value = mock_query_layer
    mock_query_layer.insert.return_value = mock_query_layer
    mock_query_layer.update.return_value = mock_query_layer

    return mock_query_layer


# =====================================================================
# STREAK ROUTE UNIT TESTS
# =====================================================================


def test_increment_streak_new_user(mock_supabase):
    """Verifies that a user without an existing streak record receives a fresh record starting at 1."""
    mock_supabase.table.return_value = create_mock_chain([])

    response = client.post("/api/streaks/increment")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_streak"] == 1


def test_increment_streak_already_active_today(mock_supabase):
    """Verifies that running increment multiple times on the same calendar day returns the existing streak metrics."""
    today_str = datetime.now(timezone.utc).date().isoformat()
    mock_records = [
        {
            "user_id": TEST_USER_ID,
            "current_streak": 5,
            "longest_streak": 5,
            "last_active": today_str,
        }
    ]
    mock_supabase.table.return_value = create_mock_chain(mock_records)

    response = client.post("/api/streaks/increment")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_streak"] == 5


def test_increment_streak_consecutive_day_yesterday(mock_supabase):
    """Verifies that an activity logged exactly one day after the last activity increments the active streak counter."""
    yesterday_str = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    # Configure the client mock chain to pass initial selection records, then update returns
    mock_chain = create_mock_chain(
        [
            {
                "user_id": TEST_USER_ID,
                "current_streak": 2,
                "longest_streak": 2,
                "last_active": yesterday_str,
            }
        ]
    )
    mock_supabase.table.return_value = mock_chain

    response = client.post("/api/streaks/increment")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_streak"] == 3


def test_increment_streak_broken_interval(mock_supabase):
    """Verifies that checking in after missing days resets an advanced historical streak back to 1."""
    long_ago_str = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()

    mock_chain = create_mock_chain(
        [
            {
                "user_id": TEST_USER_ID,
                "current_streak": 12,
                "longest_streak": 12,
                "last_active": long_ago_str,
            }
        ]
    )
    mock_supabase.table.return_value = mock_chain

    response = client.post("/api/streaks/increment")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_streak"] == 1


def test_get_streak_record_exists_and_alive(mock_supabase):
    """Verifies profile gets pull current streak totals correctly if active window is alive."""
    today_str = datetime.now(timezone.utc).date().isoformat()
    mock_supabase.table.return_value = create_mock_chain(
        [{"current_streak": 7, "longest_streak": 7, "last_active": today_str}]
    )

    response = client.get(f"/api/streaks/{TEST_USER_ID}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_streak"] == 7


def test_get_streak_unauthorized_user_access(mock_supabase):
    """CRITICAL SECURITY TEST: Verifies cross-tenant boundaries are strictly guarded."""
    response = client.get("/api/streaks/someone-elses-uuid-string")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        response.json()["detail"]
        == "You do not have permission to view this user's streak data."
    )
