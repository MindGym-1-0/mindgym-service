# src/types/mood_log.py

from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class MoodLogCreate(BaseModel):
    user_id: UUID
    score: int = Field(
        ..., ge=1, le=10, description="Score must be an integer between 1 and 10"
    )
    note: Optional[str] = None


class MoodLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    score: int
    note: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Summary Types ---


class DailyMoodHistoryItem(BaseModel):
    date: str  # Format: "YYYY-MM-DD"
    score: Optional[int] = None


class MoodLogSummaryResponse(BaseModel):
    avg_score: Optional[float] = None
    total_logs: int
    last_7_days: list[DailyMoodHistoryItem]  # 💡 Swapped List -> list here

    model_config = ConfigDict(from_attributes=True)


# Force Pydantic to fully compile all forward-referenced types immediately
MoodLogSummaryResponse.model_rebuild()
