from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.lib.auth import require_current_user_id, require_current_user_token
from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.unit
def test_login_returns_session_tokens_for_client(client):
    auth_result = {
        "authenticated": True,
        "user": {
            "id": "user-123",
            "email": "user@test.dev",
            "phone": None,
            "app_metadata": {},
            "user_metadata": {},
        },
        "session": {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "expires_in": 3600,
        },
    }

    with patch(
        "src.api.auth.login_with_email_password",
        new_callable=AsyncMock,
        return_value=auth_result,
    ):
        response = client.post(
            "/api/auth/login",
            json={"email": "user@test.dev", "password": "secret"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["session"]["access_token"] == "access-token"
    assert body["session"]["refresh_token"] == "refresh-token"


@pytest.mark.unit
def test_auth_me_returns_full_authenticated_user_profile(client):
    user_payload = {
        "id": "user-123",
        "email": "user@test.dev",
        "phone": None,
        "app_metadata": {"provider": "email"},
        "user_metadata": {"first_name": "Test", "last_name": "User"},
    }

    app.dependency_overrides[require_current_user_id] = lambda: "user-123"
    app.dependency_overrides[require_current_user_token] = lambda: "access-token"

    with patch(
        "src.api.auth.fetch_authenticated_user",
        new_callable=AsyncMock,
        return_value=user_payload,
    ):
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer access-token"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["id"] == "user-123"
    assert body["user"]["email"] == "user@test.dev"

    app.dependency_overrides.pop(require_current_user_id, None)
    app.dependency_overrides.pop(require_current_user_token, None)
