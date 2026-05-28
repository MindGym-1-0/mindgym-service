from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

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
