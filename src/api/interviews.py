from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.supabase import get_supabase_user_client

router = APIRouter()
logger = logging.getLogger(__name__)


class InterviewCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    interview_date: str = Field(..., min_length=1)
    event_type: str | None = None
    job_id: str | None = None
    notes: str | None = None


class InterviewResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    company: str
    role: str
    interview_date: str
    event_type: str | None = None
    job_id: str | None = None
    notes: str | None = None
    created_at: str | None = None


class InterviewListResponse(BaseModel):
    upcoming: list[InterviewResponse]
    past: list[InterviewResponse]


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
            .select("id,user_id,company,role,interview_date,event_type,job_id,notes,created_at")
            .eq("user_id", user_id)
            .gte("interview_date", now_iso)
            .order("interview_date", desc=False)
            .execute
        )
        past_res = await asyncio.to_thread(
            sb.table("interviews")
            .select("id,user_id,company,role,interview_date,event_type,job_id,notes,created_at")
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

    insert_row: dict = {
        "user_id": user_id,
        "company": body.company.strip(),
        "role": body.role.strip(),
        "interview_date": body.interview_date,
    }
    if body.event_type:
        insert_row["event_type"] = body.event_type.strip()
    if body.job_id:
        insert_row["job_id"] = body.job_id
    if body.notes:
        insert_row["notes"] = body.notes.strip()

    try:
        result = await asyncio.to_thread(
            sb.table("interviews")
            .insert(insert_row)
            .select("id,user_id,company,role,interview_date,event_type,job_id,notes,created_at")
            .execute
        )
    except Exception:
        logger.exception("Failed to create interview.")
        raise HTTPException(status_code=500, detail="Unable to create interview.") from None

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create interview.")

    return InterviewResponse.model_validate(result.data[0])


@router.delete("/{interview_id}", status_code=204)
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
