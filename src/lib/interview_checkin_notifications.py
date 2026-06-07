from __future__ import annotations

from dataclasses import dataclass


INTERVIEW_CHECKIN_MESSAGE = "How did your interview go?"


@dataclass(frozen=True)
class InterviewCheckinNotificationResult:
    sent: bool
    skipped: bool
    message: str
    payload: dict[str, str]
    reason: str | None = None


def build_interview_checkin_notification_payload(interview_id: str) -> dict[str, str]:
    return {"interview_id": interview_id}


async def send_interview_checkin_notification(
    user_id: str,
    interview_id: str,
) -> InterviewCheckinNotificationResult:
    _ = user_id
    payload = build_interview_checkin_notification_payload(interview_id)

    # TODO: connect to Moksh/frontend push token storage and notification provider when available.
    return InterviewCheckinNotificationResult(
        sent=False,
        skipped=True,
        message=INTERVIEW_CHECKIN_MESSAGE,
        payload=payload,
        reason="No push notification provider or token source is configured.",
    )
