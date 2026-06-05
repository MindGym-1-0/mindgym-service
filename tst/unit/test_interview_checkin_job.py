from __future__ import annotations

import asyncio
from types import SimpleNamespace

import src.lib.interview_checkin_job as job_module
from src.lib.interview_checkin_notifications import InterviewCheckinNotificationResult


class FakeQuery:
    def __init__(self, client: "FakeAdminClient", table_name: str):
        self.client = client
        self.table_name = table_name
        self.filters: list[tuple[str, str, object]] = []
        self.order_field: str | None = None
        self.order_desc = False
        self.limit_value: int | None = None
        self.select_fields: str | None = None
        self.update_payload: dict | None = None

    def select(self, fields: str):
        self.select_fields = fields
        return self

    def lt(self, field: str, value: object):
        self.filters.append(("lt", field, value))
        return self

    def eq(self, field: str, value: object):
        self.filters.append(("eq", field, value))
        return self

    def order(self, field: str, desc: bool = False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def update(self, payload: dict):
        self.update_payload = payload
        return self

    def execute(self):
        if self.update_payload is not None:
            interview_id = None
            for op, field, value in self.filters:
                if op == "eq" and field == "id":
                    interview_id = value
                    break

            for row in self.client.tables.get(self.table_name, []):
                if row.get("id") == interview_id:
                    row.update(self.update_payload)
                    self.client.updates.append(
                        {"id": interview_id, "payload": dict(self.update_payload)}
                    )
                    return SimpleNamespace(data=[{"id": interview_id}])
            return SimpleNamespace(data=[])

        rows = list(self.client.tables.get(self.table_name, []))
        for op, field, value in self.filters:
            if op == "lt":
                rows = [row for row in rows if str(row.get(field) or "") < str(value)]
            elif op == "eq":
                rows = [row for row in rows if row.get(field) == value]

        if self.order_field:
            rows = sorted(
                rows,
                key=lambda row: row.get(self.order_field),
                reverse=self.order_desc,
            )
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)


class FakeAdminClient:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables
        self.updates: list[dict] = []

    def table(self, table_name: str) -> FakeQuery:
        return FakeQuery(self, table_name)


def test_run_interview_checkin_notification_job_skips_when_admin_client_missing(monkeypatch):
    monkeypatch.setattr(job_module, "get_supabase_admin_client", lambda: None)

    summary = asyncio.run(job_module.run_interview_checkin_notification_job())

    assert summary == {
        "eligible": 0,
        "sent": 0,
        "skipped": 0,
        "failed": 0,
        "rescheduled": 0,
    }


def test_run_interview_checkin_notification_job_filters_and_reschedules(monkeypatch):
    client = FakeAdminClient(
        {
            "interviews": [
                {
                    "id": "iv-eligible-null",
                    "user_id": "user-1",
                    "company": "Acme",
                    "role": "Engineer",
                    "interview_date": "2026-06-01T12:00:00+00:00",
                    "outcome": None,
                    "check_in_attempts": 0,
                    "next_check_in_at": None,
                },
                {
                    "id": "iv-eligible-pending",
                    "user_id": "user-2",
                    "company": "Orbit",
                    "role": "PM",
                    "interview_date": "2026-06-01T13:00:00+00:00",
                    "outcome": "pending",
                    "check_in_attempts": 1,
                    "next_check_in_at": "2026-06-02T12:00:00+00:00",
                },
                {
                    "id": "iv-not-yet-due",
                    "user_id": "user-3",
                    "company": "Zenith",
                    "role": "Designer",
                    "interview_date": "2026-06-01T14:00:00+00:00",
                    "outcome": "pending",
                    "check_in_attempts": 1,
                    "next_check_in_at": "2026-06-05T12:00:00+00:00",
                },
                {
                    "id": "iv-closed",
                    "user_id": "user-4",
                    "company": "North",
                    "role": "Analyst",
                    "interview_date": "2026-06-01T15:00:00+00:00",
                    "outcome": "offer",
                    "check_in_attempts": 0,
                    "next_check_in_at": None,
                },
            ]
        }
    )

    monkeypatch.setattr(job_module, "get_supabase_admin_client", lambda: client)

    async def _fake_send(user_id: str, interview_id: str):
        return InterviewCheckinNotificationResult(
            sent=False,
            skipped=True,
            message="How did your interview go?",
            payload={"interview_id": interview_id},
            reason=f"no provider for {user_id}",
        )

    monkeypatch.setattr(job_module, "send_interview_checkin_notification", _fake_send)

    summary = asyncio.run(job_module.run_interview_checkin_notification_job())

    assert summary["eligible"] == 2
    assert summary["sent"] == 0
    assert summary["skipped"] == 2
    assert summary["failed"] == 0
    assert summary["rescheduled"] == 2
    assert {update["id"] for update in client.updates} == {
        "iv-eligible-null",
        "iv-eligible-pending",
    }


def test_run_interview_checkin_notification_job_counts_dispatch_failures(monkeypatch):
    client = FakeAdminClient(
        {
            "interviews": [
                {
                    "id": "iv-fail",
                    "user_id": "user-1",
                    "company": "Acme",
                    "role": "Engineer",
                    "interview_date": "2026-06-01T12:00:00+00:00",
                    "outcome": "pending",
                    "check_in_attempts": 0,
                    "next_check_in_at": None,
                }
            ]
        }
    )

    monkeypatch.setattr(job_module, "get_supabase_admin_client", lambda: client)

    async def _boom(_user_id: str, _interview_id: str):
        raise RuntimeError("dispatch failed")

    monkeypatch.setattr(job_module, "send_interview_checkin_notification", _boom)

    summary = asyncio.run(job_module.run_interview_checkin_notification_job())

    assert summary["eligible"] == 1
    assert summary["failed"] == 1
    assert summary["rescheduled"] == 0


def test_run_interview_checkin_notification_job_continues_after_failure(monkeypatch):
    client = FakeAdminClient(
        {
            "interviews": [
                {
                    "id": "iv-fail",
                    "user_id": "user-1",
                    "company": "Acme",
                    "role": "Engineer",
                    "interview_date": "2026-06-01T12:00:00+00:00",
                    "outcome": "pending",
                    "check_in_attempts": 0,
                    "next_check_in_at": None,
                },
                {
                    "id": "iv-skip",
                    "user_id": "user-2",
                    "company": "Orbit",
                    "role": "PM",
                    "interview_date": "2026-06-01T13:00:00+00:00",
                    "outcome": "pending",
                    "check_in_attempts": 0,
                    "next_check_in_at": None,
                },
            ]
        }
    )

    monkeypatch.setattr(job_module, "get_supabase_admin_client", lambda: client)

    async def _mixed_send(_user_id: str, interview_id: str):
        if interview_id == "iv-fail":
            raise RuntimeError("dispatch failed")
        return InterviewCheckinNotificationResult(
            sent=False,
            skipped=True,
            message="How did your interview go?",
            payload={"interview_id": interview_id},
            reason="no provider configured",
        )

    monkeypatch.setattr(job_module, "send_interview_checkin_notification", _mixed_send)

    summary = asyncio.run(job_module.run_interview_checkin_notification_job())

    assert summary["eligible"] == 2
    assert summary["failed"] == 1
    assert summary["skipped"] == 1
    assert summary["rescheduled"] == 1
    assert len(client.updates) == 1
    assert client.updates[0]["id"] == "iv-skip"
    assert "next_check_in_at" in client.updates[0]["payload"]
