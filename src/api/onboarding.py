"""Onboarding endpoints for user setup"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.lib.auth_dependencies import get_current_user
from src.lib.supabase_client import get_supabase_admin_client
from src.types.models import OnboardingRequest, OnboardingResponse
from src.lib.prompt_builder import derive_preparation_for
from src.types.models import OnboardingGapAnalysis, OnboardingFirstSession
from src.lib.session_service import insert_onboarding_session
from src.lib.gemini_service import analyze_onboarding, generate_onboarding_script

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
        "employment_status": request.employment_status,
        "unemployed_duration": request.unemployed_duration,
        "job_timeline": request.job_timeline,
        "target_role_category": request.target_role_category,
        "target_role_note": request.target_role_note,
        "company_types": request.company_types,
        "applications_sent_min": request.applications_sent_min,
        "applications_sent_max": request.applications_sent_max,
        "recruiter_contacts": request.recruiter_contacts,
        "first_round_interviews": request.first_round_interviews,
        "final_round_interviews": request.final_round_interviews,
        "offers": request.offers,
        "emotional_challenge": request.emotional_challenge,
        "baseline_anxiety": request.baseline_anxiety
    }

    try:
        client = get_supabase_admin_client()
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database client not available — SUPABASE_SERVICE_ROLE_KEY is missing",
            )

        await asyncio.to_thread(
            lambda: client.table("users").upsert(record, on_conflict="id").execute()
        )

        preparation_for = derive_preparation_for(
            employment_status=request.employment_status,
            emotional_challenge=request.emotional_challenge,
            job_timeline=request.job_timeline,
        )

        gap_analysis = await asyncio.to_thred(
            lambda: analyze_onboarding(employment_status=request.employment_status,
                        unemployed_duration=request.unemployed_duration,
                        job_timeline=request.job_timeline,
                        target_role_category=request.target_role_category,
                        target_role_note=request.target_role_note,
                        company_types=request.company_types,
                        applications_sent_min=request.applications_sent_min,
                        applications_sent_max=request.applications_sent_max,
                        recruiter_contacts=request.recruiter_contacts,
                        first_round_interviews=request.first_round_interviews,
                        final_round_interviews=request.final_round_interviews,
                        offers=request.offers,
                        emotional_challenge=request.emotional_challenge,
                        baseline_anxiety=request.baseline_anxiety,
                        preparation_for=preparation_for
                    )
        )
        onboarding_session = await asyncio.to_thred(
            lambda: generate_onboarding_script(employment_status=request.employment_status,
                        unemployed_duration=request.unemployed_duration,
                        job_timeline=request.job_timeline,
                        target_role_category=request.target_role_category,
                        target_role_note=request.target_role_note,
                        company_types=request.company_types,
                        applications_sent_min=request.applications_sent_min,
                        applications_sent_max=request.applications_sent_max,
                        recruiter_contacts=request.recruiter_contacts,
                        first_round_interviews=request.first_round_interviews,
                        final_round_interviews=request.final_round_interviews,
                        offers=request.offers,
                        emotional_challenge=request.emotional_challenge,
                        baseline_anxiety=request.baseline_anxiety,
                        preparation_for=preparation_for
                        )
        )

        session_id = await insert_onboarding_session(user_id=user_id,
            preparation_for=preparation_for,
            baseline_anxiety=request.baseline_anxiety,
            script=onboarding_session,
        )

        return OnboardingResponse(
            success=True,
            user_id=user_id,
            gap_analysis=OnboardingGapAnalysis(
                mindset_gap=gap_analysis["mindset_gap"],
                mindset_gap_detail=gap_analysis["mindset_gap_detail"],
                hunting_gap=gap_analysis.get("hunting_gap"),
                hunting_gap_detail=gap_analysis.get("hunting_gap_detail"),
                baseline_anxiety_note=gap_analysis["baseline_anxiety_note"],
            ),
            first_session=OnboardingFirstSession(
                session_id=session_id,
                preparation_for=preparation_for,
                session_title=gap_analysis["session_title"],
                session_description=gap_analysis["session_description"],
                session_tags=gap_analysis["session_tags"],
                script=onboarding_session,
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Onboarding failed for user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Onboarding failed: {exc}",
        ) from exc
