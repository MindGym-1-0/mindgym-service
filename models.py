"""Pydantic models for request and response validation"""
from enum import Enum
from pydantic import BaseModel, Field


class JobSearchStage(str, Enum):
    """Current stage in the job search process"""
    EXPLORING = "exploring"
    PREPARING = "preparing"
    ACTIVELY_SEARCHING = "actively_searching"
    INTERVIEWING = "interviewing"


class AnxietyLevel(str, Enum):
    """User's current anxiety level"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class OnboardingRequest(BaseModel):
    """Request payload for user onboarding"""
    job_goal: str = Field(..., min_length=1, max_length=500, description="User's job goal or desired role")
    job_search_stage: JobSearchStage = Field(..., description="Current stage in the job search")
    anxiety_level: AnxietyLevel = Field(..., description="Current anxiety level")

    class Config:
        json_schema_extra = {
            "example": {
                "job_goal": "Senior Software Engineer at a tech company",
                "job_search_stage": "actively_searching",
                "anxiety_level": "moderate"
            }
        }


class OnboardingResponse(BaseModel):
    """Response payload after successful onboarding"""
    success: bool
    message: str
    user_id: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Onboarding completed successfully",
                "user_id": "user_123"
            }
        }
