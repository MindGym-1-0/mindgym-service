from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendedSession(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., min_length=1)
    duration_mins: int
    focus: str = Field(..., min_length=1)
    session_type: str = Field(..., min_length=1)


class MayaSuggests(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(..., min_length=1)
    session_type: str = Field(..., min_length=1)
    time_suggestion: str = Field(..., min_length=1)


class CoachHomeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recommended_sessions: list[RecommendedSession]
    recommended_today: list[str]
    maya_suggests: MayaSuggests
    maya_greeting: str = Field(..., min_length=1)


class PrepPlanItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: int
    task: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    session_type: str = Field(..., min_length=1)
    duration_mins: int


class RecommendedFirstSession(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_type: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)
    duration_mins: int


class CoachPrepPlanRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    interview_id: UUID
    worry_input: str = Field(..., min_length=1)

    @field_validator("worry_input", mode="before")
    @classmethod
    def strip_and_validate_worry_input(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("worry_input cannot be empty or whitespace.")
            return stripped
        return value


class CoachPrepPlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan: list[PrepPlanItem]
    recommended_first_session: RecommendedFirstSession
    coach_note: str = Field(..., min_length=1)


class SavedCoachPrepPlanResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan: list[PrepPlanItem]
    recommended_first_session: RecommendedFirstSession
    coach_note: str = Field(..., min_length=1)
    created_at: datetime
