from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class InterviewCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    interview_date: datetime
    event_type: str = Field(..., min_length=1)
    job_id: str | None = None
    notes: str | None = None


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
    created_at: datetime


class InterviewListResponse(BaseModel):
    upcoming: list[InterviewResponse]
    past: list[InterviewResponse]
