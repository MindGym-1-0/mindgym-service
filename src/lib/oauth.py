"""Google OAuth utilities and token management"""
import json
from typing import Optional
import httpx
import jwt
from datetime import datetime, timedelta
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from src.lib.config import settings


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


def verify_google_token(id_token: str) -> dict:
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
        decoded = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            audience=settings.google_client_id,
        )
        return decoded
    except ValueError as e:
        raise ValueError(f"Token verification failed: {e}")


def create_jwt_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token for authenticated user
    
    Args:
        user_id: Unique user identifier
        email: User email address
        expires_delta: Token expiration time delta (default: 24 hours)
        
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=24)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    
    return token


def verify_jwt_token(token: str) -> dict:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        ValueError: If token verification fails
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")
