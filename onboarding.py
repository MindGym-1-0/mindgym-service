"""Onboarding endpoints for user setup"""
from fastapi import APIRouter, HTTPException, status
from src.types.models import OnboardingRequest, OnboardingResponse

router = APIRouter(prefix="/api", tags=["onboarding"])


@router.post(
    "/onboard",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Complete user onboarding",
    description="Receives user's job goal, job search stage, and anxiety level to personalize their experience"
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
        HTTPException: If onboarding data is invalid
    """
    try:
        return OnboardingResponse(
            success=True,
            message="Onboarding completed successfully",
            user_id="user_123"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Onboarding failed: {str(e)}"
        )
