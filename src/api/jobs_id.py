from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import ValidationError

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.errors import raise_400
from src.lib.supabase import get_supabase_user_client
from src.lib.utils import cast_row_uuids
from src.types.job import DeleteOk, JobResponse, JobUpdate, OutcomeUpdate, StageAdvance

router = APIRouter()

# Strictly sequential pipeline progression rule boundary
STAGE_PROGRESSION = [
    "applied",
    "screen",
    "hm",
    "deep",
    "final",
    "offer",
    "closed",
]


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    body: dict = Body(default_factory=dict),
):
    try:
        patch = JobUpdate.model_validate(body)
    except ValidationError as exc:
        raise_400(exc)

    sb = get_supabase_user_client(token)
    updates = patch.model_dump(exclude_unset=True, mode="json")

    if "company" in updates and isinstance(updates["company"], str):
        updates["company"] = updates["company"].strip()
    if "role" in updates and isinstance(updates["role"], str):
        updates["role"] = updates["role"].strip()

    # Automatically update timestamp when status changes
    if "status" in updates:
        updates["last_moved_at"] = datetime.now(timezone.utc).isoformat()

    if not updates:
        existing = (
            sb.table("jobs")
            .select("*")
            .eq("id", str(job_id))
            .eq("user_id", str(current_user_id))
            .limit(1)
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Not found")

        return JobResponse.model_validate(cast_row_uuids(existing.data[0]))

    result = (
        sb.table("jobs")
        .update(updates)
        .eq("id", str(job_id))
        .eq("user_id", str(current_user_id))
        .select("*")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Not found")

    return JobResponse.model_validate(cast_row_uuids(result.data[0]))


@router.delete("/{job_id}", response_model=DeleteOk)
async def delete_job(
    job_id: UUID, current_user_id: CurrentUserId, token: CurrentUserToken
):
    sb = get_supabase_user_client(token)
    result = (
        sb.table("jobs")
        .delete()
        .eq("id", str(job_id))
        .eq("user_id", str(current_user_id))
        .select("id")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Not found")

    return DeleteOk(success=True)


# =============================================================
# STEP 1 — STAGE ADVANCEMENT
# =============================================================


@router.patch("/{job_id}/advance", response_model=JobResponse)
async def advance_job_stage(
    job_id: UUID,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    body: dict = Body(default_factory=dict),
):
    """
    Advances a job application strictly to the next logical stage.
    Prevents skips or moving backward.
    """
    try:
        payload = StageAdvance.model_validate(body)
    except ValidationError as exc:
        raise_400(exc)

    sb = get_supabase_user_client(token)

    # Pull down current record to check pipeline stage status
    existing = (
        sb.table("jobs")
        .select("*")
        .eq("id", str(job_id))
        .eq("user_id", str(current_user_id))
        .maybe_single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(status_code=404, detail="Job application not found")

    # Map database row status field to state sequence string
    current_stage = existing.data.get("status")
    new_stage = payload.new_stage.value

    if current_stage not in STAGE_PROGRESSION or new_stage not in STAGE_PROGRESSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application contains an unrecognized workflow stage status.",
        )

    current_idx = STAGE_PROGRESSION.index(current_stage)
    new_idx = STAGE_PROGRESSION.index(new_stage)

    # Rule enforcement: exact sequential step forward (+1)
    if new_idx != current_idx + 1:
        allowed_next = (
            STAGE_PROGRESSION[current_idx + 1]
            if current_idx + 1 < len(STAGE_PROGRESSION)
            else "None (pipeline finished)"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Illegal transition from '{current_stage}' to '{new_stage}'. From here, you can only advance to '{allowed_next}'.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()

    result = (
        sb.table("jobs")
        .update({"status": new_stage, "last_moved_at": now_iso})
        .eq("id", str(job_id))
        .eq("user_id", str(current_user_id))
        .select("*")
        .execute()
    )

    return JobResponse.model_validate(cast_row_uuids(result.data[0]))


# =============================================================
# STEP 2 — OUTCOME LOGGING
# =============================================================


@router.post("/{job_id}/outcome", response_model=JobResponse)
async def log_job_outcome(
    job_id: UUID,
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    body: dict = Body(default_factory=dict),
):
    """
    Closes a job with a terminal outcome and flags linked interviews for recovery if needed.
    """
    try:
        payload = OutcomeUpdate.model_validate(body)
    except ValidationError as exc:
        raise_400(exc)

    sb = get_supabase_user_client(token)

    # Validate that job belongs to current user before modifying states
    existing = (
        sb.table("jobs")
        .select("id")
        .eq("id", str(job_id))
        .eq("user_id", str(current_user_id))
        .maybe_single()
        .execute()
    )

    if not existing.data:
        raise HTTPException(status_code=404, detail="Job application not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    outcome_val = payload.outcome.value

    # Update application properties to complete terminal configuration
    result = (
        sb.table("jobs")
        .update(
            {
                "outcome": outcome_val,
                "status": JobStatus.CLOSED.value,
                "last_moved_at": now_iso,
            }
        )
        .eq("id", str(job_id))
        .eq("user_id", str(current_user_id))
        .select("*")
        .execute()
    )

    # Recovery trigger assessment
    if outcome_val in ["rejected", "ghosted"]:
        interview_res = (
            sb.table("interviews")
            .select("id")
            .eq("job_id", str(job_id))
            .eq("user_id", str(current_user_id))
            .maybe_single()
            .execute()
        )

        if interview_res.data:
            sb.table("interviews").update({"recovery_needed": True}).eq(
                "id", interview_res.data["id"]
            ).execute()

    return JobResponse.model_validate(cast_row_uuids(result.data[0]))
