from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class ConfidenceDataPoint(BaseModel):
    """Represents a single confidence plot point along a timeframe axis."""

    day: str  # e.g., 'Mon', 'Today', 'Wk 24', or 'Jun'
    value: float


class EmotionalStates(BaseModel):
    """Stores average scores across specific psychological metrics.

    Excludes null values implicitly via optional parameters defaulting to 0.0.
    """

    confidence: Optional[float] = 0.0
    clarity: Optional[float] = 0.0
    calmness: Optional[float] = 0.0
    focus: Optional[float] = 0.0


class ProgressResponse(BaseModel):
    """Final parsed payload structure returned by the GET /api/progress endpoint."""

    avg_confidence: float
    sessions_done: int
    day_streak: int
    avg_lift_per_session: float
    confidence_over_time: List[ConfidenceDataPoint]
    emotional_states: EmotionalStates
    key_insight: str


class GeminiProgressInsight(BaseModel):
    """Schema used strictly for validating structured JSON responses from Gemini."""

    key_insight: str
