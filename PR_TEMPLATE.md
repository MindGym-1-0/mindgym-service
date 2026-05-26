# Onboarding API Endpoint

## What this PR does
- Implements `/api/onboard` POST endpoint for user onboarding
- Accepts job goal, job search stage, and anxiety level
- Validates all required fields with proper error handling
- Returns user ID on successful onboarding
- Configures CORS for frontend integration
- Includes comprehensive unit tests (9/9 passing)

## How to test
```bash
make install
make test
make run
```
Then POST to `http://localhost:8000/api/onboard` with:
```json
{
  "job_goal": "Senior Software Engineer",
  "job_search_stage": "actively_searching",
  "anxiety_level": "moderate"
}
```

## Notes
- Built with FastAPI + Pydantic
- API documentation available at `/docs`
- Mock implementation ready for database integration
- Tests cover all validation scenarios and enum values
