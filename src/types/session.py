"""Pydantic models for session request and response validation"""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


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
    desired_feeling: list[Literal[
        'calm',
        'grounded',
        'confident',
        'focused',
        'clear_minded',
        'composed',
    ]]
    time_available: Literal['5 min', '10 min', '15 min']
    anxiety_level_before: int = Field(..., ge=1, le=10)
    interview_id: UUID | None = None
    company: str | None = None
    role: str | None = None

    _MODE1_TYPES = {'interview_tomorrow', 'recruiter_call'}

    @field_validator('desired_feeling')
    @classmethod
    def validate_desired_feeling(cls, v: list) -> list:
        if len(v) < 1:
            raise ValueError('desired_feeling must have at least 1 selection')
        if len(v) > 2:
            raise ValueError('desired_feeling allows at most 2 selections')
        return v

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


class RecommendedAction(BaseModel):
    title: str
    body: str
    timing: str


class SessionCompleteResponse(BaseModel):
    session_id: str
    anxiety_level_before: int
    anxiety_level_after: int
    anxiety_level_delta: int
    session_number: int
    recommended_actions: list['RecommendedAction']
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
    current_feeling: str | None = None
    desired_feeling: str | None = None
    time_available: str | None = None
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
