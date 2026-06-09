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
TEST_USER_UUID = str(uuid4())
MOCK_TOKEN = "mocked-supabase-jwt-token"


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """Maps dynamic dependency overrides looking at exact route paths."""
    target_route = None
    for route in app.routes:
        # Fixed path evaluation to match internal APIRouter prefix configurations
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
            
            # Fluent mock properties for handling .not_.is_() column validations
            chain.not_ = chain
            chain.is_.return_value = chain
            
            chain.execute.return_value = MagicMock(data=return_data if return_data is not None else [])
            return chain

        mock_client._create_chain = create_mock_chain
        mock_get_client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_openai_chat():
    """Fixture to mock the internal OpenAI _chat function to prevent network hits."""
    with patch("src.api.progress._chat") as mock_chat_fn:
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
            return mock_supabase._create_chain({"current_streak": 5})
        return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    response = client.get("/api/progress?period=week")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Core schema fields assertion validation refactored
    assert data["sessions_done"] == 0
    assert data["day_streak"] == 5
    assert data["avg_lift_per_session"] == 0.0
    assert data["key_insight"] == ""


def test_get_progress_with_mocked_openai_call(mock_supabase, mock_openai_chat):
    """Verifies metrics assembly pipeline across production database keys."""
    mock_sessions = [
        {
            "id": f"session_{i}",
            "completed_at": datetime.now(UTC).isoformat(),
            "anxiety_level_before": 7.0,
            "anxiety_level_after": 4.0,
        }
        for i in range(4)
    ]

    def side_effect_mock(table_name):
        if table_name == "streaks":
            return mock_supabase._create_chain({"current_streak": 3})
        elif table_name == "ai_sessions":
            return mock_supabase._create_chain(mock_sessions)
        return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    response = client.get("/api/progress?period=week")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Updated metrics evaluating accurate calculated schema values (7.0 - 4.0 = 3.0 lift)
    assert data["sessions_done"] == 4
    assert data["day_streak"] == 3
    assert data["avg_lift_per_session"] == 3.0
    assert "Clarity" in data["key_insight"]
    mock_openai_chat.assert_called_once()
