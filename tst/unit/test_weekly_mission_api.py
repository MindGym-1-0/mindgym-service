from __future__ import annotations

import inspect
from datetime import date, datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)
TEST_USER_UUID = str(uuid4())
MOCK_TOKEN = "mocked-supabase-jwt-token"
TARGET_PATH = "/api/weekly-mission/generate"


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
        from src.api import weekly_mission

        sig = inspect.signature(weekly_mission.generate_weekly_mission)
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
        "src.api.weekly_mission.get_supabase_user_client"
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
def mock_openai_parse():
    """Fixture to mock OpenAI structured outputs async parsing endpoint."""
    with patch(
        "src.api.weekly_mission.openai_client.beta.chat.completions.parse",
        new_callable=AsyncMock,
    ) as mock_parse:
        # Construct the mock response layout expected by the parser
        mock_parsed_payload = MagicMock()
        mock_parsed_payload.action_1 = "Apply to 2 backend engine positions."
        mock_parsed_payload.action_2 = "Practice 2 systems design sessions."
        mock_parsed_payload.action_3 = "Document post-session debrief notes."

        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_parsed_payload

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_parse.return_value = mock_response
        yield mock_parse


def test_generate_weekly_mission_success(mock_supabase, mock_openai_parse):
    """Verifies weekly targets compile via Supabase profiles and OpenAI."""
    today_str = date.today().strftime("%Y-%m-%d")
    now_iso = datetime.now(UTC).isoformat()

    def side_effect_mock(table_name):
        if table_name == "users":
            return mock_supabase._create_chain(
                [{"goal": "Backend Dev", "stage": "Applying"}]
            )
        elif table_name == "jobs":
            return mock_supabase._create_chain(
                [{"id": "job_1", "status": "applied"}]
            )
        elif table_name == "ai_sessions":
            return mock_supabase._create_chain([{"anxiety_level_delta": -0.5}])
        elif table_name == "weekly_mission":
            # This side effect covers both verification selects and inserts
            chain = mock_supabase._create_chain()
            chain.execute.return_value = MagicMock(
                data=[
                    {
                        "id": str(uuid4()),
                        "user_id": TEST_USER_UUID,
                        "week_start_date": today_str,
                        "action_1": "Apply to 2 backend engine positions.",
                        "action_1_completed": False,
                        "action_2": "Practice 2 systems design sessions.",
                        "action_2_completed": False,
                        "action_3": "Document post-session debrief notes.",
                        "action_3_completed": False,
                        "completion_count": 0,
                        "generated_at": now_iso,
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
    assert data["action_1"] == "Apply to 2 backend engine positions."
    assert data["completion_count"] == 0
    mock_openai_parse.assert_called_once()


def test_generate_weekly_mission_fallback_on_exception(mock_supabase):
    """Ensures fallback heuristics execute gracefully if OpenAI drops."""
    with patch(
        "src.api.weekly_mission.openai_client.beta.chat.completions.parse",
        new_callable=AsyncMock,
        side_effect=RuntimeError("OpenAI Rate Limited"),
    ):
        today_str = date.today().strftime("%Y-%m-%d")
        now_iso = datetime.now(UTC).isoformat()

        def side_effect_mock(table_name):
            if table_name == "users":
                return mock_supabase._create_chain([])
            elif table_name == "jobs":
                return mock_supabase._create_chain([])
            elif table_name == "weekly_mission":
                chain = mock_supabase._create_chain()
                chain.execute.return_value = MagicMock(
                    data=[
                        {
                            "id": str(uuid4()),
                            "user_id": TEST_USER_UUID,
                            "week_start_date": today_str,
                            "action_1": "Target and submit at least 2 new backend engineering applications to expand your baseline pipeline.",
                            "action_1_completed": False,
                            "action_2": "Complete 2 practice mock sessions this week to initialize your competency tracking.",
                            "action_2_completed": False,
                            "action_3": "Book and complete a core system design mock study session to stabilize your weekly performance trends.",
                            "action_3_completed": False,
                            "completion_count": 0,
                            "generated_at": now_iso,
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
        # Verifies that it fell back to the local string-formatting rule
        assert "expand your baseline pipeline" in data["action_1"]
        assert "stabilize your weekly performance trends" in data["action_3"]
