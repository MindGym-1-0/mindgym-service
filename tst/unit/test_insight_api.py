from __future__ import annotations

import inspect
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)
TEST_USER_UUID = uuid4()
MOCK_TOKEN = "mocked-supabase-jwt-token"


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """Maps dynamic dependency overrides looking at exact route paths."""
    target_route = None
    for route in app.routes:
        if getattr(route, "path", None) == "/api/insights":
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
        from src.api import insights

        sig = inspect.signature(insights.get_insights)
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
    with patch("src.api.insights.get_supabase_user_client") as mock_get_client:
        mock_client = MagicMock()

        def create_mock_chain(return_data=None):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.execute.return_value = MagicMock(data=return_data or [])
            return chain

        mock_client._create_chain = create_mock_chain
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openai_chat():
    """Fixture to mock the internal OpenAI _chat function to prevent network hits."""
    with patch("src.api.insights._chat") as mock_chat_fn:
        mock_json_payload = """
        {
          "top_insights": [
            {"text": "Morning Focus Works", "detail": "Anxiety drops 2.5 pts."},
            {"text": "Pipeline Static", "detail": "Zero new interviews track."}
          ],
          "secondary_insights": [
            {"text": "Keep utilizing structured calming routines."},
            {"text": "Review your upcoming mock test schedules."},
            {"text": "Consistency across weeks preserves retention."}
          ],
          "hiring_funnel_gap": {
            "title": "Hiring Funnel Gap Identified",
            "body": "Expand application streams to hit baseline markers.",
            "based_on": "4 sessions · Delta 2.0 · Active 100%"
          }
        }
        """
        mock_chat_fn.return_value = mock_json_payload
        yield mock_chat_fn


def test_get_insights_empty_state_fewer_than_3_sessions(mock_supabase):
    """Verifies empty bounds state if a user has fewer than 3 sessions."""

    def side_effect_mock(table_name):
        if table_name == "ai_sessions":
            return mock_supabase._create_chain(
                [{"id": "s1", "completed": True}]
            )
        return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    response = client.get("/api/insights")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["top_insights"] == []
    assert data["secondary_insights"] == []
    assert data["hiring_funnel_gap"] is None


def test_get_insights_with_mocked_openai_call(mock_supabase, mock_openai_chat):
    """Verifies full workflow mapping metrics across production database keys."""
    mock_sessions = [
        {
            "id": f"s_{i}",
            "completed": True,
            "completed_at": datetime.now(UTC).isoformat(),
            "anxiety_level_before": 5.0,
            "anxiety_level_after": 3.0,
            "preparation_for": "Technical Interview",
        }
        for i in range(4)
    ]

    def side_effect_mock(table_name):
        if table_name == "users":
            return mock_supabase._create_chain(
                [
                    {
                        "target_role_category": "Backend Engineer",
                        "employment_status": "applying",
                        "emotional_challenge": "anxiety",
                    }
                ]
            )
        elif table_name == "ai_sessions":
            return mock_supabase._create_chain(mock_sessions)
        elif table_name in ["jobs", "interviews"]:
            return mock_supabase._create_chain([{"id": "j1"}])
        return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    response = client.get("/api/insights")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert len(data["top_insights"]) == 2
    assert len(data["secondary_insights"]) == 3
    assert data["hiring_funnel_gap"] is not None

    for insight in data["top_insights"]:
        assert insight["highlight"] is True

    assert "·" in data["hiring_funnel_gap"]["based_on"]
    mock_openai_chat.assert_called_once()
