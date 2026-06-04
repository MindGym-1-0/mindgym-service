from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, Request

from src.lib import config
from src.lib.tokens import extract_access_token_from_request

logger = logging.getLogger(__name__)


async def fetch_supabase_user_id(access_token: str) -> UUID:
    base = config.supabase_url()
    url = f"{base.rstrip('/')}/auth/v1/user"
    api_key = config.supabase_anon_key()

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Server missing SUPABASE_ANON_KEY",
        )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": api_key,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=15.0)
    except httpx.HTTPError:
        logger.exception("Supabase auth request failed.")
        raise HTTPException(status_code=401, detail="Unauthorized") from None

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = resp.json()
    except ValueError:
        raise HTTPException(status_code=401, detail="Unauthorized") from None

    user_id = data.get("id")
    try:
        return UUID(str(user_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Unauthorized") from None


def require_current_user_token(request: Request) -> str:
    token = extract_access_token_from_request(
        auth_header=request.headers.get("authorization"),
        cookies=dict(request.cookies),
    )
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not config.supabase_url():
        raise HTTPException(status_code=500, detail="Server missing SUPABASE_URL")

    return token


async def require_current_user_id(
    token: str = Depends(require_current_user_token),
) -> UUID:
    return await fetch_supabase_user_id(token)


CurrentUserId = Annotated[UUID, Depends(require_current_user_id)]
CurrentUserToken = Annotated[str, Depends(require_current_user_token)]
