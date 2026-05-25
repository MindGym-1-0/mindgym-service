from __future__ import annotations
from datetime import datetime, date
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ActionType(str, Enum):
    PREPARE_INTERVIEW = "PREPARE_INTERVIEW"
    ADD_APPLICATIONS = "ADD_APPLICATIONS"
    FOLLOW_UP = "FOLLOW_UP"
    LOG_DEBRIEF = "LOG_DEBRIEF"
    GENERIC_PIPELINE = "GENERIC_PIPELINE"


class GeminiDailyFocusOutput(BaseModel):
    action_1_text: str = Field(..., min_length=1)
    action_1_type: ActionType
    action_2_text: Optional[str] = None
    action_2_type: Optional[ActionType] = None


class DailyFocusResponse(BaseModel):
    id: UUID
    user_id: UUID
    date: date
    action_1_text: str
    action_1_type: ActionType
    action_2_text: Optional[str] = None
    action_2_type: Optional[ActionType] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


DailyFocusResponse.model_rebuild()
GeminiDailyFocusOutput.model_rebuild()
