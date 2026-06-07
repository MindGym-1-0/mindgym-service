from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class TopInsightItem(BaseModel):
    text: str = Field(..., description="Short headline, max 8 words.")
    detail: str = Field(..., description="Supporting detail containing metrics.")
    highlight: bool = True


class SecondaryInsightItem(BaseModel):
    text: str = Field(..., description="Short insight statement.")


class HiringFunnelGap(BaseModel):
    title: str = Field("Hiring Funnel Gap Identified")
    body: str = Field(..., description="2-3 actionable sentences.")
    based_on: str = Field(..., description="Format: N sessions · X% · Y%")


class InsightsResponse(BaseModel):
    top_insights: List[TopInsightItem]
    secondary_insights: List[SecondaryInsightItem]
    hiring_funnel_gap: Optional[HiringFunnelGap] = None
