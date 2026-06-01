from __future__ import annotations

import os
from dataclasses import dataclass
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import src.api.coach as coach_module
from src.lib.auth import require_current_user_id, require_current_user_token
from src.lib.gemini import GeminiInvalidJsonError, GeminiTimeoutError

os.environ["DEBUG"] = "false"
from src.main import app


@dataclass
class _Filter:
    op: str
    field: str
    value: object


class FakeQuery:
    def __init__(self, sb: "FakeSupabase", table_name: str):
        self.sb = sb
        self.table_name = table_name
        self.filters: list[_Filter] = []
        self.order_field: str | None = None
        self.order_desc = False
        self.limit_value: int | None = None
        self.select_fields: str | None = None
        self.upsert_payload: dict | None = None

    def select(self, fields: str):
        self.select_fields = fields
        return self

    def eq(self, field: str, value: object):
        self.filters.append(_Filter("eq", field, value))
        return self

    def gte(self, field: str, value: object):
        self.filters.append(_Filter("gte", field, value))
        return self

    def order(self, field: str, desc: bool = False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    @property
    def not_(self):
        return self

    def is_(self, field: str, value: object):
        self.filters.append(_Filter("not_is", field, value))
        return self

    def upsert(self, payload: dict, on_conflict: str | None = None):
        self.upsert_payload = payload
        self.sb.last_upsert = {
            "table": self.table_name,
            "payload": payload,
            "on_conflict": on_conflict,
        }
        return self

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        result = list(rows)
        for flt in self.filters:
            if flt.op == "eq":
                result = [r for r in result if r.get(flt.field) == flt.value]
            elif flt.op == "gte":
                result = [r for r in result if str(r.get(flt.field) or "") >= str(flt.value)]
            elif flt.op == "not_is":
                # We only need completed_at IS NOT NULL behavior for these tests.
                if flt.value == "null":
                    result = [r for r in result if r.get(flt.field) is not None]
        return result

    def _apply_order(self, rows: list[dict]) -> list[dict]:
        if not self.order_field:
            return rows
        return sorted(
            rows,
            key=lambda r: (r.get(self.order_field) is None, r.get(self.order_field)),
            reverse=self.order_desc,
        )

    def execute(self):
        self.sb.query_log.append(
            {
                "table": self.table_name,
                "select_fields": self.select_fields,
                "filters": [
                    {"op": flt.op, "field": flt.field, "value": flt.value}
                    for flt in self.filters
                ],
                "order_field": self.order_field,
                "order_desc": self.order_desc,
                "limit": self.limit_value,
                "is_upsert": self.upsert_payload is not None,
            }
        )
        if self.upsert_payload is not None:
            rows = self.sb.tables.setdefault(self.table_name, [])
            key_fields = (self.sb.last_upsert or {}).get("on_conflict", "")
            keys = [k.strip() for k in key_fields.split(",") if k.strip()]
            replaced = False
            for idx, row in enumerate(rows):
                if keys and all(row.get(k) == self.upsert_payload.get(k) for k in keys):
                    new_row = dict(row)
                    new_row.update(self.upsert_payload)
                    rows[idx] = new_row
                    replaced = True
                    break
            if not replaced:
                new_row = dict(self.upsert_payload)
                new_row.setdefault("created_at", "2026-05-25T12:00:00+00:00")
                rows.append(new_row)
            return SimpleNamespace(data=[self.upsert_payload])

        rows = self.sb.tables.get(self.table_name, [])
        result = self._apply_filters(rows)
        result = self._apply_order(result)
        if self.limit_value is not None:
            result = result[: self.limit_value]
        return SimpleNamespace(data=result)


class FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]] | None = None):
        self.tables = tables or {}
        self.last_upsert: dict | None = None
        self.query_log: list[dict] = []

    def table(self, table_name: str) -> FakeQuery:
        return FakeQuery(self, table_name)


@pytest.fixture
def fake_user_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def client(fake_user_id: UUID, monkeypatch):
    monkeypatch.setitem(
        app.dependency_overrides, require_current_user_id, lambda: fake_user_id
    )
    monkeypatch.setitem(
        app.dependency_overrides, require_current_user_token, lambda: "fake-token"
    )
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.pop(require_current_user_id, None)
    app.dependency_overrides.pop(require_current_user_token, None)


@pytest.fixture(autouse=True)
def clear_coach_home_cache():
    coach_module._COACH_HOME_CACHE.clear()
    yield
    coach_module._COACH_HOME_CACHE.clear()


def _base_tables(user_id: str) -> dict[str, list[dict]]:
    return {
        "users": [
            {
                "id": user_id,
                "goal": "Land senior backend role",
                "stage": "interviewing",
                "anxiety_level": 7,
                "employment_status": "employed",
                "target_role_category": "backend",
                "emotional_challenge": "impostor syndrome",
                "baseline_anxiety": 6,
            }
        ],
        "interviews": [],
        "ai_sessions": [],
        "streaks": [{"user_id": user_id, "current_streak": 4}],
        "coach_prep_plans": [],
    }


def _mock_coach_deps(monkeypatch, sb: FakeSupabase, gemini_result_or_exc):
    monkeypatch.setattr(coach_module, "get_supabase_user_client", lambda token: sb)
    if isinstance(gemini_result_or_exc, Exception):
        async def _raise(*_args, **_kwargs):
            raise gemini_result_or_exc
        monkeypatch.setattr(coach_module, "generate_gemini_flash_json", _raise)
    else:
        async def _ok(*_args, **_kwargs):
            return gemini_result_or_exc
        monkeypatch.setattr(coach_module, "generate_gemini_flash_json", _ok)


def test_get_coach_home_success(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "iv1",
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-01T12:00:00+00:00",
        }
    ]
    tables["ai_sessions"] = [
        {"user_id": uid, "preparation_for": "interview_tomorrow", "anxiety_level_delta": 2, "completed_at": "2026-05-24T10:00:00+00:00"}
    ]
    sb = FakeSupabase(tables)

    gemini = {
        "recommended_sessions": [
            {"title": "A", "duration_mins": 10, "focus": "f1", "session_type": "interview_tomorrow"},
            {"title": "B", "duration_mins": 8, "focus": "f2", "session_type": "general_reset"},
            {"title": "C", "duration_mins": 12, "focus": "f3", "session_type": "recruiter_call"},
        ],
        "recommended_today": ["i1", "i2", "i3", "i4"],
        "maya_suggests": {"text": "Prep for your interview", "session_type": "interview_tomorrow", "time_suggestion": "10 min now"},
        "maya_greeting": "Your interview is coming up, let's focus today.",
    }
    _mock_coach_deps(monkeypatch, sb, gemini)

    resp = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["recommended_sessions"]) == 3
    assert len(body["recommended_today"]) == 4
    assert "maya_suggests" in body
    assert "maya_greeting" in body
    assert "interview" in body["maya_greeting"].lower()


def test_get_coach_home_requires_actual_company_or_role_mention(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "iv2",
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-02T12:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)

    # Generic wording includes "role" and "interview" but not actual company/role values.
    gemini = {
        "recommended_sessions": [
            {"title": "A", "duration_mins": 10, "focus": "f1", "session_type": "interview_tomorrow"},
            {"title": "B", "duration_mins": 8, "focus": "f2", "session_type": "general_reset"},
            {"title": "C", "duration_mins": 12, "focus": "f3", "session_type": "recruiter_call"},
        ],
        "recommended_today": ["i1", "i2", "i3", "i4"],
        "maya_suggests": {"text": "Prepare for your role interview", "session_type": "interview_tomorrow", "time_suggestion": "10 min"},
        "maya_greeting": "Your role interview is coming up.",
    }
    _mock_coach_deps(monkeypatch, sb, gemini)

    resp = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200
    # Should fallback because actual company/role context is missing.
    assert "upcoming interview soon" in resp.json()["maya_greeting"].lower()


def test_get_coach_home_actual_company_or_role_mention_passes(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "iv3",
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-03T12:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)

    gemini = {
        "recommended_sessions": [
            {"title": "A", "duration_mins": 10, "focus": "f1", "session_type": "interview_tomorrow"},
            {"title": "B", "duration_mins": 8, "focus": "f2", "session_type": "general_reset"},
            {"title": "C", "duration_mins": 12, "focus": "f3", "session_type": "recruiter_call"},
        ],
        "recommended_today": ["i1", "i2", "i3", "i4"],
        "maya_suggests": {"text": "Let's prepare for Acme", "session_type": "interview_tomorrow", "time_suggestion": "10 min"},
        "maya_greeting": "Your Acme interview is coming up, let's focus.",
    }
    _mock_coach_deps(monkeypatch, sb, gemini)

    resp = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200
    assert "acme" in resp.json()["maya_greeting"].lower()


def test_get_coach_home_same_user_uses_cache(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "iv4",
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-04T12:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)
    monkeypatch.setattr(coach_module, "get_supabase_user_client", lambda token: sb)

    calls = {"count": 0}

    async def _gemini(*_args, **_kwargs):
        calls["count"] += 1
        return {
            "recommended_sessions": [
                {"title": "A", "duration_mins": 10, "focus": "f1", "session_type": "interview_tomorrow"},
                {"title": "B", "duration_mins": 8, "focus": "f2", "session_type": "general_reset"},
                {"title": "C", "duration_mins": 12, "focus": "f3", "session_type": "recruiter_call"},
            ],
            "recommended_today": ["i1", "i2", "i3", "i4"],
            "maya_suggests": {"text": "Let's prepare for Acme", "session_type": "interview_tomorrow", "time_suggestion": "10 min"},
            "maya_greeting": "Your Acme interview is coming up, let's focus.",
        }

    monkeypatch.setattr(coach_module, "generate_gemini_flash_json", _gemini)

    first = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    second = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["count"] == 1


def test_get_coach_home_cache_is_per_user(monkeypatch):
    uid1 = UUID("11111111-1111-1111-1111-111111111111")
    uid2 = UUID("22222222-2222-2222-2222-222222222222")
    current_user = {"id": uid1}

    app.dependency_overrides[require_current_user_id] = lambda: current_user["id"]
    app.dependency_overrides[require_current_user_token] = lambda: "fake-token"
    client = TestClient(app)

    def _sb_for_user(token: str):
        uid = str(current_user["id"])
        tables = _base_tables(uid)
        tables["interviews"] = [
            {
                "id": f"iv-{uid}",
                "user_id": uid,
                "company": "Acme" if uid.endswith("111111111111") else "Zenith",
                "role": "Backend Engineer",
                "interview_date": "2026-06-05T12:00:00+00:00",
            }
        ]
        return FakeSupabase(tables)

    monkeypatch.setattr(coach_module, "get_supabase_user_client", _sb_for_user)
    calls = {"count": 0}

    async def _gemini(*_args, **_kwargs):
        calls["count"] += 1
        label = "Acme" if str(current_user["id"]).endswith("111111111111") else "Zenith"
        return {
            "recommended_sessions": [
                {"title": "A", "duration_mins": 10, "focus": "f1", "session_type": "interview_tomorrow"},
                {"title": "B", "duration_mins": 8, "focus": "f2", "session_type": "general_reset"},
                {"title": "C", "duration_mins": 12, "focus": "f3", "session_type": "recruiter_call"},
            ],
            "recommended_today": ["i1", "i2", "i3", "i4"],
            "maya_suggests": {"text": f"Let's prepare for {label}", "session_type": "interview_tomorrow", "time_suggestion": "10 min"},
            "maya_greeting": f"Your {label} interview is coming up, let's focus.",
        }

    monkeypatch.setattr(coach_module, "generate_gemini_flash_json", _gemini)

    r1 = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    current_user["id"] = uid2
    r2 = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert calls["count"] == 2
    assert "acme" in r1.json()["maya_greeting"].lower()
    assert "zenith" in r2.json()["maya_greeting"].lower()

    app.dependency_overrides.pop(require_current_user_id, None)
    app.dependency_overrides.pop(require_current_user_token, None)


def test_get_coach_home_expired_cache_triggers_fresh_generation(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "iv5",
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-06T12:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)
    monkeypatch.setattr(coach_module, "get_supabase_user_client", lambda token: sb)

    calls = {"count": 0}

    async def _gemini(*_args, **_kwargs):
        calls["count"] += 1
        return {
            "recommended_sessions": [
                {"title": "A", "duration_mins": 10, "focus": "f1", "session_type": "interview_tomorrow"},
                {"title": "B", "duration_mins": 8, "focus": "f2", "session_type": "general_reset"},
                {"title": "C", "duration_mins": 12, "focus": "f3", "session_type": "recruiter_call"},
            ],
            "recommended_today": ["i1", "i2", "i3", "i4"],
            "maya_suggests": {"text": "Let's prepare for Acme", "session_type": "interview_tomorrow", "time_suggestion": "10 min"},
            "maya_greeting": "Your Acme interview is coming up, let's focus.",
        }

    monkeypatch.setattr(coach_module, "generate_gemini_flash_json", _gemini)

    fake_now = {"value": 1000.0}

    def _fake_time():
        return fake_now["value"]

    monkeypatch.setattr(coach_module.time, "time", _fake_time)

    r1 = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    fake_now["value"] += coach_module.COACH_HOME_CACHE_TTL_SECONDS + 1
    r2 = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert calls["count"] == 2


def test_get_coach_home_no_upcoming_interview_fallback_momentum(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, GeminiTimeoutError("timeout"))

    resp = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["recommended_sessions"]) == 3
    assert len(body["recommended_today"]) == 4
    assert "momentum" in body["maya_greeting"].lower()


def test_get_coach_home_gemini_invalid_json_returns_fallback(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, GeminiInvalidJsonError("bad json"))

    resp = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200
    assert len(resp.json()["recommended_sessions"]) == 3
    assert len(resp.json()["recommended_today"]) == 4


def test_post_prep_plan_success_and_saves_upsert(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "event_type": "onsite",
            "interview_date": "2026-06-03T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    gemini = {
        "plan": [
            {"day": 1, "task": "Acme role prep", "description": "Focus on Backend Engineer scope", "session_type": "general_reset", "duration_mins": 10},
            {"day": 2, "task": "Acme stories", "description": "Role-aligned examples", "session_type": "interview_tomorrow", "duration_mins": 10},
            {"day": 3, "task": "Acme pressure run", "description": "Backend Engineer timed drill", "session_type": "recruiter_call", "duration_mins": 10},
            {"day": 4, "task": "Acme confidence", "description": "Role strengths", "session_type": "general_reset", "duration_mins": 8},
            {"day": 5, "task": "Acme final", "description": "Backend Engineer focus", "session_type": "interview_tomorrow", "duration_mins": 12},
        ],
        "recommended_first_session": {"session_type": "general_reset", "reason": "Start calm", "duration_mins": 10},
        "coach_note": "You are ready.",
    }
    _mock_coach_deps(monkeypatch, sb, gemini)

    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1", "worry_input": "I'm worried about blanking out"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["plan"]) == 5
    assert "recommended_first_session" in body
    assert body["coach_note"]
    assert sb.last_upsert is not None
    assert sb.last_upsert["table"] == "coach_prep_plans"
    assert sb.last_upsert["on_conflict"] == "user_id,interview_id"


def test_post_prep_plan_gemini_failure_returns_fallback_and_saves(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
            "user_id": uid,
            "company": "Zenith",
            "role": "Platform Engineer",
            "event_type": "phone",
            "interview_date": "2026-06-04T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, GeminiTimeoutError("timeout"))

    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2", "worry_input": "I ramble"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["plan"]) == 5
    assert body["recommended_first_session"]["session_type"] in {
        "general_reset",
        "interview_tomorrow",
        "recruiter_call",
        "networking",
        "salary_negotiation",
        "rejection_recovery",
        "restarting_search",
    }
    assert sb.last_upsert is not None


def test_post_prep_plan_invalid_session_type_uses_fallback(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3",
            "user_id": uid,
            "company": "Nova",
            "role": "Data Engineer",
            "event_type": "onsite",
            "interview_date": "2026-06-05T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    bad = {
        "plan": [
            {"day": i, "task": "Nova Data Engineer task", "description": "desc", "session_type": "bad_type", "duration_mins": 10}
            for i in [1, 2, 3, 4, 5]
        ],
        "recommended_first_session": {"session_type": "bad_type", "reason": "x", "duration_mins": 10},
        "coach_note": "note",
    }
    _mock_coach_deps(monkeypatch, sb, bad)

    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3", "worry_input": "I freeze"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["plan"]) == 5
    assert resp.json()["recommended_first_session"]["session_type"] != "bad_type"


def test_post_prep_plan_missing_company_role_mentions_uses_fallback(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4",
            "user_id": uid,
            "company": "Orbit",
            "role": "SRE",
            "event_type": "onsite",
            "interview_date": "2026-06-06T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    bad = {
        "plan": [
            {"day": i, "task": "Generic task", "description": "No company role mentioned", "session_type": "general_reset", "duration_mins": 10}
            for i in [1, 2, 3, 4, 5]
        ],
        "recommended_first_session": {"session_type": "general_reset", "reason": "x", "duration_mins": 10},
        "coach_note": "note",
    }
    _mock_coach_deps(monkeypatch, sb, bad)

    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4", "worry_input": "I lose focus"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    combined = " ".join([f"{i['task']} {i['description']}" for i in resp.json()["plan"]]).lower()
    assert "orbit" in combined
    assert "sre" in combined


def test_post_prep_plan_empty_company_uses_fallback(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6",
            "user_id": uid,
            "company": "",
            "role": "SRE",
            "event_type": "onsite",
            "interview_date": "2026-06-06T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    gemini = {
        "plan": [
            {"day": i, "task": "Generic task", "description": "Generic desc", "session_type": "general_reset", "duration_mins": 10}
            for i in [1, 2, 3, 4, 5]
        ],
        "recommended_first_session": {"session_type": "general_reset", "reason": "x", "duration_mins": 10},
        "coach_note": "note",
    }
    _mock_coach_deps(monkeypatch, sb, gemini)

    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa6", "worry_input": "I lose focus"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["plan"]) == 5


def test_post_prep_plan_empty_role_uses_fallback(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7",
            "user_id": uid,
            "company": "Orbit",
            "role": "   ",
            "event_type": "onsite",
            "interview_date": "2026-06-06T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    gemini = {
        "plan": [
            {"day": i, "task": "Generic task", "description": "Generic desc", "session_type": "general_reset", "duration_mins": 10}
            for i in [1, 2, 3, 4, 5]
        ],
        "recommended_first_session": {"session_type": "general_reset", "reason": "x", "duration_mins": 10},
        "coach_note": "note",
    }
    _mock_coach_deps(monkeypatch, sb, gemini)

    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa7", "worry_input": "I lose focus"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["plan"]) == 5


def test_get_saved_prep_plan_existing_returns_saved(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["coach_prep_plans"] = [
        {
            "user_id": uid,
            "interview_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1",
            "plan": {
                "plan": [
                    {"day": 1, "task": "A", "description": "B", "session_type": "general_reset", "duration_mins": 10},
                    {"day": 2, "task": "A2", "description": "B2", "session_type": "interview_tomorrow", "duration_mins": 10},
                    {"day": 3, "task": "A3", "description": "B3", "session_type": "recruiter_call", "duration_mins": 10},
                    {"day": 4, "task": "A4", "description": "B4", "session_type": "general_reset", "duration_mins": 10},
                    {"day": 5, "task": "A5", "description": "B5", "session_type": "interview_tomorrow", "duration_mins": 10},
                ],
                "recommended_first_session": {"session_type": "general_reset", "reason": "x", "duration_mins": 10},
            },
            "coach_note": "Saved note",
            "created_at": "2026-05-25T12:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, {"unused": True})

    resp = client.get(
        "/api/coach/prep-plan/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["plan"]) == 5
    assert body["coach_note"] == "Saved note"
    assert "recommended_first_session" in body
    assert "created_at" in body


def test_get_saved_prep_plan_missing_returns_404(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    sb = FakeSupabase(_base_tables(uid))
    _mock_coach_deps(monkeypatch, sb, {"unused": True})

    resp = client.get(
        "/api/coach/prep-plan/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 404


def test_get_saved_prep_plan_does_not_expose_other_users_plan(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    tables["coach_prep_plans"] = [
        {
            "user_id": "22222222-2222-2222-2222-222222222222",
            "interview_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3",
            "plan": [],
            "coach_note": "Other user note",
            "created_at": "2026-05-25T12:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, {"unused": True})

    resp = client.get(
        "/api/coach/prep-plan/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb3",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 404


def test_post_prep_plan_invalid_uuid_returns_422(client):
    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": "not-a-uuid", "worry_input": "I ramble"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 422


def test_get_saved_prep_plan_invalid_uuid_path_returns_422(client):
    resp = client.get(
        "/api/coach/prep-plan/not-a-uuid",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 422


def test_post_prep_plan_whitespace_worry_input_returns_422(client):
    resp = client.post(
        "/api/coach/prep-plan",
        json={
            "interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5",
            "worry_input": "     ",
        },
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 422


def test_post_prep_plan_overlong_worry_input_returns_422(client):
    resp = client.post(
        "/api/coach/prep-plan",
        json={
            "interview_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa5",
            "worry_input": "a" * 301,
        },
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 422


def test_post_checklist_success(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    interview_id = "cccccccc-cccc-cccc-cccc-ccccccccccc1"
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": interview_id,
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-10T12:00:00+00:00",
            "job_id": "job-123",
        }
    ]
    tables["ai_sessions"] = [
        {
            "id": "s1",
            "user_id": uid,
            "job_id": "job-123",
            "company": "Acme",
            "role": "Backend Engineer",
            "anxiety_level_after": 8,
            "completed_at": "2026-06-09T18:00:00+00:00",
        },
        {
            "id": "s2",
            "user_id": uid,
            "job_id": "job-123",
            "company": "Acme",
            "role": "Backend Engineer",
            "anxiety_level_after": 9,
            "completed_at": "2026-06-09T20:00:00+00:00",
        },
    ]
    sb = FakeSupabase(tables)
    gemini = {
        "tonights_plan": [
            {"time": "7:00 PM", "task": "Review role priorities."},
            {"time": "8:30 PM", "task": "Practice concise answers."},
            {"time": "9:30 PM", "task": "Do a short breathing reset."},
        ],
        "quote": "Calm prep tonight creates clear execution tomorrow.",
    }
    _mock_coach_deps(monkeypatch, sb, gemini)

    resp = client.post(
        "/api/coach/checklist",
        json={"interview_id": interview_id},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "overall_readiness" in body
    assert "mental_prep" in body
    assert "logistics" in body
    assert "tonights_plan" in body
    assert "quote" in body
    assert len(body["tonights_plan"]) == 3
    assert body["quote"]
    assert body["overall_readiness"]["total_items"] == (
        len(body["mental_prep"]) + len(body["logistics"])
    )


def test_post_checklist_skips_company_role_fallback_when_job_sessions_exist(
    client, fake_user_id: UUID, monkeypatch
):
    uid = str(fake_user_id)
    interview_id = "cccccccc-cccc-cccc-cccc-ccccccccccc5"
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": interview_id,
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-10T12:00:00+00:00",
            "job_id": "job-123",
        }
    ]
    tables["ai_sessions"] = [
        {
            "id": "s1",
            "user_id": uid,
            "job_id": "job-123",
            "company": "Acme",
            "role": "Backend Engineer",
            "anxiety_level_after": 8,
            "completed_at": "2026-06-09T18:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, GeminiTimeoutError("timeout"))

    resp = client.post(
        "/api/coach/checklist",
        json={"interview_id": interview_id},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200

    ai_session_queries = [q for q in sb.query_log if q["table"] == "ai_sessions"]
    assert len(ai_session_queries) == 1
    assert any(
        f["field"] == "job_id" and f["value"] == "job-123"
        for f in ai_session_queries[0]["filters"]
    )


def test_post_checklist_uses_company_role_fallback_when_job_query_empty(
    client, fake_user_id: UUID, monkeypatch
):
    uid = str(fake_user_id)
    interview_id = "cccccccc-cccc-cccc-cccc-ccccccccccc6"
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": interview_id,
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "interview_date": "2026-06-10T12:00:00+00:00",
            "job_id": "job-123",
        }
    ]
    tables["ai_sessions"] = [
        {
            "id": "s2",
            "user_id": uid,
            "job_id": "different-job",
            "company": "Acme",
            "role": "Backend Engineer",
            "anxiety_level_after": 7,
            "completed_at": "2026-06-09T20:00:00+00:00",
        }
    ]
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, GeminiTimeoutError("timeout"))

    resp = client.post(
        "/api/coach/checklist",
        json={"interview_id": interview_id},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200

    ai_session_queries = [q for q in sb.query_log if q["table"] == "ai_sessions"]
    assert len(ai_session_queries) == 2
    assert any(
        any(f["field"] == "job_id" and f["value"] == "job-123" for f in q["filters"])
        for q in ai_session_queries
    )
    assert any(
        any(f["field"] == "company" and f["value"] == "Acme" for f in q["filters"])
        and any(
            f["field"] == "role" and f["value"] == "Backend Engineer"
            for f in q["filters"]
        )
        for q in ai_session_queries
    )


def test_post_checklist_interview_not_found_returns_404(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    sb = FakeSupabase(_base_tables(uid))
    _mock_coach_deps(monkeypatch, sb, {"unused": True})

    resp = client.post(
        "/api/coach/checklist",
        json={"interview_id": "cccccccc-cccc-cccc-cccc-ccccccccccc2"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 404


def test_post_checklist_gemini_failure_returns_fallback(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    interview_id = "cccccccc-cccc-cccc-cccc-ccccccccccc3"
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": interview_id,
            "user_id": uid,
            "company": "Zenith",
            "role": "Platform Engineer",
            "interview_date": "2026-06-10T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, GeminiTimeoutError("timeout"))

    resp = client.post(
        "/api/coach/checklist",
        json={"interview_id": interview_id},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["tonights_plan"]) == 3
    assert "Preparation compounds confidence" in body["quote"]


def test_post_checklist_scoped_to_authenticated_user(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    interview_id = "cccccccc-cccc-cccc-cccc-ccccccccccc4"
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": interview_id,
            "user_id": "22222222-2222-2222-2222-222222222222",
            "company": "OtherCo",
            "role": "Other Role",
            "interview_date": "2026-06-10T12:00:00+00:00",
            "job_id": None,
        }
    ]
    sb = FakeSupabase(tables)
    _mock_coach_deps(monkeypatch, sb, {"unused": True})

    resp = client.post(
        "/api/coach/checklist",
        json={"interview_id": interview_id},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 404


def test_get_coach_home_prompt_includes_full_onboarding_fields(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    tables = _base_tables(uid)
    # Explicitly set nulls to verify safe prompt fallback formatting.
    tables["users"][0]["employment_status"] = None
    tables["users"][0]["target_role_category"] = None
    tables["users"][0]["emotional_challenge"] = None
    tables["users"][0]["baseline_anxiety"] = None
    sb = FakeSupabase(tables)
    monkeypatch.setattr(coach_module, "get_supabase_user_client", lambda token: sb)

    captured = {"prompt": ""}

    async def _gemini(prompt: str, **_kwargs):
        captured["prompt"] = prompt
        return {
            "recommended_sessions": [
                {"title": "A", "duration_mins": 10, "focus": "f1", "session_type": "general_reset"},
                {"title": "B", "duration_mins": 8, "focus": "f2", "session_type": "general_reset"},
                {"title": "C", "duration_mins": 12, "focus": "f3", "session_type": "recruiter_call"},
            ],
            "recommended_today": ["i1", "i2", "i3", "i4"],
            "maya_suggests": {"text": "Try a short reset", "session_type": "general_reset", "time_suggestion": "10 min"},
            "maya_greeting": "You're building momentum today.",
        }

    monkeypatch.setattr(coach_module, "generate_gemini_flash_json", _gemini)

    resp = client.get("/api/coach/home", headers={"Authorization": "Bearer fake-token"})
    assert resp.status_code == 200
    prompt = captured["prompt"]
    assert "- employment_status: Not provided" in prompt
    assert "- target_role_category: Not provided" in prompt
    assert "- emotional_challenge: Not provided" in prompt
    assert "- baseline_anxiety: Not provided" in prompt


def test_post_prep_plan_prompt_includes_full_onboarding_fields(client, fake_user_id: UUID, monkeypatch):
    uid = str(fake_user_id)
    interview_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaf"
    tables = _base_tables(uid)
    tables["interviews"] = [
        {
            "id": interview_id,
            "user_id": uid,
            "company": "Acme",
            "role": "Backend Engineer",
            "event_type": "onsite",
            "interview_date": "2026-06-03T12:00:00+00:00",
            "job_id": None,
        }
    ]
    tables["users"][0]["employment_status"] = None
    tables["users"][0]["target_role_category"] = None
    tables["users"][0]["emotional_challenge"] = None
    tables["users"][0]["baseline_anxiety"] = None
    sb = FakeSupabase(tables)
    monkeypatch.setattr(coach_module, "get_supabase_user_client", lambda token: sb)

    captured = {"prompt": ""}

    async def _gemini(prompt: str, **_kwargs):
        captured["prompt"] = prompt
        return {
            "plan": [
                {"day": 1, "task": "Acme role prep", "description": "Backend Engineer focus", "session_type": "general_reset", "duration_mins": 10},
                {"day": 2, "task": "Acme stories", "description": "Backend Engineer examples", "session_type": "interview_tomorrow", "duration_mins": 10},
                {"day": 3, "task": "Acme pressure", "description": "Backend Engineer timing", "session_type": "recruiter_call", "duration_mins": 10},
                {"day": 4, "task": "Acme confidence", "description": "Backend Engineer strengths", "session_type": "general_reset", "duration_mins": 8},
                {"day": 5, "task": "Acme final", "description": "Backend Engineer summary", "session_type": "interview_tomorrow", "duration_mins": 12},
            ],
            "recommended_first_session": {"session_type": "general_reset", "reason": "Start calm", "duration_mins": 10},
            "coach_note": "You are ready.",
        }

    monkeypatch.setattr(coach_module, "generate_gemini_flash_json", _gemini)

    resp = client.post(
        "/api/coach/prep-plan",
        json={"interview_id": interview_id, "worry_input": "I might blank"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert resp.status_code == 200
    prompt = captured["prompt"]
    assert "- employment_status: Not provided" in prompt
    assert "- target_role_category: Not provided" in prompt
    assert "- emotional_challenge: Not provided" in prompt
    assert "- baseline_anxiety: Not provided" in prompt
