import pytest
from datetime import datetime, timezone, date, timedelta
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.main import app

# Pulling the dependencies exactly from where they are consumed
from src.api.streaks import get_supabase_client
from src.lib.auth_dependencies import get_current_user

# Setup isolated mock structures for database interactions
mock_supabase = MagicMock()
mock_user = {"id": "test-user-123-uuid", "email": "developer@test.com"}


# Override dependencies automatically across every test execution
@pytest.fixture(autouse=True)
def setup_dependencies():
    app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# =====================================================================
# INCREMENT STREAK TESTS (POST /api/streaks/increment)
# =====================================================================


def test_increment_streak_new_user(client):
    """Rule: If no streak record exists, initialize values to 1."""
    # Mocking empty list returned from Supabase table select
    mock_supabase.table().select().eq().execute.return_value.data = []
    mock_supabase.table().insert().execute.return_value.data = [{}]

    response = client.post("/api/streaks/increment")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_streak"] == 1
    assert json_data["longest_streak"] == 1
    assert json_data["milestone"] is None


def test_increment_streak_already_active_today(client):
    """Rule: If last_active is today, do nothing and return values as-is."""
    today_str = datetime.now(timezone.utc).date().isoformat()

    mock_supabase.table().select().eq().execute.return_value.data = [
        {
            "user_id": "test-user-123-uuid",
            "current_streak": 5,
            "longest_streak": 10,
            "last_active": today_str,
        }
    ]

    response = client.post("/api/streaks/increment")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_streak"] == 5
    assert json_data["longest_streak"] == 10
    assert json_data["milestone"] is None


def test_increment_streak_consecutive_day_yesterday(client):
    """Rule: If last_active is yesterday, increment current_streak by 1."""
    yesterday_str = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    mock_supabase.table().select().eq().execute.return_value.data = [
        {
            "user_id": "test-user-123-uuid",
            "current_streak": 2,
            "longest_streak": 5,
            "last_active": yesterday_str,
        }
    ]
    mock_supabase.table().update().eq().execute.return_value.data = [{}]

    response = client.post("/api/streaks/increment")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_streak"] == 3
    assert json_data["longest_streak"] == 5
    assert json_data["milestone"] == 3  # Hit a 3-day milestone!


def test_increment_streak_broken_interval(client):
    """Rule: If last_active is older than yesterday, reset current_streak to 1."""
    long_ago_str = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()

    mock_supabase.table().select().eq().execute.return_value.data = [
        {
            "user_id": "test-user-123-uuid",
            "current_streak": 12,
            "longest_streak": 20,
            "last_active": long_ago_str,
        }
    ]
    mock_supabase.table().update().eq().execute.return_value.data = [{}]

    response = client.post("/api/streaks/increment")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_streak"] == 1  # Streak broke; reset back to 1
    assert json_data["longest_streak"] == 20  # Record high preserved intact


def test_increment_streak_breaks_longest_streak_record(client):
    """Rule: Update longest_streak if current_streak surpasses it."""
    yesterday_str = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    mock_supabase.table().select().eq().execute.return_value.data = [
        {
            "user_id": "test-user-123-uuid",
            "current_streak": 4,
            "longest_streak": 4,
            "last_active": yesterday_str,
        }
    ]
    mock_supabase.table().update().eq().execute.return_value.data = [{}]

    response = client.post("/api/streaks/increment")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_streak"] == 5
    assert json_data["longest_streak"] == 5  # Scaled up to mirror new record high


# =====================================================================
# GET STREAK STATE TESTS (GET /api/streaks/{user_id})
# =====================================================================


def test_get_streak_record_exists(client):
    """Verify clean retrieval of streak metrics when data exists."""
    mock_supabase.table().select().eq().execute.return_value.data = [
        {"current_streak": 7, "longest_streak": 14}
    ]

    response = client.get("/api/streaks/test-user-123-uuid")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_streak"] == 7
    assert json_data["longest_streak"] == 14


def test_get_streak_record_missing_returns_zeros(client):
    """Rule: Return fallback zeroes if no row matches the given user_id."""
    mock_supabase.table().select().eq().execute.return_value.data = []

    response = client.get("/api/streaks/brand-new-user-uuid")

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_streak"] == 0
    assert json_data["longest_streak"] == 0
