import logging
from typing import Any, Optional

import jwt
from fastapi import Cookie, Header, HTTPException, status
from pydantic import ValidationError

from src.lib.auth_service import fetch_authenticated_user
from src.lib.config import get_settings

logger = logging.getLogger(__name__)


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer" or not token:
        return None

    return token.strip()


def _extract_cookie_token(access_token_cookie: Optional[str]) -> Optional[str]:
    if access_token_cookie and access_token_cookie.strip():
        return access_token_cookie.strip()
    return None


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    access_token: Optional[str] = Cookie(default=None),
) -> dict[str, Any]:
    """Resolve the active user from bearer header or cookie and verify with Supabase."""

    token = _extract_bearer_token(authorization) or _extract_cookie_token(access_token)
    if not token:
        logger.warning("get_current_user: no token in request (header=%s, cookie=%s)", bool(authorization), bool(access_token))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        settings = get_settings()
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error",
        ) from exc

    if settings.resolved_supabase_jwt_secret:
        try:
            header = jwt.get_unverified_header(token)
            alg = header.get("alg", "")
            if alg in ("HS256", "HS384", "HS512"):
                jwt.decode(
                    token,
                    settings.resolved_supabase_jwt_secret,
                    algorithms=["HS256", "HS384", "HS512"],
                    options={"verify_aud": False},
                )
            else:
                # Asymmetric algorithm (ES256, RS256, etc.) — skip local
                # verification and let fetch_authenticated_user validate via
                # Supabase API which has the correct public key.
                logger.debug("JWT uses asymmetric alg=%s — skipping local verify", alg)
        except jwt.PyJWTError as exc:
            logger.warning("get_current_user: JWT decode failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc
    else:
        logger.debug(
            "JWT secret not configured; using Supabase token validation fallback"
        )

    user = await fetch_authenticated_user(token)
    if not user:
        logger.warning("get_current_user: fetch_authenticated_user returned None for token prefix=%s", token[:12] if token else "none")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized user",
        )

    return user
