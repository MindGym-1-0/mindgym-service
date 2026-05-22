from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from src.lib.auth import CurrentUserId, CurrentUserToken
from src.lib.errors import raise_400
from src.lib.supabase import get_supabase_user_client
from src.lib.utils import cast_row_uuids
from src.types.job import JobCreate, JobResponse, JobStatus

router = APIRouter()


@router.post("", status_code=201, response_model=JobResponse)
async def create_job(
    current_user_id: CurrentUserId,
    token: CurrentUserToken,
    body: dict = Body(default_factory=dict)
):
    try:
        payload = JobCreate.model_validate(body)
    except ValidationError as exc:
        raise_400(exc)

    sb = get_supabase_user_client(token)
    status_value = JobStatus.APPLIED.value if payload.status is None else payload.status.value

    insert_row: dict[str, object] = {
        "user_id": str(current_user_id),
        "company": payload.company,
        "role": payload.role,
        "status": status_value,
        "notes": payload.notes,
    }

    if payload.applied_at is not None:
        insert_row["applied_at"] = payload.applied_at.isoformat()

    # Catch database execution exceptions (network errors, schema conflicts, constraint violations)
    try:
        result = sb.table("jobs").insert(insert_row).select("*").execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"Database error during job creation: {str(exc)}"
        ) from None

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
        
    return JobResponse.model_validate(cast_row_uuids(result.data[0]))


@router.get("", response_model=list[JobResponse])
async def list_jobs(current_user_id: CurrentUserId, token: CurrentUserToken):
    sb = get_supabase_user_client(token)
    
    try:
        result = (
            sb.table("jobs")
            .select("*")
            .eq("user_id", str(current_user_id))
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"Database error while fetching jobs: {str(exc)}"
        ) from None

    rows = result.data or []

    return [JobResponse.model_validate(cast_row_uuids(row)) for row in rows]