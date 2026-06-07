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
        # Fixed: Directly returns the mock instance instead of a lambda function
        mock_get_client.return_value = mock_client
        yield mock_client


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


def test_get_insights_with_real_gemini_call(mock_supabase):
    """Hits the live Gemini endpoint to verify prompt layout logic."""
    mock_sessions = [
        {
            "id": f"s_{i}",
            "completed": True,
            "completed_at": datetime.now(UTC).isoformat(),
            "pre_score": 50.0,
            "post_score": 70.0 + i,
            "session_type": "prepare_questions",
            "phase_1_complete": True,
            "pre_emotion": "anxious",
            "post_confidence": 65.0,
            "post_calmness": 60.0,
        }
        for i in range(4)
    ]

    def side_effect_mock(table_name):
        if table_name == "users":
            return mock_supabase._create_chain(
                [
                    {
                        "goal": "Backend Engineer",
                        "stage": "applying",
                        "anxiety_level": "medium",
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
        assert len(insight["text"].split()) <= 8

    assert "·" in data["hiring_funnel_gap"]["based_on"]
    print(f"\n[LIVE INSIGHT RUN]: {data['top_insights'][0]['text']}")