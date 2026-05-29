"""Pydantic models for request and response validation"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from pydantic import model_validator
from src.types.session import SessionScript

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

    def score(self) -> int:
        return {
            self.LOW: 1,
            self.MODERATE: 4,
            self.HIGH: 7,
            self.VERY_HIGH: 10,
        }[self]


class OnboardingRequest(BaseModel):
    """Request payload for user onboarding"""

    employment_status: Literal["employed", "unemployed", "laid_off"]
    unemployed_duration: Literal["1m", "2m", "3m", "6m", "1y", "1y+"] | None = None
    job_timeline: Literal["asap", "3m", "6m", "12m"]
    target_role_category: Literal["product_design_ux", "product_management", "software_engineering", "data_analytics", "marketing", "sales", "operations", "finance", "people_hr", "leadership_executive", "not_sure"]
    target_role_note: str | None = None
    company_types: list[Literal["startup", "scale_up", "large_tech", "enterprise", "any"]] = Field(..., min_length=1)
    applications_sent_min: int | None = None
    applications_sent_max: int | None = None
    recruiter_contacts: int | None = None
    first_round_interviews: int | None = None
    final_round_interviews: int | None = None
    offers: int | None = None
    emotional_challenge: Literal["rejection_silence", "interview_anxiety", "imposter_syndrome", "burnout", "uncertainty", "financial_pressure"]
    baseline_anxiety: int = Field(ge=1, le=10, description="Current anxiety level on a 1-10 scale"
    )

    @model_validator(mode="after")
    def check_unemployed_duration(self):
        if self.employment_status in ("unemployed", "laid_off") and self.unemployed_duration is None:
            raise ValueError("unemployed_duration is required when not employed")
        return self

    model_config = {
    "json_schema_extra": {
        "example": {
            "employment_status": "unemployed",
            "unemployed_duration": "3m",
            "job_timeline": "asap",
            "target_role_category": "product_management",
            "target_role_note": "Senior PM in fintech",
            "company_types": ["startup", "scale_up"],
            "applications_sent_min": 10,
            "applications_sent_max": 15,
            "recruiter_contacts": 3,
            "first_round_interviews": 2,
            "final_round_interviews": 1,
            "offers": 0,
            "emotional_challenge": "rejection_silence",
            "baseline_anxiety": 7,
        }
    }
    }

class OnboardingGapAnalysis(BaseModel):
    mindset_gap: str
    mindset_gap_detail: str
    hunting_gap: str | None = None
    hunting_gap_detail: str | None = None
    baseline_anxiety_note: str


class OnboardingFirstSession(BaseModel):
    session_id: str
    preparation_for: str
    session_title: str
    session_description: str
    session_tags: list[str]
    script: SessionScript


class OnboardingResponse(BaseModel):
    """Response payload after successful onboarding"""

    success: bool
    user_id: str | None = None
    gap_analysis: OnboardingGapAnalysis
    first_session: OnboardingFirstSession

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "user_id": "user_123",
            }
        }
