from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, HTTPException
from pydantic import ValidationError

from src.lib.auth import CurrentUserId
from src.lib.supabase import get_supabase_service_client
from src.types.job import DeleteOk, JobResponse, JobUpdate

router = APIRouter()


def _raise_400(exc: ValidationError) -> None:
    raise HTTPException(status_code=400, detail=exc.errors(include_url=False)) from None


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: UUID, current_user_id: CurrentUserId, body: dict = Body(default_factory=dict)):
    try:
        patch = JobUpdate.model_validate(body)
    except ValidationError as exc:
        _raise_400(exc)

    sb = get_supabase_service_client()
    updates = patch.model_dump(exclude_unset=True, mode="json")

    if "company" in updates and isinstance(updates["company"], str):
        updates["company"] = updates["company"].strip()
    if "role" in updates and isinstance(updates["role"], str):
        updates["role"] = updates["role"].strip()

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

        row = existing.data[0]
        row["user_id"] = UUID(str(row["user_id"]))
        row["id"] = UUID(str(row["id"]))
        return JobResponse.model_validate(row)

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

    row = result.data[0]
    row["user_id"] = UUID(str(row["user_id"]))
    row["id"] = UUID(str(row["id"]))
    return JobResponse.model_validate(row)


@router.delete("/{job_id}", response_model=DeleteOk)
def delete_job(job_id: UUID, current_user_id: CurrentUserId):
    sb = get_supabase_service_client()
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
    return DeleteOk()
