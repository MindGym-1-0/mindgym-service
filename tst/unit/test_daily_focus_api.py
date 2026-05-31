from __future__ import annotations

from datetime import date, datetime, UTC
from uuid import uuid4
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app

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


def test_generate_daily_focus_with_real_gemini(mock_supabase):
    """Hits the real Gemini API to verify payload schema generation using real context tracking data."""

    final_db_record = {
        "id": str(uuid4()),
        "user_id": str(TEST_USER_UUID),
        "date": date.today().strftime("%Y-%m-%d"),
        "action_1_text": "Live engine structural target text.",
        "action_1_type": "PREPARE_INTERVIEW",
        "action_2_text": "Live engine validation pass text.",
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
                        "stage": "applying",
                        "anxiety_level": "medium",
                    }
                ]
            )
        elif table_name == "jobs":
            return mock_supabase._create_chain(
                [
                    {
                        "company": "Google",
                        "role": "Software Engineer",
                        "stage": "applied",
                        "last_moved_at": date.today().strftime("%Y-%m-%d"),
                    }
                ]
            )
        elif table_name == "interviews":
            return mock_supabase._create_chain([])
        elif table_name == "ai_sessions":
            return mock_supabase._create_chain([])
        elif table_name == "streaks":
            return mock_supabase._create_chain([{"current_streak": 5}])
        elif table_name in ["daily_focus", "daily_focuses"]:
            return mock_supabase._create_chain([final_db_record])
        else:
            return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    # Execute request over the real network to the active Google API endpoint
    response = client.post("/api/daily-focus/generate")

    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()

    # Structural validations verify schema conformity from the live production response mapping
    assert "action_1_text" in res_data
    assert "action_1_type" in res_data
    assert "action_2_text" in res_data
    assert "action_2_type" in res_data
