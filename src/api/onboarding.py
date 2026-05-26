"""Onboarding endpoints for user setup"""

from fastapi import APIRouter, HTTPException, status

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client
from src.types.models import OnboardingRequest, OnboardingResponse

router = APIRouter(prefix="/api", tags=["onboarding"])


@router.post(
    "/onboard",
    response_model=OnboardingResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete user onboarding",
    description="Receives user's job goal, job search stage, and mood to personalize their experience",
)
async def onboard(
    request: OnboardingRequest,
    user_id: CurrentUserId,
    token: CurrentUserToken,
) -> OnboardingResponse:
    client = get_supabase_user_client(token)

    try:
        result = await (
            client.table("users")
            .update({
                "goal": request.job_goal,
                "stage": request.job_search_stage.value,
                "mood": request.mood,
            })
            .eq("id", str(user_id))
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to update user record: {exc}",
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User record not found.",
        )

    return OnboardingResponse(
        success=True,
        message="Onboarding completed successfully",
        user_id=str(result.data[0].get("id", user_id)),
    )
