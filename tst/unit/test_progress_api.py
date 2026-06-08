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
        if getattr(route, "path", None) == "/api/progress":
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
        from src.api import progress

        sig = inspect.signature(progress.get_progress)
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
    with patch("src.api.progress.get_supabase_user_client") as mock_get_client:
        mock_client = MagicMock()

        def create_mock_chain(return_data=None):
            chain = MagicMock()
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.gte.return_value = chain
            chain.maybe_single.return_value = chain
            chain.order.return_value = chain
            chain.execute.return_value = MagicMock(data=return_data or [])
            return chain

        mock_client._create_chain = create_mock_chain
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openai_chat():
    """Fixture to mock the internal OpenAI _chat function to prevent network hits."""
    with patch("src.api.progress._chat") as mock_chat_fn:
        # Returns structured text following the schema structure exactly
        mock_json_payload = """
        {
          "key_insight": "Clarity is trending up this week. Focus on morning deep-work intervals."
        }
        """
        mock_chat_fn.return_value = mock_json_payload
        yield mock_chat_fn


def test_get_progress_empty_state_no_sessions(mock_supabase):
    """Verifies response defaults when user has zero completed sessions."""

    def side_effect_mock(table_name):
        if table_name == "streaks":
            # Test helper for table dictionary checks
            chain = mock_supabase._create_chain()
            chain.execute.return_value = MagicMock(
                data={"current_streak": 5}
            )
            return chain
        return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    response = client.get("/api/progress?period=week")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["sessions_done"] == 0
    assert data["day_streak"] == 5
    assert data["avg_confidence"] == 0.0
    assert data["key_insight"] == ""


def test_get_progress_with_mocked_openai_call(mock_supabase, mock_openai_chat):
    """Verifies metrics assembly pipeline across production database keys."""
    mock_sessions = [
        {
            "id": f"session_{i}",
            "completed": True,
            "completed_at": datetime.now(UTC).isoformat(),
            "anxiety_level_before": 7.0,
            "anxiety_level_after": 4.0,
            "confidence": 6.0,
            "clarity": 5.0,
            "calmness": 8.0,
            "focus": 7.0,
        }
        for i in range(4)
    ]

    def side_effect_mock(table_name):
        if table_name == "streaks":
            chain = mock_supabase._create_chain()
            chain.execute.return_value = MagicMock(
                data={"current_streak": 3}
            )
            return chain
        elif table_name == "ai_sessions":
            return mock_supabase._create_chain(mock_sessions)
        return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    response = client.get("/api/progress?period=week")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["sessions_done"] == 4
    assert data["day_streak"] == 3
    assert data["avg_confidence"] == 6.0
    assert "Clarity" in data["key_insight"]
    mock_openai_chat.assert_called_once()