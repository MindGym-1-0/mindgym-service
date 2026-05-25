from __future__ import annotations
import json
from datetime import date, datetime, timedelta, UTC
from uuid import uuid4, UUID
from unittest.mock import patch, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app
from src.types.daily_focus import ActionType

client = TestClient(app)

# Standard mock constants matching security context fixtures
TEST_USER_UUID = uuid4()
MOCK_TOKEN = "mocked-supabase-jwt-token"


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """Maps dependency overrides by looking at the exact route parameter names."""
    target_route = None
    for route in app.routes:
        if getattr(route, "path", None) == "/api/daily-focus/generate":
            target_route = route
            break

    if target_route and hasattr(target_route, "dependant"):
        for sub_dependant in target_route.dependant.dependencies:
            param_name = sub_dependant.name
            call_target = sub_dependant.call

            if param_name == "current_user_id":
                app.dependency_overrides[call_target] = lambda: TEST_USER_UUID
            elif param_name == "token":
                app.dependency_overrides[call_target] = lambda: MOCK_TOKEN
    else:
        from src.api import daily_focus
        import inspect

        sig = inspect.signature(daily_focus.generate_daily_focus)
        for param_name, param in sig.parameters.items():
            if hasattr(param.annotation, "__metadata__"):
                for metadata in param.annotation.__metadata__:
                    if hasattr(metadata, "dependency") and metadata.dependency:
                        if param_name == "current_user_id":
                            app.dependency_overrides[metadata.dependency] = (
                                lambda: TEST_USER_UUID
                            )
                        elif param_name == "token":
                            app.dependency_overrides[metadata.dependency] = (
                                lambda: MOCK_TOKEN
                            )

    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase():
    """Fixture to intercept Supabase clients and provide a chained query constructor supporting updates."""
    with patch("src.api.daily_focus.get_supabase_user_client") as mock_get_client:
        mock_client = MagicMock()

        # Helper to mock fluent interface patterns for reads, updates, and inserts
        def create_mock_chain(return_data=None):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.insert.return_value = chain
            chain.update.return_value = chain
            chain.eq.return_value = chain
            chain.is_.return_value = chain
            chain.gte.return_value = chain
            chain.order.return_value = chain
            chain.limit.return_value = chain

            # Setup final execution value encapsulated inside a PostgrestResponse structure mock
            mock_execution = MagicMock()
            mock_execution.data = return_data or []
            chain.execute.return_value = mock_execution
            return chain

        mock_client._create_chain = create_mock_chain
        mock_get_client.return_value = mock_client
        yield mock_client


def test_generate_daily_focus_success(mock_supabase):
    """Verifies baseline pathway executing clean JSON extraction and parsing via google-genai."""

    final_db_record = {
        "id": str(uuid4()),
        "user_id": str(TEST_USER_UUID),
        "date": date.today().strftime("%Y-%m-%d"),
        "action_1_text": "Review system architecture designs for your upcoming interviews.",
        "action_1_type": "PREPARE_INTERVIEW",
        "action_2_text": "Apply to 2 backend positions to pad pipeline limits.",
        "action_2_type": "ADD_APPLICATIONS",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    def side_effect_mock(table_name):
        if table_name == "users":
            return mock_supabase._create_chain(
                [
                    {
                        "goal": "Backend Engineer",
                        "stage": "Applying",
                        "anxiety_level": "medium",
                    }
                ]
            )
        elif table_name == "streaks":
            return mock_supabase._create_chain([{"current_streak": 5}])
        elif table_name in ["daily_focus", "daily_focuses"]:
            return mock_supabase._create_chain([final_db_record])
        else:
            return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    gemini_json_mock = {
        "action_1_text": "Review system architecture designs for your upcoming interviews.",
        "action_1_type": "PREPARE_INTERVIEW",
        "action_2_text": "Apply to 2 backend positions to pad pipeline limits.",
        "action_2_type": "ADD_APPLICATIONS",
    }

    mock_response_obj = MagicMock()
    mock_response_obj.text = json.dumps(gemini_json_mock)

    with patch("src.api.daily_focus.genai.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response_obj
        mock_client_class.return_value = mock_client_instance

        response = client.post("/api/daily-focus/generate")

        assert response.status_code == status.HTTP_200_OK
        res_data = response.json()
        assert res_data["action_1_type"] == "PREPARE_INTERVIEW"
        assert "Review system architecture" in res_data["action_1_text"]


def test_generate_daily_focus_timeout_fallback(mock_supabase):
    """Verifies that exceeding the timeout boundary cleanly shifts execution to fallback pipeline heuristics."""

    stagnant_job = {
        "company": "Google",
        "role": "Software Engineer",
        "stage": "Applied",
        "last_moved_at": (date.today() - timedelta(days=20)).strftime("%Y-%m-%d"),
    }

    fallback_record = {
        "id": str(uuid4()),
        "user_id": str(TEST_USER_UUID),
        "date": date.today().strftime("%Y-%m-%d"),
        "action_1_text": "Follow up with the hiring team or recruiter at Google regarding your Software Engineer application.",
        "action_1_type": ActionType.FOLLOW_UP.value,
        "action_2_text": "Keep looking for new technical opportunities to fill your pipeline.",
        "action_2_type": ActionType.ADD_APPLICATIONS.value,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    def side_effect_mock(table_name):
        if table_name == "jobs":
            return mock_supabase._create_chain([stagnant_job])
        elif table_name == "users":
            return mock_supabase._create_chain(
                [{"goal": "Backend Engineer", "stage": "Applying"}]
            )
        elif table_name in ["daily_focus", "daily_focuses"]:
            return mock_supabase._create_chain([fallback_record])
        else:
            return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    def simulate_timeout(*args, **kwargs):
        raise Exception("Timeout or network failure simulation window exception")

    with patch("src.api.daily_focus.genai.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.side_effect = simulate_timeout
        mock_client_class.return_value = mock_client_instance

        response = client.post("/api/daily-focus/generate")

        assert response.status_code == status.HTTP_200_OK
        res_data = response.json()
        assert res_data["action_1_type"] == "FOLLOW_UP"
        assert "Google" in res_data["action_1_text"]
