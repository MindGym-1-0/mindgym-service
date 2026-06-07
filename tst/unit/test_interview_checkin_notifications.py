from __future__ import annotations

import asyncio

from src.lib.interview_checkin_notifications import (
    INTERVIEW_CHECKIN_MESSAGE,
    build_interview_checkin_notification_payload,
    send_interview_checkin_notification,
)


def test_build_interview_checkin_notification_payload():
    assert build_interview_checkin_notification_payload("iv-123") == {
        "interview_id": "iv-123"
    }


def test_send_interview_checkin_notification_skips_without_provider():
    result = asyncio.run(send_interview_checkin_notification("user-123", "iv-123"))

    assert result.sent is False
    assert result.skipped is True
    assert result.message == INTERVIEW_CHECKIN_MESSAGE
    assert result.payload == {"interview_id": "iv-123"}
    assert result.reason is not None
