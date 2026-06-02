import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.lib.auth import require_current_user_id, require_current_user_token

# Use a structurally valid UUID to ensure validation logic handles it smoothly
TEST_USER_ID = str(uuid.uuid4())
TEST_TOKEN = "fake-jwt-token"


@pytest.fixture
def mock_supabase():
    """Per-test scoped fixture to prevent mock state and call counters
    from bleeding across separate test executions.
    """
    return MagicMock()


@pytest.fixture(autouse=True)
def setup_dependencies(mock_supabase):
    """Overriding explicit FastAPI dependencies and patching the core utility function
    to eliminate network connectivity assumptions.
    """
    app.dependency_overrides[require_current_user_id] = lambda: TEST_USER_ID
    app.dependency_overrides[require_current_user_token] = lambda: TEST_TOKEN

    with patch(
        "src.api.weekly_mission.get_supabase_user_client", return_value=mock_supabase
    ):
        yield

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def create_mock_chain(return_data: list) -> MagicMock:
    """Helper utility to mimic fluent builders common in Supabase Postgrest queries.

    Ensures that any sequence of chained builders (.select(), .eq(), etc.)
    ultimately evaluates to a structure where '.data' is a real, serializable list.
    """
    mock_query_layer = MagicMock()

    # Configure the terminal execution layer
    mock_execution_result = MagicMock()
    mock_execution_result.data = return_data

    # Ensure calling execute() or accessing it as an attribute returns the data container
    mock_query_layer.execute.return_value = mock_execution_result
    mock_query_layer.execute.data = return_data

    # Self-referential cascading loop for chain queries (e.g., sb.table().select().eq())
    mock_query_layer.select.return_value = mock_query_layer
    mock_query_layer.eq.return_value = mock_query_layer
    mock_query_layer.gte.return_value = mock_query_layer
    mock_query_layer.order.return_value = mock_query_layer
    mock_query_layer.limit.return_value = mock_query_layer
    mock_query_layer.is_.return_value = mock_query_layer
    mock_query_layer.update.return_value = mock_query_layer
    mock_query_layer.insert.return_value = mock_query_layer

    return mock_query_layer


def test_generate_weekly_mission_with_real_gemini(client, mock_supabase):
    """Hits the real Gemini API to verify prompt structural rendering and token parsing.

    Ensures structural data cleanly interoperates with gemini-2.5-flash.
    """
    # Define payload target that Supabase will hand back on successful insert or lookup
    final_db_record = {
        "id": str(uuid.uuid4()),
        "user_id": TEST_USER_ID,
        "week_start_date": "2026-06-01",
        "action_1": "Live engine generation validation target.",
        "action_1_completed": False,
        "action_2": "Live engine structural pass action.",
        "action_2_completed": False,
        "action_3": "Live engine schema conformity check.",
        "action_3_completed": False,
        "completion_count": 0,
        "generated_at": "2026-05-27T23:30:00+00:00",
        "updated_at": "2026-05-27T23:30:00+00:00",
    }

    # Robust table side-effect router pattern matching test_daily_focus_api.py
    def table_side_effect(table_name: str):
        data_map = {
            "users": [{"goal": "Backend Engineer", "stage": "Interviewing"}],
            "jobs": [],  # Empty array drops down cleanly to baseline constraints
            "ai_sessions": [],  # Returns no sessions smoothly
            "weekly_mission": [final_db_record],
        }
        return create_mock_chain(data_map.get(table_name, []))

    # Bind the router to our table initialization endpoint
    mock_supabase.table.side_effect = table_side_effect

    # Execute request hitting the real Gemini model configured in your API router
    response = client.post("/api/weekly-mission/generate")

    assert response.status_code == 200
    json_data = response.json()

    # Assertions confirm the structural integrity of fields returned by the endpoint mapping logic
    assert "action_1" in json_data
    assert "action_2" in json_data
    assert "action_3" in json_data
    assert json_data["completion_count"] == 0
