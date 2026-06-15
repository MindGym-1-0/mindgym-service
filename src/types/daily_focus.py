from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActionType(str, Enum):
    # Aligned with PostgreSQL action_routing_type enum constraints
    PREPARE_INTERVIEW = "prepare_questions"
    ADD_APPLICATIONS = "add_applications"
    FOLLOW_UP = "follow_up"
    LOG_DEBRIEF = "log_debrief"
    GENERIC_PIPELINE = "review_week"


class DailyFocusOutput(BaseModel):
    action_1_text: str = Field(..., min_length=1)
    action_1_type: ActionType
    action_2_text: Optional[str] = None
    action_2_type: Optional[ActionType] = None


class DailyFocusResponse(BaseModel):
    id: UUID
    user_id: UUID
    date: str
    action_1_text: str
    action_1_type: ActionType
    action_2_text: Optional[str] = None
    action_2_type: Optional[ActionType] = None
    created_at: str  # Fixed: was generated_at which didn't match the DB column
    updated_at: str
    model_config = ConfigDict(from_attributes=True)


DailyFocusResponse.model_rebuild()
DailyFocusOutput.model_rebuild()
