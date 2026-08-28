from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

class JobMatchRequest(BaseModel):
    domain_interest: str = Field(..., description="E.g., Frontend Developer, Data Scientist")
    skills: List[str] = Field(..., description="List of student skills")
    preferred_locations: List[str] = []

class JobMatchResult(BaseModel):
    job_title: str
    company_name: str
    location: str
    linkedin_job_url: Optional[HttpUrl] = None
    match_score: int = Field(..., ge=0, le=100)
    match_reason: str
    missing_skills: List[str]

class JobMatchesResponse(BaseModel):
    student_domain: str
    total_jobs_analyzed: int
    matches: List[JobMatchResult]
