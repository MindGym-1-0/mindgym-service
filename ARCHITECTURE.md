# MindGym Service — Architecture Guidelines

This document explains how the backend is structured, why it is structured that way, and how to add new features correctly. Please read this before writing any code.

---

## System Overview

```
mindgym-client (Next.js)
      ↓ HTTP requests
mindgym-service (FastAPI)  ← YOU ARE HERE
      ↓                ↓               ↓
  Supabase DB     Anthropic API    Schedulers
  (Postgres)      (Claude AI)      (cron jobs)
```

- All Anthropic API calls happen in this backend only — never from the frontend
- All business logic lives here — the frontend makes requests and displays results
- Claude is stateless — every API call sends fresh context from the database

---

## Folder Structure

```
mindgym-service/
├── src/
│   ├── main.py        # Single FastAPI entry point — registers routers and middleware only
│   ├── api/           # Route handlers — thin, no business logic
│   ├── lib/           # Business logic, services, shared utilities
│   └── types/         # Pydantic models for requests and responses
├── supabase/
│   └── migrations/    # SQL migration files only
├── tst/
│   ├── unit/          # Unit tests — mirror src/ structure
│   ├── integration/   # Integration tests — API endpoints and database
│   └── e2e/           # End-to-end tests — critical user flows
├── docs/              # Local only, gitignored
├── ARCHITECTURE.md
└── README.md
```

### What goes where — quick reference

| You are writing... | It goes in... |
|---|---|
| A route handler (`@router.post(...)`) | `src/api/` |
| Business logic, service calls | `src/lib/` |
| A Pydantic request or response model | `src/types/` |
| A shared utility (e.g. Supabase client, config) | `src/lib/` |
| A new database migration | `supabase/migrations/` |
| Tests | `tst/unit/`, `tst/integration/`, or `tst/e2e/` |

---

## The Golden Rules

### 1. One entry point only

`src/main.py` is the single FastAPI entry point. There is no other `main.py` anywhere in the project. If you are building a new feature, you register your router here — you do not create a new app.

```python
# src/main.py
from src.api.auth import router as auth_router
from src.api.jobs import router as jobs_router

app.include_router(auth_router, prefix='/api')
app.include_router(jobs_router, prefix='/api')
```

### 2. One import convention

All imports use the `src.` prefix. The server always runs from the repo root — never from a subdirectory.

```python
# Correct
from src.lib.config import get_settings
from src.lib.auth_service import login_with_email_password
from src.types.auth import AuthResponse

# Wrong — only works if running from src/api/, breaks everything else
from app.core.config import get_settings
```

### 3. Keep route handlers thin

Route handlers in `src/api/` do three things only: validate the request, call a function in `src/lib/`, and return the response. Business logic, database calls, and external API calls all live in `src/lib/`.

```python
# src/api/auth.py — correct
@router.post('/login', response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response) -> AuthResponse:
    auth_result = await login_with_email_password(payload.email, payload.password)
    _set_auth_cookies(response, auth_result)
    return _as_auth_response(auth_result)

# Wrong — business logic leaking into the route handler
@router.post('/login')
async def login(payload: LoginRequest):
    client = create_client(...)
    result = client.auth.sign_in_with_password(...)
    if result.session is None:
        raise HTTPException(...)
    ...
```

### 4. One requirements.txt

There is one `requirements.txt` at the repo root. Do not create separate `requirements.txt` files in subdirectories.

### 5. Async all the way down

All route handlers and all functions that touch the database or external APIs must be `async def`. The Supabase Python SDK is synchronous — wrap it with `asyncio.to_thread()`.

```python
# Correct
response = await asyncio.to_thread(client.auth.sign_in_with_password, credentials)

# Wrong — blocks the event loop
response = client.auth.sign_in_with_password(credentials)
```

---

## How to Add a New Feature

Follow these steps every time. Do not skip steps.

**1. Create your Pydantic models first**
```
src/types/your_feature.py
```

**2. Write your service logic**
```
src/lib/your_feature_service.py
```

**3. Write your route handler**
```
src/api/your_feature.py
```

**4. Register your router in `src/main.py`**
```python
from src.api.your_feature import router as your_feature_router
app.include_router(your_feature_router, prefix='/api')
```

**5. Write tests before or alongside your code**
```
tst/unit/test_your_feature_service.py
tst/integration/test_your_feature_api.py
```

**6. Add any new database tables as a migration file**
```
supabase/migrations/YYYYMMDD_your_feature.sql
```

---

## Key Patterns

### Pydantic for everything

Every request body and every response must be a Pydantic model. No raw `dict` at the API boundary.

```python
# src/types/jobs.py
class CreateJobRequest(BaseModel):
    title: str
    company: str
    status: JobStatus = JobStatus.APPLIED

class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    status: JobStatus
    applied_at: datetime | None
```

### Supabase client — user-scoped, never service role for user data

Pass the user's JWT to scope queries to that user. Never use the service role key to fetch or mutate user data — it bypasses Row Level Security.

```python
# Correct — RLS enforced
client.postgrest.auth(user_token)
result = await asyncio.to_thread(client.table('jobs').select('*').execute)

# Wrong — bypasses RLS, returns all users' data
admin_client.table('jobs').select('*').execute()
```

### Error handling — classify, never expose raw exceptions

Catch exceptions from external services (Supabase, Anthropic), classify them into meaningful domain errors, and raise `HTTPException` with a safe message. Never let a raw exception reach the client.

```python
# Correct
try:
    response = await asyncio.to_thread(client.auth.sign_in_with_password, credentials)
except Exception as exc:
    if 'invalid login credentials' in str(exc).lower():
        raise AuthenticationError('Invalid email or password') from exc
    raise UpstreamAuthServiceError('Authentication provider unavailable') from exc

# Wrong — exposes internal error details to the client
except Exception as exc:
    raise HTTPException(status_code=500, detail=str(exc))
```

### SSE for AI-generated content

All Anthropic Claude API calls must stream via Server-Sent Events. Never buffer a full AI response before sending — it will time out.

```python
from fastapi.responses import StreamingResponse

@router.post('/session/generate')
async def generate_session(payload: SessionRequest) -> StreamingResponse:
    return StreamingResponse(stream_session(payload), media_type='text/event-stream')
```

---

## Database Conventions

- RLS is enabled on all tables — always use `(SELECT auth.uid())` in policies
- All timestamps are `timestamptz` — never `timestamp`
- Migration files are named `YYYYMMDD_description.sql`
- Never alter a migration that has already been merged — create a new one

### Field contracts

| Field | Type | Values |
|---|---|---|
| `jobs.status` | `text` | `applied`, `screen`, `hm`, `deep`, `final`, `offer`, `closed` |
| `meditation_sessions.type` | `text` | `phone_screen`, `hm_round`, `final_round`, `negotiation`, `first_day`, `rejection_recovery`, `networking_event`, `cold_outreach` |
| `anxiety_level` | `integer` | 1–10 |
| `mood_before` / `mood_after` / `mood_logs.score` | `integer` | 1–10 |
| `applied_at` / `last_active` | `timestamptz` | — |

---

## What Does Not Belong Here

| This... | Goes here instead |
|---|---|
| Anthropic API calls | This backend only — never the frontend |
| Business logic | `src/lib/` — never in route handlers |
| A second `main.py` | There is only one — `src/main.py` |
| Hardcoded secrets or API keys | `.env` file, loaded via `Settings` in `src/lib/config.py` |
| Hardcoded CORS origins | `Settings.cors_origins` loaded from environment |
| Synchronous database calls | Wrap with `asyncio.to_thread()` |
| Raw `dict` at API boundaries | Use Pydantic models |
