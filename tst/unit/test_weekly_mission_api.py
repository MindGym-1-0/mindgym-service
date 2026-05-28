import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.lib.supabase import get_supabase_user_client
from src.lib.auth import require_current_user_id, require_current_user_token

TEST_USER_ID = "test-user-999-uuid"
TEST_TOKEN = "fake-jwt-token"

mock_supabase = MagicMock()


@pytest.fixture(autouse=True)
def setup_dependencies():
    app.dependency_overrides[get_supabase_user_client] = lambda: mock_supabase
    app.dependency_overrides[require_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[require_current_user_token] = lambda: TEST_TOKEN
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_generate_weekly_mission_with_real_gemini(client):
    """Hits the real Gemini API to verify prompt structural rendering and token parsing."""
    # Mocking database responses so we don't need a real Supabase instance
    mock_supabase.table().select().eq().execute.return_value.data = [
        {"goal": "Backend Engineer", "stage": "Interviewing"}
    ]
    mock_supabase.table().select().eq().order().limit().execute.return_value.data = []
    mock_supabase.table().select().eq().gte().execute.return_value.data = []

    # Mock checking for an existing record row (return empty to trigger code's insert path)
    mock_supabase.table().select().eq().eq().execute.return_value.data = []

    # Mock the save response that occurs after the Gemini API finishes generating
    mock_supabase.table().insert().execute.return_value.data = [
        {
            "id": "real-gemini-test-uuid",
            "user_id": TEST_USER_ID,
            "week_start_date": "2026-06-01",
            "action_1": "Live engine generation validation target.",
            "action_1_completed": False,
            "action_2": "Live engine structural pass action.",
            "action_2_completed": False,
            "action_3": "Live engine schema conformity check.",
            "action_3_completed": False,
            "completion_count": 0,
            "generated_at": "2026-05-27T23:30:00+00:00",
            "updated_at": "2026-05-27T23:30:00+00:00",
        }
    ]

    # Execute request hitting the real Gemini model configured in your API router
    response = client.post("/api/weekly-mission/generate")

    assert response.status_code == 200
    json_data = response.json()

    # Assertions confirm the structural integrity of fields returned by the endpoint mapping logic
    assert "action_1" in json_data
    assert "action_2" in json_data
    assert "action_3" in json_data
    assert json_data["completion_count"] == 0
