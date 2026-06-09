from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client
from src.lib.subscription_service import can_create_interview, increment_interview_usage
from src.types.interview import (
    InterviewCreate,
    InterviewListResponse,
    InterviewOutcome,
    InterviewOutcomeResponse,
    InterviewOutcomeUpdate,
    InterviewResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

INTERVIEW_SELECT_FIELDS = (
    "id,user_id,company,role,interview_date,event_type,job_id,notes,"
    "outcome,check_in_attempts,next_check_in_at,created_at"
)
MAX_CHECK_IN_ATTEMPTS = 3
INTERVIEW_OUTCOME_SELECT_FIELDS = "id,outcome,check_in_attempts,next_check_in_at"


@router.get("", response_model=InterviewListResponse)
async def list_interviews(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> InterviewListResponse:
    sb = get_supabase_user_client(token)
    user_id = str(current_user_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        upcoming_res = await asyncio.to_thread(
            sb.table("interviews")
            .select(INTERVIEW_SELECT_FIELDS)
            .eq("user_id", user_id)
            .gte("interview_date", now_iso)
            .order("interview_date", desc=False)
            .limit(20)
            .execute
        )
        past_res = await asyncio.to_thread(
            sb.table("interviews")
            .select(INTERVIEW_SELECT_FIELDS)
            .eq("user_id", user_id)
            .lt("interview_date", now_iso)
            .order("interview_date", desc=True)
            .limit(20)
            .execute
        )
    except Exception:
        logger.exception("Failed to fetch interviews.")
        raise HTTPException(status_code=500, detail="Unable to fetch interviews.") from None

    upcoming = [InterviewResponse.model_validate(r) for r in (upcoming_res.data or [])]
    past = [InterviewResponse.model_validate(r) for r in (past_res.data or [])]

    return InterviewListResponse(upcoming=upcoming, past=past)


@router.post("", response_model=InterviewResponse, status_code=201)
async def create_interview(
    body: InterviewCreate,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> InterviewResponse:
    sb = get_supabase_user_client(token)
    user_id = str(current_user_id)
    
    # Check subscription tier limits for interviews
    can_create, error_message = await can_create_interview(user_id)
    if not can_create:
        raise HTTPException(
            status_code=403,
            detail=error_message or 'Interview limit reached for your subscription tier.',
        )

    insert_row: dict = {
        "user_id": user_id,
        "company": body.company.strip(),
        "role": body.role.strip(),
        "interview_date": body.interview_date.isoformat(),
        "event_type": body.event_type.strip(),
    }
    if body.job_id:
        insert_row["job_id"] = body.job_id
    if body.notes:
        insert_row["notes"] = body.notes.strip()

    try:
        result = await asyncio.to_thread(
            sb.table("interviews")
            .insert(insert_row)
            .select(INTERVIEW_SELECT_FIELDS)
            .execute
        )
        # Increment usage counter after interview is successfully created
        await increment_interview_usage(user_id)
    except Exception:
        logger.exception("Failed to create interview.")
        raise HTTPException(status_code=500, detail="Unable to create interview.") from None

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create interview.")

    return InterviewResponse.model_validate(result.data[0])


@router.patch("/{interview_id}/outcome", response_model=InterviewOutcomeResponse)
async def update_interview_outcome(
    interview_id: UUID,
    body: InterviewOutcomeUpdate,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> InterviewOutcomeResponse:
    sb = get_supabase_user_client(token)
    user_id = str(current_user_id)

    if body.from_not_ready and body.outcome != InterviewOutcome.NO_OFFER:
        raise HTTPException(
            status_code=422,
            detail="from_not_ready can only be used with outcome='no_offer'.",
        )

    try:
        existing = await asyncio.to_thread(
            sb.table("interviews")
            .select(INTERVIEW_OUTCOME_SELECT_FIELDS)
            .eq("id", str(interview_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute
        )
    except Exception:
        logger.exception("Failed to fetch interview outcome state.")
        raise HTTPException(status_code=500, detail="Unable to update interview outcome.") from None

    if not existing.data:
        raise HTTPException(status_code=404, detail="Interview not found.")

    current_row = existing.data[0]
    current_outcome = current_row.get("outcome")
    if current_outcome not in (
        None,
        InterviewOutcome.PENDING.value,
        InterviewOutcome.AWAITING.value,
    ):
        raise HTTPException(
            status_code=422,
            detail="Outcome is already finalized and cannot be updated.",
        )

    current_attempts = int(current_row.get("check_in_attempts") or 0)
    updates: dict[str, str | int | None] = {}

    if (
        body.outcome == InterviewOutcome.NO_OFFER
        and body.from_not_ready
    ):
        next_attempts = current_attempts + 1
        updates["check_in_attempts"] = next_attempts

        if next_attempts >= MAX_CHECK_IN_ATTEMPTS:
            updates["outcome"] = InterviewOutcome.NO_OFFER.value
            updates["next_check_in_at"] = None
        else:
            updates["outcome"] = InterviewOutcome.AWAITING.value
            updates["next_check_in_at"] = (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat()
    else:
        updates["outcome"] = body.outcome.value
        updates["next_check_in_at"] = None

    try:
        result = await asyncio.to_thread(
            sb.table("interviews")
            .update(updates)
            .eq("id", str(interview_id))
            .eq("user_id", user_id)
            .select(INTERVIEW_OUTCOME_SELECT_FIELDS)
            .execute
        )
    except Exception:
        logger.exception("Failed to persist interview outcome update.")
        raise HTTPException(status_code=500, detail="Unable to update interview outcome.") from None

    if not result.data:
        raise HTTPException(status_code=404, detail="Interview not found.")

    return InterviewOutcomeResponse.model_validate(result.data[0])


@router.patch("/{interview_id}/snooze-checkin", response_model=InterviewOutcomeResponse)
async def snooze_interview_checkin(
    interview_id: UUID,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> InterviewOutcomeResponse:
    sb = get_supabase_user_client(token)
    user_id = str(current_user_id)

    try:
        existing = await asyncio.to_thread(
            sb.table("interviews")
            .select(INTERVIEW_OUTCOME_SELECT_FIELDS)
            .eq("id", str(interview_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute
        )
    except Exception:
        logger.exception("Failed to fetch interview for snooze.")
        raise HTTPException(status_code=500, detail="Unable to snooze interview check-in.") from None

    if not existing.data:
        raise HTTPException(status_code=404, detail="Interview not found.")

    current_row = existing.data[0]
    current_outcome = current_row.get("outcome")
    if current_outcome not in (
        None,
        InterviewOutcome.PENDING.value,
        InterviewOutcome.AWAITING.value,
    ):
        raise HTTPException(
            status_code=422,
            detail="Interview check-in can only be snoozed while outcome is pending or awaiting.",
        )

    current_attempts = int(current_row.get("check_in_attempts") or 0)
    updates: dict[str, str | int | None] = {}

    if current_attempts >= MAX_CHECK_IN_ATTEMPTS:
        updates["check_in_attempts"] = current_attempts
        updates["outcome"] = InterviewOutcome.NO_OFFER.value
        updates["next_check_in_at"] = None
    else:
        next_attempts = current_attempts + 1
        updates["check_in_attempts"] = next_attempts
        if next_attempts >= MAX_CHECK_IN_ATTEMPTS:
            updates["outcome"] = InterviewOutcome.NO_OFFER.value
            updates["next_check_in_at"] = None
        else:
            updates["next_check_in_at"] = (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat()

    try:
        result = await asyncio.to_thread(
            sb.table("interviews")
            .update(updates)
            .eq("id", str(interview_id))
            .eq("user_id", user_id)
            .select(INTERVIEW_OUTCOME_SELECT_FIELDS)
            .execute
        )
    except Exception:
        logger.exception("Failed to persist interview snooze update.")
        raise HTTPException(status_code=500, detail="Unable to snooze interview check-in.") from None

    if not result.data:
        raise HTTPException(status_code=404, detail="Interview not found.")

    return InterviewOutcomeResponse.model_validate(result.data[0])


@router.delete(
    "/{interview_id}",
    status_code=204,
    response_class=Response,
    response_model=None,
)
async def delete_interview(
    interview_id: UUID,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
) -> None:
    sb = get_supabase_user_client(token)
    user_id = str(current_user_id)

    try:
        result = await asyncio.to_thread(
            sb.table("interviews")
            .delete()
            .eq("id", str(interview_id))
            .eq("user_id", user_id)
            .select("id")
            .execute
        )
    except Exception:
        logger.exception("Failed to delete interview.")
        raise HTTPException(status_code=500, detail="Unable to delete interview.") from None

    if not result.data:
        raise HTTPException(status_code=404, detail="Interview not found.")
