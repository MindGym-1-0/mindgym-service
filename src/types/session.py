"""Pydantic models for session request and response validation"""
from typing import Literal

from pydantic import BaseModel, Field


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
    current_feeling: str  # chip selection or free text from the user
    desired_feeling: Literal[
        'calm',
        'grounded',
        'confident',
        'focused',
        'clear_minded',
        'composed',
    ]
    time_available: Literal['5 min', '10 min', '15 min']
    pre_score: int = Field(..., ge=1, le=10)
    company: str | None = None
    role: str | None = None


class SessionScript(BaseModel):
    phase1: str
    phase2: str
    phase3: str
    phase4: str
    phase5: str


class SessionStartResponse(BaseModel):
    session_id: str
    script: SessionScript
    mode: str  # echoes preparation_for back to the frontend
    fallback_used: bool


class SessionCompleteRequest(BaseModel):
    session_id: str
    post_score: int = Field(..., ge=1, le=10)


class SessionCompleteResponse(BaseModel):
    session_id: str
    pre_score: int
    post_score: int
    mood_delta: int
    message: str


class SessionHistoryItem(BaseModel):
    id: str
    preparation_for: str
    pre_score: int
    post_score: int | None
    mood_delta: int | None
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
    pre_score: int
    post_score: int | None
    mood_delta: int | None
    script: SessionScript
    fallback_used: bool
    completed_at: str | None
    created_at: str


class UserUpdateRequest(BaseModel):
    goal: str | None = None
    stage: str | None = None
    anxiety_level: int | None = Field(default=None, ge=1, le=10)
