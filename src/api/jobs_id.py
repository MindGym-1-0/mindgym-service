from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.errors import raise_400
from src.lib.supabase import get_supabase_user_client
from src.lib.utils import cast_row_uuids
from src.types.job import DeleteOk, JobResponse, JobUpdate

router = APIRouter()


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
