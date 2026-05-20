import pytest

from src.lib.auth_dependencies import _extract_bearer_token, _extract_cookie_token


@pytest.mark.unit
def test_extract_bearer_token_missing_header_returns_none():
    assert _extract_bearer_token(None) is None


@pytest.mark.unit
def test_extract_bearer_token_wrong_scheme_returns_none():
    assert _extract_bearer_token("Basic abc123") is None


@pytest.mark.unit
def test_extract_bearer_token_empty_bearer_returns_none():
    assert _extract_bearer_token("Bearer ") is None


@pytest.mark.unit
def test_extract_bearer_token_valid_bearer_returns_token():
    assert _extract_bearer_token("Bearer mytoken") == "mytoken"


@pytest.mark.unit
def test_extract_bearer_token_extra_whitespace_returns_trimmed_token():
    assert _extract_bearer_token("Bearer   mytoken") == "mytoken"


@pytest.mark.unit
def test_extract_cookie_token_missing_cookie_returns_none():
    assert _extract_cookie_token(None) is None


@pytest.mark.unit
def test_extract_cookie_token_empty_cookie_returns_none():
    assert _extract_cookie_token("   ") is None


@pytest.mark.unit
def test_extract_cookie_token_valid_cookie_returns_token():
    assert _extract_cookie_token("cookie-token") == "cookie-token"
