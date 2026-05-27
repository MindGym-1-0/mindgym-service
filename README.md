# mindgym-service

FastAPI backend for MindGym - an AI-powered job search companion platform.

## Overview

MindGym Service provides the backend API for the MindGym platform, starting with user onboarding functionality. The service is designed to personalize users' experiences based on their job goals, job search stage, and anxiety levels.

## Project Structure

```
src/
  api/              # API routes and endpoints
    onboarding.py   # Onboarding endpoints
  lib/              # Shared utilities and helpers
  types/            # Pydantic models and type definitions
  config.py         # Application configuration
  main.py           # FastAPI application factory
tst/
  unit/             # Unit tests
  integration/      # Integration tests
  e2e/              # End-to-end tests
```

## Getting Started

### Prerequisites

- Python 3.9+
- pip or conda

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mindgym-service
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install
# or
pip install -r requirements.txt
```

### Running the Server

Start the development server:
```bash
make run
# or
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, view the interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### POST /api/onboard

Complete the onboarding process for a new user.

**Request Body:**
```json
{
  "job_goal": "Senior Software Engineer at a tech company",
  "job_search_stage": "actively_searching",
  "anxiety_level": "moderate"
}
```

**Valid Values:**

Job Search Stages:
- `exploring` - Just beginning to explore options
- `preparing` - Preparing materials and skills
- `actively_searching` - Currently applying to jobs
- `interviewing` - In active interviews

Anxiety Levels:
- `low` - Minimal anxiety
- `moderate` - Moderate anxiety
- `high` - High anxiety
- `very_high` - Severe anxiety

The endpoint also accepts a numeric anxiety score between `1` and `10`. Category values are normalized to the matching score before persisting.

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Onboarding completed successfully",
  "user_id": "user_123"
}
```

**Error Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "job_goal"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Testing

Run the test suite:
```bash
make test
```

Run tests with coverage report:
```bash
make test-cov
```

## Development

### Install Development Dependencies

```bash
make dev
```

### Available Commands

```bash
make help           # Show all available commands
make install        # Install dependencies
make dev            # Install dev dependencies
make test           # Run tests
make test-cov       # Run tests with coverage
make run            # Run development server
make clean          # Clean up cache files
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

Available settings:
- `API_HOST` - Server host (default: 0.0.0.0)
- `API_PORT` - Server port (default: 8000)
- `DEBUG` - Debug mode (default: False)
- `FRONTEND_URL` - Frontend URL for CORS (default: http://localhost:3000)

## Integration with Frontend

The frontend should make a POST request to `/api/onboard` when the user completes the onboarding wizard:

```javascript
const response = await fetch('/api/onboard', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    job_goal: userJobGoal,
    job_search_stage: selectedStage,
    anxiety_level: selectedAnxiety,
  }),
});

if (response.ok) {
  const data = await response.json();
  window.location.href = '/dashboard';
} else {
  const error = await response.json();
  console.error('Onboarding failed:', error);
}
```

