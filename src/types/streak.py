from pydantic import BaseModel, ConfigDict
from typing import Optional


class StreakIncrementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_streak: int
    longest_streak: int
    milestone: Optional[int] = None


class StreakGetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    current_streak: int
    longest_streak: int
