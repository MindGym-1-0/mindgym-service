"""Pydantic models for session request and response validation"""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SessionStartRequest(BaseModel):
    preparation_for: Literal[
        'interview_tomorrow',
        'recruiter_call',
        'networking',
        'salary_negotiation',
        'rejection_recovery',
        'restarting_search',
        'general_reset',
    ]
    # Structured calibration key — must be one of the 5 known chips.
    # Free-text context lives in feeling_note (separate field, prompt-only).
    current_feeling: Literal[
        'overwhelmed',
        'discouraged',
        'exhausted',
        'unsure',
        'anxious but hopeful',
    ]
    feeling_note: str | None = Field(None, max_length=500)
    desired_feeling: Literal[
        'calm',
        'grounded',
        'confident',
        'focused',
        'clear_minded',
        'composed',
    ]
    time_available: Literal['5 min', '10 min', '15 min']
    anxiety_level_before: int = Field(..., ge=1, le=10)
    interview_id: UUID | None = None
    company: str | None = None
    role: str | None = None

    _MODE1_TYPES = {'interview_tomorrow', 'recruiter_call'}

    @model_validator(mode='after')
    def require_company_and_role_for_mode1(self) -> 'SessionStartRequest':
        if self.preparation_for in self._MODE1_TYPES:
            if not self.company or not self.role:
                raise ValueError(
                    f"'company' and 'role' are required for preparation_for='{self.preparation_for}'"
                )
        return self


class SessionScript(BaseModel):
    phase1: str = Field(min_length=20)
    phase2: str = Field(min_length=20)
    phase3: str = Field(min_length=20)
    phase4: str = Field(min_length=20)
    phase5: str = Field(min_length=20)


class SessionStartResponse(BaseModel):
    session_id: str
    script: SessionScript
    mode: str  # echoes preparation_for back to the frontend


class SessionCompleteRequest(BaseModel):
    session_id: str
    anxiety_level_after: int = Field(..., ge=1, le=10)


class SessionCompleteResponse(BaseModel):
    session_id: str
    anxiety_level_before: int
    anxiety_level_after: int
    anxiety_level_delta: int
    message: str


class SessionHistoryItem(BaseModel):
    id: str
    preparation_for: str
    anxiety_level_before: int
    anxiety_level_after: int | None
    anxiety_level_delta: int | None
    completed_at: str | None
    created_at: str


class SessionDetail(BaseModel):
    id: str
    preparation_for: str
    current_feeling: str
    desired_feeling: str
    time_available: str
    company: str | None = None
    role: str | None = None
    feeling_note: str | None = None
    anxiety_level_before: int
    anxiety_level_after: int | None
    anxiety_level_delta: int | None
    script: SessionScript
    completed_at: str | None
    created_at: str


class UserUpdateRequest(BaseModel):
    goal: str | None = None
    stage: str | None = None
