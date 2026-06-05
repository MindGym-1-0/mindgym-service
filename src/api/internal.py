from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from src.lib.config import settings
from src.lib.interview_checkin_job import run_interview_checkin_notification_job

router = APIRouter()


def _require_valid_cron_secret(provided_secret: str | None) -> None:
    expected_secret = getattr(settings, "internal_cron_secret", None)
    if not expected_secret or provided_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/cron/interview-checkins")
async def trigger_interview_checkin_cron(
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict[str, int]:
    _require_valid_cron_secret(x_cron_secret)
    return await run_interview_checkin_notification_job()
