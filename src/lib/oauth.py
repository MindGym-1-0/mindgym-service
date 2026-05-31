"""Google OAuth utilities and token management"""
import asyncio
import urllib.parse
import httpx
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
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


async def verify_google_token(id_token: str) -> dict:
    """
    Verify and decode Google ID token using Google's public keys

    This verifies the cryptographic signature, expiration, issuer, and audience
    in a single secure call using Google's official oauth2 library.

    Args:
        id_token: JWT token from Google

    Returns:
        Decoded token payload

    Raises:
        ValueError: If token verification fails (invalid signature, expired, wrong audience, etc.)
    """
    try:
        decoded = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            id_token,
            google_requests.Request(),
            audience=settings.google_client_id,
        )
        return decoded
    except ValueError as e:
        raise ValueError(f"Token verification failed: {e}")