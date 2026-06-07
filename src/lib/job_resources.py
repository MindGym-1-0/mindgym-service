"""Job search tool resources curated by Claire — unwired pending placement decision."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobTool:
    name: str
    url: str
    description: str
    best_for: str


JOB_TOOLS: tuple[JobTool, ...] = (
    JobTool(
        name="Resume-Now",
        url="https://www.resume-now.com",
        description="AI-assisted resume builder with ATS-optimised templates.",
        best_for="Building or refreshing a resume quickly",
    ),
    JobTool(
        name="Teal",
        url="https://www.tealhq.com",
        description="Job application tracker with resume tailoring and job match scoring.",
        best_for="Tracking applications and tailoring resumes per role",
    ),
    JobTool(
        name="Interviewer.AI",
        url="https://interviewer.ai",
        description="AI video interview practice with real-time feedback on delivery.",
        best_for="Practising interview answers and reducing camera anxiety",
    ),
    JobTool(
        name="LoopCV",
        url="https://www.loopcv.pro",
        description="Automated job application tool that applies on your behalf at scale.",
        best_for="Running a high-volume passive application campaign",
    ),
    JobTool(
        name="JobCopilot",
        url="https://jobcopilot.com",
        description="AI job search assistant that automates applications and tracks responses.",
        best_for="Automating outreach while keeping the pipeline organised",
    ),
)
