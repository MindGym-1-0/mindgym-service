# mindgym-service

Mind Gym Job Tracker backend (FastAPI + Supabase).

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in `.env`.

## Run locally

From the repo root:

```powershell
python -m uvicorn src.main:app --reload --port 8000
```

- API docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

### Test login locally

1. Copy `.env.example` to `.env` and set Supabase keys.
2. Start the API (command above).
3. Run unit tests: `pytest tst/unit/test_auth_api.py tst/unit/test_auth_service.py -q`
4. Optional live smoke test against Supabase (use a real beta test user):

```bash
export LOGIN_TEST_EMAIL="you@example.com"
export LOGIN_TEST_PASSWORD="your-password"
chmod +x scripts/smoke-login.sh
./scripts/smoke-login.sh
```

5. In `mindgym-client`, copy `.env.example` to `.env.local`, set the same Supabase project values, run `npm run dev`, then sign in at http://localhost:3000/login.

## Tests

```powershell
pytest
```

## Layout

- `src/main.py` — FastAPI app
- `src/api/jobs.py` — `POST` / `GET` `/api/jobs`
- `src/api/jobs_id.py` — `PATCH` / `DELETE` `/api/jobs/{id}`
- `src/lib/` — config, Supabase client, auth, token parsing
- `src/types/job.py` — Pydantic models
- `tst/unit/` — unit tests (mocked Supabase)
