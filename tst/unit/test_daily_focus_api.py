from __future__ import annotations

import inspect
from datetime import date, datetime, UTC
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)
TEST_USER_UUID = str(uuid4())
MOCK_TOKEN = "mocked-supabase-jwt-token"
TARGET_PATH = "/api/daily-focus/generate"


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """Maps dynamic dependency overrides looking at exact route paths."""
    target_route = None
    for route in app.routes:
        if TARGET_PATH == getattr(route, "path", ""):
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

        sig = inspect.signature(daily_focus.generate_daily_focus)
        for param_name, param in sig.parameters.items():
            if hasattr(param.annotation, "__metadata__"):
                for metadata in param.annotation.__metadata__:
                    if hasattr(metadata, "dependency") and metadata.dependency:
                        if param_name == "current_user_id":
                            app.dependency_overrides[
                                metadata.dependency
                            ] = lambda: TEST_USER_UUID
                        elif param_name == "token":
                            app.dependency_overrides[
                                metadata.dependency
                            ] = lambda: MOCK_TOKEN

    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_supabase():
    """Fixture to intercept Supabase clients and build fluent mock chains."""
    with patch(
        "src.api.daily_focus.get_supabase_user_client"
    ) as mock_get_client:
        mock_client = MagicMock()

        def create_mock_chain(return_data=None):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.gte.return_value = chain
            chain.is_.return_value = chain
            chain.limit.return_value = chain
            chain.order.return_value = chain
            chain.update.return_value = chain
            chain.insert.return_value = chain
            chain.execute.return_value = MagicMock(data=return_data or [])
            return chain

        mock_client._create_chain = create_mock_chain
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openai_chat():
    """Fixture to mock the internal OpenAI _chat function to prevent network hits."""
    with patch("src.api.daily_focus._chat") as mock_chat_fn:
        mock_json_payload = """
        {
          "action_1_text": "Prepare for your interview at Google.",
          "action_1_type": "prepare_questions",
          "action_2_text": "Follow up with Amazon regarding status.",
          "action_2_type": "follow_up"
        }
        """
        mock_chat_fn.return_value = mock_json_payload
        yield mock_chat_fn


def test_generate_daily_focus_success(mock_supabase, mock_openai_chat):
    """Verifies focus compilation across pipeline databases and OpenAI parser."""
    today_str = date.today().strftime("%Y-%m-%d")
    now_iso = datetime.now(UTC).isoformat()

    def side_effect_mock(table_name):
        if table_name == "users":
            return mock_supabase._create_chain(
                [
                    {
                        "goal": "Get hired",
                        "stage": "Applying",
                        "anxiety_level": 3.0,
                    }
                ]
            )
        elif table_name == "jobs":
            return mock_supabase._create_chain(
                [
                    {
                        "company": "Amazon",
                        "role": "SDE",
                        "status": "applied",
                        "last_moved_at": today_str,
                    }
                ]
            )
        elif table_name == "interviews":
            return mock_supabase._create_chain(
                [
                    {
                        "company": "Google",
                        "role": "Frontend Engineer",
                        "interview_date": today_str,
                    }
                ]
            )
        elif table_name == "daily_focus":
            chain = mock_supabase._create_chain()
            chain.execute.return_value = MagicMock(
                data=[
                    {
                        "id": str(uuid4()),
                        "user_id": TEST_USER_UUID,
                        "date": today_str,
                        "action_1_text": "Prepare for your interview...",
                        "action_1_type": "prepare_questions",
                        "action_2_text": "Follow up with Amazon...",
                        "action_2_type": "follow_up",
                        "created_at": now_iso,
                        "updated_at": now_iso,
                    }
                ]
            )
            return chain
        return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    response = client.post(TARGET_PATH)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "action_1_text" in data
    assert data["action_1_type"] == "prepare_questions"
    mock_openai_chat.assert_called_once()


def test_generate_daily_focus_fallback_on_ai_failure(mock_supabase):
    """Verifies fallback heuristics activate automatically if OpenAI errors out."""
    with patch(
        "src.api.daily_focus._chat", side_effect=RuntimeError("API Outage")
    ):
        today_str = date.today().strftime("%Y-%m-%d")
        now_iso = datetime.now(UTC).isoformat()

        def side_effect_mock(table_name):
            if table_name == "users":
                return mock_supabase._create_chain([{"anxiety_level": 2.0}])
            elif table_name == "jobs":
                return mock_supabase._create_chain(
                    [
                        {
                            "company": "Netflix",
                            "role": "Engineer",
                            "status": "applied",
                            "last_moved_at": today_str,
                        }
                    ]
                )
            elif table_name == "daily_focus":
                chain = mock_supabase._create_chain()
                chain.execute.return_value = MagicMock(
                    data=[
                        {
                            "id": str(uuid4()),
                            "user_id": TEST_USER_UUID,
                            "date": today_str,
                            "action_1_text": "Apply to 3 more positions.",
                            "action_1_type": "add_applications",
                            "action_2_text": "Keep tracking your process.",
                            "action_2_type": "follow_up",
                            "created_at": now_iso,
                            "updated_at": now_iso,
                        }
                    ]
                )
                return chain
            return mock_supabase._create_chain([])

        mock_supabase.table.side_effect = side_effect_mock

        response = client.post(TARGET_PATH)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["action_1_type"] == "add_applications"
