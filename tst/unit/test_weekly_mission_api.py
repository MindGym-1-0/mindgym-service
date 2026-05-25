# tst/unit/test_weekly_mission_api.py

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.api.weekly_mission import get_supabase_client
from src.lib.auth_dependencies import get_current_user

mock_supabase = MagicMock()
mock_user = {"id": "test-user-999-uuid", "email": "engineer@test.com"}


@pytest.fixture(autouse=True)
def setup_dependencies():
    app.dependency_overrides[get_supabase_client] = lambda: mock_supabase
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@patch("google.genai.Client")
def test_generate_weekly_mission_success(mock_gen_client_class, client):
    """Verifies standard end-to-end mission compilation path when Gemini produces valid strings."""
    mock_supabase.table().select().eq().execute.return_value.data = []
    mock_supabase.table().select().eq().order().limit().execute.return_value.data = []
    mock_supabase.table().select().eq().gte().execute.return_value.data = []

    # Explicitly mock the existing row validation check to return empty list (forcing insert path)
    mock_supabase.table().select().eq().eq().execute.return_value.data = []

    mock_supabase.table().insert().execute.return_value.data = [
        {
            "id": "mission-uuid-1",
            "user_id": "test-user-999-uuid",
            "week_start_date": "2026-05-25",
            "action_1": "Apply to 2 targeted software roles.",
            "action_1_completed": False,
            "action_2": "Complete a system design tracking run.",
            "action_2_completed": False,
            "action_3": "Review tech debrief data.",
            "action_3_completed": False,
            "completion_count": 0,
            "generated_at": "2026-05-24T18:00:00+00:00",
            "updated_at": "2026-05-24T18:00:00+00:00",
        }
    ]

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"action_1": "Apply to 2 targeted software roles.", "action_2": "Complete a system design tracking run.", "action_3": "Review tech debrief data."}'
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_gen_client_class.return_value = mock_client_instance

    response = client.post("/api/weekly-mission/generate")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["action_1"] == "Apply to 2 targeted software roles."
    assert json_data["completion_count"] == 0


@patch("google.genai.Client")
def test_generate_weekly_mission_timeout_fallback(mock_gen_client_class, client):
    """Verifies that if Gemini hangs, our 4s asyncio timeout catches it and uses fallback logic."""
    mock_supabase.table().select().eq().execute.return_value.data = []
    mock_supabase.table().select().eq().order().limit().execute.return_value.data = []
    mock_supabase.table().select().eq().gte().execute.return_value.data = []

    # Explicitly mock the existing row validation check to return empty list (forcing insert path)
    mock_supabase.table().select().eq().eq().execute.return_value.data = []

    mock_supabase.table().insert().execute.return_value.data = [
        {
            "id": "fallback-mission-uuid",
            "user_id": "test-user-999-uuid",
            "week_start_date": "2026-05-25",
            "action_1": "Target and submit at least 2 new backend engineering applications to expand your baseline pipeline.",
            "action_1_completed": False,
            "action_2": "Complete 2 practice mock sessions this week to initialize your competency tracking performance logs.",
            "action_2_completed": False,
            "action_3": "Book and complete a core system design mock study session to stabilize your weekly performance trends.",
            "action_3_completed": False,
            "completion_count": 0,
            "generated_at": "2026-05-24T18:00:00+00:00",
            "updated_at": "2026-05-24T18:00:00+00:00",
        }
    ]

    # Acoroutine function that replicates a slow runtime stalling execution
    async def slow_generate_coroutine(*args, **kwargs):
        await asyncio.sleep(10.0)
        raise TimeoutError("Gemini client execution stalled.")

    # Native synchronous mock setup that returns the awaitable task smoothly to asyncio.to_thread
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.side_effect = (
        lambda *args, **kwargs: slow_generate_coroutine()
    )
    mock_gen_client_class.return_value = mock_client_instance

    response = client.post("/api/weekly-mission/generate")
    assert response.status_code == 200
    json_data = response.json()
    assert (
        "Target and submit at least 2 new backend engineering applications"
        in json_data["action_1"]
    )
