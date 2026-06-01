from src.lib.tokens import extract_access_token_from_request


def test_extract_access_token_from_plain_access_cookie():
    token = extract_access_token_from_request(
        auth_header=None,
        cookies={"access_token": "plain-cookie-token"},
    )
    assert token == "plain-cookie-token"


def test_extract_access_token_prefers_bearer_over_cookie():
    token = extract_access_token_from_request(
        auth_header="Bearer bearer-token",
        cookies={"access_token": "plain-cookie-token"},
    )
    assert token == "bearer-token"

