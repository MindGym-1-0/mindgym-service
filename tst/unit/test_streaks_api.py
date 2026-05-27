import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from src.main import app
from src.lib.supabase import get_supabase_user_client
from src.lib.auth import require_current_user_id, require_current_user_token

TEST_USER_ID = "test-user-123-uuid"
TEST_TOKEN = "fake-jwt-token"


@pytest.fixture
def mock_sb():
    mock = MagicMock()
    # Ensure chained calls return a mock with data
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[])
    )
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[])
    )
    return mock


@pytest.fixture(autouse=True)
def setup_dependencies(mock_sb):
    app.dependency_overrides[get_supabase_user_client] = lambda: mock_sb
    app.dependency_overrides[require_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[require_current_user_token] = lambda: TEST_TOKEN
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_increment_streak_new_user(client, mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = (
        []
    )
    response = client.post("/api/streaks/increment")
    assert response.status_code == 200


def test_increment_streak_already_active_today(client, mock_sb):
    today_str = datetime.now(timezone.utc).date().isoformat()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "user_id": TEST_USER_ID,
            "current_streak": 5,
            "longest_streak": 5,
            "last_active": today_str,
        }
    ]
    response = client.post("/api/streaks/increment")
    assert response.status_code == 200
    assert response.json()["current_streak"] == 5


def test_increment_streak_consecutive_day_yesterday(client, mock_sb):
    yesterday_str = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "user_id": TEST_USER_ID,
            "current_streak": 2,
            "longest_streak": 2,
            "last_active": yesterday_str,
        }
    ]
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"current_streak": 3}
    ]
    response = client.post("/api/streaks/increment")
    assert response.status_code == 200
    assert response.json()["current_streak"] == 3


def test_increment_streak_broken_interval(client, mock_sb):
    long_ago_str = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "user_id": TEST_USER_ID,
            "current_streak": 12,
            "longest_streak": 12,
            "last_active": long_ago_str,
        }
    ]
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"current_streak": 1}
    ]
    response = client.post("/api/streaks/increment")
    assert response.status_code == 200
    assert response.json()["current_streak"] == 1


def test_get_streak_record_exists_and_alive(client, mock_sb):
    today_str = datetime.now(timezone.utc).date().isoformat()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"current_streak": 7, "longest_streak": 7, "last_active": today_str}
    ]
    response = client.get(f"/api/streaks/{TEST_USER_ID}")
    assert response.status_code == 200
    assert response.json()["current_streak"] == 7


def test_get_streak_unauthorized_user_access(client):
    response = client.get("/api/streaks/someone-elses-uuid-string")
    assert response.status_code == 403
