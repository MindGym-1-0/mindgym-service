from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    applied = "applied"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"


class JobCreate(BaseModel):
    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    notes: str | None = None
    applied_at: date | datetime | None = None
    status: JobStatus | None = None


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str | None = Field(default=None, min_length=1)
    role: str | None = Field(default=None, min_length=1)
    notes: str | None = None
    applied_at: date | datetime | None = None
    status: JobStatus | None = None


class JobResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    user_id: UUID
    company: str
    role: str
    status: str

    applied_at: str | datetime | date | None = None
    notes: str | None = None
    created_at: str | datetime | None = None


class DeleteOk(BaseModel):
    success: bool = True
