from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

class JobMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_interest: str = Field(..., description="E.g., Frontend Developer, Data Scientist")
    skills: List[str] = Field(..., description="List of student skills")
    preferred_locations: List[str] = Field(default_factory=list)

class JobMatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_title: str
    company_name: str
    location: str
    linkedin_job_url: Optional[HttpUrl] = None
    match_score: int = Field(..., ge=0, le=100)
    match_reason: str
    missing_skills: List[str]

class JobMatchesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_domain: str
    total_jobs_analyzed: int
    matches: List[JobMatchResult]
