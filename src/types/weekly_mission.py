from datetime import date, datetime

from pydantic import BaseModel, Field


class WeeklyMissionGenerateResponse(BaseModel):
    id: str
    user_id: str
    week_start_date: date
    action_1: str
    action_1_completed: bool
    action_2: str
    action_2_completed: bool
    action_3: str
    action_3_completed: bool
    completion_count: int
    generated_at: datetime
    updated_at: datetime


class GeminiMissionOutput(BaseModel):
    action_1: str = Field(..., description="First tailored weekly action string")
    action_2: str = Field(..., description="Second tailored weekly action string")
    action_3: str = Field(..., description="Third tailored weekly action string")
