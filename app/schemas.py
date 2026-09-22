from typing import Literal

from pydantic import BaseModel, Field


CriterionName = Literal[
    "skills",
    "experience",
    "education",
    "responsibilities",
    "domain",
]


class JobDescriptionRequest(BaseModel):
    job_description: str = Field(
        min_length=80,
        max_length=30000,
    )


class Criterion(BaseModel):
    name: CriterionName
    requirement: str = Field(min_length=3)
    weight: float = Field(ge=0, le=1)


class CriterionScore(BaseModel):
    name: CriterionName
    requirement: str
    score: float = Field(ge=0, le=100)
    weighted_score: float = Field(ge=0, le=100)
    evidence: list[str] = Field(default_factory=list)
    reasoning: str
    missing: list[str] = Field(default_factory=list)


class FitAssessment(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    criteria: list[CriterionScore]
    summary: str
    calibration_note: str
    latency_ms: float
    parser_warning: str | None = None


class AnalysisResponse(FitAssessment):
    resume_filename: str
    job_criteria: list[Criterion]