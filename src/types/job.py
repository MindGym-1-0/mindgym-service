from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobStatus(str, Enum):
    APPLIED = "applied"
    SCREEN = "screen"
    HM = "hm"
    DEEP = "deep"
    FINAL = "final"
    OFFER = "offer"
    CLOSED = "closed"


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    notes: str | None = None
    applied_at: datetime | None = None
    status: JobStatus | None = None

    @field_validator("company", "role", mode="before")
    @classmethod
    def strip_and_validate_not_empty(cls, value: str) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("String cannot be empty or just whitespace.")
            return stripped
        return value


class JobUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    company: str | None = Field(default=None, min_length=1)
    role: str | None = Field(default=None, min_length=1)
    notes: str | None = None
    applied_at: datetime | None = None
    status: JobStatus | None = None

    @field_validator("company", "role", mode="before")
    @classmethod
    def strip_and_validate_not_empty(cls, value: str | None) -> str | None:
        if value is not None and isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("String cannot be empty or just whitespace.")
            return stripped
        return value


class JobResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    user_id: UUID
    company: str
    role: str
    status: JobStatus
    applied_at: datetime | None = None
    notes: str | None = None

    # New database-tracking tracking fields added below
    last_moved_at: datetime | None = None
    outcome: str | None = None

    created_at: datetime | None = None


class DeleteOk(BaseModel):
    success: bool = True
