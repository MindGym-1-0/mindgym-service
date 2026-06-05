from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.lib.interview_checkin_notifications import (
    InterviewCheckinNotificationResult,
    send_interview_checkin_notification,
)
from src.lib.supabase_client import get_supabase_admin_client

logger = logging.getLogger(__name__)

INTERVIEW_CHECKIN_JOB_SELECT_FIELDS = (
    "id,user_id,company,role,interview_date,outcome,check_in_attempts,next_check_in_at"
)
INTERVIEW_CHECKIN_JOB_LIMIT = 200


def _is_eligible_for_checkin(row: dict[str, Any], now: datetime) -> bool:
    outcome = row.get("outcome")
    if outcome not in (None, "pending", "awaiting"):
        return False

    attempts = int(row.get("check_in_attempts") or 0)
    if attempts >= 3:
        return False

    interview_date_raw = row.get("interview_date")
    if not interview_date_raw:
        return False

    interview_date = datetime.fromisoformat(
        str(interview_date_raw).replace("Z", "+00:00")
    )
    if interview_date >= now:
        return False

    next_check_in_at_raw = row.get("next_check_in_at")
    if not next_check_in_at_raw:
        return True

    next_check_in_at = datetime.fromisoformat(
        str(next_check_in_at_raw).replace("Z", "+00:00")
    )
    return next_check_in_at <= now


async def _update_next_check_in_at(
    client: Any,
    interview_id: str,
    next_check_in_at_iso: str,
) -> bool:
    result = await asyncio.to_thread(
        client.table("interviews")
        .update({"next_check_in_at": next_check_in_at_iso})
        .eq("id", interview_id)
        .select("id")
        .execute
    )
    return bool(result.data)


async def run_interview_checkin_notification_job() -> dict[str, int]:
    summary = {
        "eligible": 0,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
        "rescheduled": 0,
    }

    client = get_supabase_admin_client()
    if client is None:
        logger.warning("Interview check-in job skipped: admin Supabase client unavailable.")
        return summary

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # We treat NULL, 'pending', and 'awaiting' outcomes as eligible because the current
    # schema defaults new rows to 'pending', older task wording referenced NULL, and
    # 'awaiting' means the user is still waiting for a decision and should receive
    # due follow-up check-ins.
    candidate_result = await asyncio.to_thread(
        client.table("interviews")
        .select(INTERVIEW_CHECKIN_JOB_SELECT_FIELDS)
        .lt("interview_date", now_iso)
        .lt("check_in_attempts", 3)
        .order("interview_date", desc=False)
        .limit(INTERVIEW_CHECKIN_JOB_LIMIT)
        .execute
    )

    candidate_rows = candidate_result.data or []
    eligible_rows = [row for row in candidate_rows if _is_eligible_for_checkin(row, now)]
    summary["eligible"] = len(eligible_rows)

    next_check_in_at_iso = (now + timedelta(days=1)).isoformat()

    for row in eligible_rows:
        interview_id = str(row.get("id") or "").strip()
        user_id = str(row.get("user_id") or "").strip()
        if not interview_id or not user_id:
            summary["failed"] += 1
            logger.warning("Interview check-in job skipped malformed row.")
            continue

        try:
            notification_result: InterviewCheckinNotificationResult = (
                await send_interview_checkin_notification(user_id, interview_id)
            )
        except Exception:
            summary["failed"] += 1
            logger.exception("Interview check-in notification dispatch failed.")
            continue

        if notification_result.sent:
            summary["sent"] += 1
        elif notification_result.skipped:
            summary["skipped"] += 1
        else:
            summary["failed"] += 1
            continue

        try:
            was_rescheduled = await _update_next_check_in_at(
                client,
                interview_id,
                next_check_in_at_iso,
            )
        except Exception:
            logger.exception("Interview check-in reschedule update failed.")
            summary["failed"] += 1
            continue

        if was_rescheduled:
            summary["rescheduled"] += 1

    return summary
