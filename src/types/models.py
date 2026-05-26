"""Pydantic models for request and response validation"""

from enum import Enum
from typing import Union
from pydantic import BaseModel, Field


class JobSearchStage(str, Enum):
    """Current stage in the job search process"""

    SENDING_APPLICATIONS = "Sending applications"
    GETTING_RECRUITER_CALLS = "Getting recruiter calls"
    IN_INTERVIEWS = "In interviews"
    FINAL_ROUNDS_OFFERS = "Final rounds / offers"


class MoodChallenge(str, Enum):
    """Emotional challenge options shown during onboarding"""

    INTERVIEW_ANXIETY = "interview-anxiety"
    OVERTHINKING = "overthinking"
    REJECTION = "rejection"
    BURNOUT = "burnout"
    MOTIVATION = "motivation"
    CONFIDENCE = "confidence"


class OnboardingRequest(BaseModel):
    """Request payload for user onboarding"""

    job_goal: str = Field(
        ..., min_length=1, max_length=500, description="User's job goal or desired role"
    )
    job_search_stage: JobSearchStage = Field(
        ..., description="Current stage in the job search"
    )
    mood: Union[MoodChallenge, str] = Field(
        ..., min_length=1, description="Emotional challenge selected during onboarding"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "job_goal": "Senior Software Engineer at a tech company",
                "job_search_stage": "Sending applications",
                "mood": "interview-anxiety",
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
                "user_id": "user_123",
            }
        }
