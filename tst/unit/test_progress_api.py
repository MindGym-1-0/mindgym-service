from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import MagicMock, patch
from uuid import uuid4

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
        import inspect

        sig = inspect.signature(progress.get_progress)
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
    """Fixture to intercept Supabase clients and provide a chained constructor."""
    with patch("src.api.progress.get_supabase_user_client") as mock_get_client:
        mock_client = MagicMock()

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

            mock_execution = MagicMock()
            mock_execution.data = return_data or []
            chain.execute.return_value = mock_execution
            return chain

        mock_client._create_chain = create_mock_chain
        mock_get_client.return_value = mock_client
        yield mock_client


def test_get_progress_with_real_gemini(mock_supabase):
    """Hits the real Gemini API using your native chained database routing."""

    mock_session_record = {
        "id": str(uuid4()),
        "completed": True,
        "completed_at": datetime.now(UTC).isoformat(),
        "pre_score": 50.0,
        "post_score": 75.0,
        "confidence": 75.0,
        "clarity": 60.0,
        "calmness": 40.0,  # Explicitly low metric dimension
        "focus": 70.0,
    }

    def side_effect_mock(table_name):
        if table_name == "streaks":
            return mock_supabase._create_chain([{"current_streak": 4}])
        elif table_name in ["sessions", "ai_sessions"]:
            return mock_supabase._create_chain([mock_session_record])
        else:
            return mock_supabase._create_chain([])

    mock_supabase.table.side_effect = side_effect_mock

    # Execute request using TestClient over to the real active Google backend
    response = client.get("/api/progress?period=week")

    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()

    # Verify structural aggregations run smoothly
    assert res_data["sessions_done"] == 1
    assert "day_streak" in res_data

    # Validate structural properties returned from real Gemini generation
    assert "key_insight" in res_data
    assert isinstance(res_data["key_insight"], str)
    assert len(res_data["key_insight"]) > 0

    # Under 20 words check validation pass execution
    word_count = len(res_data["key_insight"].split())
    assert word_count <= 20

    print(f"\n[LIVE GEMINI INSIGHT OUTPUT]: {res_data['key_insight']}")
