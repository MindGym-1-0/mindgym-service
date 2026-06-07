from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.internal as internal_module


def _create_client(monkeypatch, secret: str | None = "cron-secret") -> TestClient:
    app = FastAPI()
    app.include_router(internal_module.router, prefix="/api/internal", tags=["internal"])
    monkeypatch.setattr(
        internal_module,
        "settings",
        SimpleNamespace(internal_cron_secret=secret),
    )
    return TestClient(app)


def test_interview_checkin_cron_rejects_missing_secret(monkeypatch):
    client = _create_client(monkeypatch)

    resp = client.post("/api/internal/cron/interview-checkins")

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Unauthorized"}


def test_interview_checkin_cron_rejects_invalid_secret(monkeypatch):
    client = _create_client(monkeypatch)

    resp = client.post(
        "/api/internal/cron/interview-checkins",
        headers={"X-Cron-Secret": "wrong-secret"},
    )

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Unauthorized"}


def test_interview_checkin_cron_runs_job_with_valid_secret(monkeypatch):
    client = _create_client(monkeypatch)

    async def _fake_job():
        return {
            "eligible": 4,
            "sent": 1,
            "skipped": 2,
            "failed": 0,
            "rescheduled": 3,
        }

    monkeypatch.setattr(
        internal_module,
        "run_interview_checkin_notification_job",
        _fake_job,
    )

    resp = client.post(
        "/api/internal/cron/interview-checkins",
        headers={"X-Cron-Secret": "cron-secret"},
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "eligible": 4,
        "sent": 1,
        "skipped": 2,
        "failed": 0,
        "rescheduled": 3,
    }
