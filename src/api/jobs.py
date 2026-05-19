from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from src.lib.auth import CurrentUserId
from src.lib.supabase import get_supabase_service_client
from src.types.job import JobCreate, JobResponse, JobStatus

router = APIRouter()


def _raise_400(exc: ValidationError) -> None:
    raise HTTPException(status_code=400, detail=exc.errors(include_url=False)) from None


@router.post("", status_code=201, response_model=JobResponse)
def create_job(current_user_id: CurrentUserId, body: dict = Body(default_factory=dict)):
    try:
        payload = JobCreate.model_validate(body)
    except ValidationError as exc:
        _raise_400(exc)

    sb = get_supabase_service_client()

    status_value = JobStatus.applied.value if payload.status is None else payload.status.value

    insert_row: dict[str, object] = {
        "user_id": str(current_user_id),
        "company": payload.company.strip(),
        "role": payload.role.strip(),
        "status": status_value,
        "notes": payload.notes,
    }

    if payload.applied_at is not None:
        insert_row["applied_at"] = payload.applied_at.isoformat()

    result = sb.table("jobs").insert(insert_row).select("*").execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create job")
    row = result.data[0]
    row["user_id"] = UUID(str(row["user_id"]))
    row["id"] = UUID(str(row["id"]))
    return JobResponse.model_validate(row)


@router.get("", response_model=list[JobResponse])
def list_jobs(current_user_id: CurrentUserId):
    sb = get_supabase_service_client()
    result = (
        sb.table("jobs")
        .select("*")
        .eq("user_id", str(current_user_id))
        .order("created_at", desc=True)
        .execute()
    )
    rows = result.data or []

    validated: list[JobResponse] = []
    for row in rows:
        row_uuid = dict(row)
        row_uuid["user_id"] = UUID(str(row_uuid["user_id"]))
        row_uuid["id"] = UUID(str(row_uuid["id"]))
        validated.append(JobResponse.model_validate(row_uuid))
    return validated
