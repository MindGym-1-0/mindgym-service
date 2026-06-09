from __future__ import annotations

from pydantic import BaseModel


class ProgressResponse(BaseModel):
    """Final parsed payload structure returned by the GET /api/progress endpoint."""

    sessions_done: int
    day_streak: int
    avg_lift_per_session: float
    key_insight: str


class ProgressInsight(BaseModel):
    """Schema used strictly for validating structured JSON coaching responses from the AI provider."""

    key_insight: str
