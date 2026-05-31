"""Google OAuth utilities and token management"""
import urllib.parse
import httpx
from src.lib.config import settings


def get_google_auth_url() -> str:
    """Generate the Google OAuth2 consent screen URL."""
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"


async def exchange_auth_code_for_token(code: str) -> dict:
    """
    Exchange Google authorization code for tokens

    Args:
        code: Authorization code from Google OAuth flow

    Returns:
        Dictionary containing id_token, access_token, and other OAuth token info

    Raises:
        ValueError: If token exchange fails
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise ValueError("Google OAuth credentials not configured")

    token_url = "https://oauth2.googleapis.com/token"

    payload = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=payload)

        if response.status_code != 200:
            raise ValueError(f"Failed to exchange code for token: {response.text}")

        return response.json()
