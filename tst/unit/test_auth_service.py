from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.lib.auth_service import (
    AuthenticationError,
    UpstreamAuthServiceError,
    UserAlreadyExistsError,
    login_with_email_password,
    signup_with_email_password,
)


def _mock_client_with_auth(**auth_methods):
    auth = SimpleNamespace(**auth_methods)
    return SimpleNamespace(auth=auth)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_invalid_credentials_raises_authentication_error():
    client = _mock_client_with_auth(
        sign_in_with_password=lambda payload: (_ for _ in ()).throw(
            Exception("invalid login credentials")
        )
    )

    with patch("src.lib.auth_service.get_supabase_client", return_value=client):
        with pytest.raises(AuthenticationError):
            await login_with_email_password("user@test.dev", "bad-password")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_unexpected_upstream_error_raises_upstream_error():
    client = _mock_client_with_auth(
        sign_in_with_password=lambda payload: (_ for _ in ()).throw(
            Exception("connection refused")
        )
    )

    with patch("src.lib.auth_service.get_supabase_client", return_value=client):
        with pytest.raises(UpstreamAuthServiceError):
            await login_with_email_password("user@test.dev", "password")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_signup_existing_user_raises_user_already_exists_error():
    client = _mock_client_with_auth(
        sign_up=lambda payload: (_ for _ in ()).throw(Exception("user already exists"))
    )

    with patch("src.lib.auth_service.get_supabase_client", return_value=client):
        with pytest.raises(UserAlreadyExistsError):
            await signup_with_email_password("user@test.dev", "password")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_signup_upstream_error_raises_upstream_error():
    client = _mock_client_with_auth(
        sign_up=lambda payload: (_ for _ in ()).throw(Exception("connection refused"))
    )

    with patch("src.lib.auth_service.get_supabase_client", return_value=client):
        with pytest.raises(UpstreamAuthServiceError):
            await signup_with_email_password("user@test.dev", "password")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_success_returns_normalized_auth_payload():
    user = SimpleNamespace(
        id="abc-123",
        email="user@test.dev",
        phone="",
        app_metadata={"provider": "email"},
        user_metadata={"role": "candidate"},
    )
    session = SimpleNamespace(
        access_token="token-access",
        refresh_token="token-refresh",
        expires_in=3600,
        token_type="bearer",
    )
    response = SimpleNamespace(user=user, session=session)
    client = _mock_client_with_auth(sign_in_with_password=lambda payload: response)

    with patch("src.lib.auth_service.get_supabase_client", return_value=client):
        result = await login_with_email_password("user@test.dev", "password")

    assert result["authenticated"] is True
    assert result["user"]["id"] == "abc-123"
    assert result["user"]["email"] == "user@test.dev"
    assert result["session"]["access_token"] == "token-access"
    assert result["session"]["refresh_token"] == "token-refresh"
