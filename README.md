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
- Health: http://127.0.0.1:8000/healthz  

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
