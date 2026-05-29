"""Onboarding endpoints for user setup"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth_dependencies import get_current_user
from src.lib.supabase_client import get_supabase_admin_client
from src.types.models import OnboardingRequest, OnboardingResponse

router = APIRouter(prefix="/api", tags=["onboarding"])
logger = logging.getLogger(__name__)


@router.post(
    "/onboard",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete user onboarding",
    description="Receives user's job goal, job search stage, and anxiety level to personalize their experience",
)
async def onboard(
    request: OnboardingRequest,
    current_user: dict = Depends(get_current_user),
) -> OnboardingResponse:
    """
    Complete the onboarding process for a new user.

    Inserts a row into public.users with the authenticated user's id,
    job goal, job search stage, and anxiety level.
    """
    user_id = current_user["id"]
    record = {
        "id": user_id,
        "goal": request.job_goal,
        "stage": request.job_search_stage.value,
        "anxiety_level": request.anxiety_level,
    }

    try:
        client = get_supabase_admin_client()
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database client not available — SUPABASE_SERVICE_ROLE_KEY is missing",
            )

        await asyncio.to_thread(
            lambda: client.table("users").insert(record).execute()
        )

        return OnboardingResponse(
            success=True,
            message="Onboarding completed successfully",
            user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Onboarding failed for user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Onboarding failed: {exc}",
        ) from exc
