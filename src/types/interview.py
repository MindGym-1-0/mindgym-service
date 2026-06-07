from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class InterviewOutcome(str, Enum):
    OFFER = "offer"
    NO_OFFER = "no_offer"
    AWAITING = "awaiting"
    PENDING = "pending"


class InterviewCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    interview_date: datetime
    event_type: str = Field(..., min_length=1)
    job_id: str | None = None
    notes: str | None = None


class InterviewOutcomeUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    outcome: InterviewOutcome
    from_not_ready: bool = False


class InterviewOutcomeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    outcome: InterviewOutcome = InterviewOutcome.PENDING
    check_in_attempts: int | None = None
    next_check_in_at: datetime | None = None


class InterviewResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    user_id: str
    company: str
    role: str
    interview_date: datetime
    event_type: str
    job_id: str | None = None
    notes: str | None = None
    outcome: InterviewOutcome = InterviewOutcome.PENDING
    check_in_attempts: int | None = None
    next_check_in_at: datetime | None = None
    created_at: datetime


class InterviewListResponse(BaseModel):
    upcoming: list[InterviewResponse]
    past: list[InterviewResponse]
