"""Onboarding endpoints for user setup"""

import uuid

import httpx
from fastapi import APIRouter, HTTPException, status

from src.lib.config import settings
from src.lib.supabase import insert_onboarding_record
from src.types.models import OnboardingRequest, OnboardingResponse

router = APIRouter(prefix="/api", tags=["onboarding"])


@router.post(
    "/onboard",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete user onboarding",
    description="Receives user's job goal, job search stage, and anxiety level to personalize their experience",
)
async def onboard(request: OnboardingRequest) -> OnboardingResponse:
    """
    Complete the onboarding process for a new user.

    This endpoint collects three pieces of information used to personalize the user's daily sessions,
    meditation recommendations, and action suggestions.

    Args:
        request: OnboardingRequest containing job_goal, job_search_stage, and anxiety_level

    Returns:
        OnboardingResponse with success status and user_id

    Raises:
        HTTPException: If onboarding data is invalid or the persistence layer fails
    """
    try:
        record = {
            "goal": request.job_goal,
            "stage": request.job_search_stage.value,
        }

        persisted = {}
        if settings.supabase_url and settings.supabase_key:
            persisted = await insert_onboarding_record(record)

        user_id = persisted.get("user_id") or persisted.get("id") or str(uuid.uuid4())

        return OnboardingResponse(
            success=True,
            message="Onboarding completed successfully",
            user_id=user_id,
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase returned {e.response.status_code}: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase request failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Onboarding failed: {str(e)}",
        )
