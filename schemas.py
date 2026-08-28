from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import List, Optional, Literal
from datetime import date

class Identity(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+?\d{10,15}$', description="Valid phone number")
    aadhaar_number: str = Field(..., pattern=r'^\d{12}$', description="12-digit numeric UID")
    dob: date = Field(..., description="YYYY-MM-DD format strictly enforced as date object")
    gender: Literal["Male", "Female", "Other", "Prefer not to say"]
    category: Literal["General", "OBC", "SC", "ST", "EWS"]
    location: str
    photo_url: Optional[HttpUrl] = None

class Academic(BaseModel):
    institute_type: Literal["AICTE Affiliated", "Non-AICTE", "UGC", "Other"]
    institute_state: str = Field(..., description="State where the institute is located")
    aishe_code: str = Field(..., description="All India Survey on Higher Education Code")
    institution: str
    degree: str
    branch: str
    year_of_study: Literal["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "Graduated"]
    graduation_year: int = Field(..., ge=2000, le=2100)
    cgpa: float = Field(..., ge=0.0, le=100.0)
    transcript_url: Optional[HttpUrl] = None
    roll_number: str

class Experience(BaseModel):
    company: str
    role: str
    duration: str
    description: List[str]

class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: Optional[int] = None

class Skill(BaseModel):
    name: str
    category: str

class Certification(BaseModel):
    title: str
    issuing_authority: str
    verification_url: Optional[HttpUrl] = None

class PortfolioProject(BaseModel):
    title: str
    tech_stack: List[str]
    description: str
    link: Optional[HttpUrl] = None

class ProjectData(BaseModel):
    skills_tags: List[str]
    availability: Literal["Immediate", "Part-time", "Full-time", "Specific Months"]
    availability_hours_per_week: int = Field(..., ge=0, le=168)
    project_preference: str 
    domain_interest: str
    preferred_locations: List[str]

class Scheduling(BaseModel):
    timezone: str
    preferred_interview_mode: str
    calendar_integration_consent: bool = False

class UserProfile(BaseModel):
    identity: Identity
    academic: Academic
    work_experience: List[Experience] = []
    education_history: List[Education] = []
    skills: List[Skill] = []
    certifications: List[Certification] = []
    projects: List[PortfolioProject] = []
    project_data: ProjectData
    scheduling: Scheduling
    linkedin_url: Optional[HttpUrl] = None
    resume_url: Optional[HttpUrl] = None

class AnalyzerRequest(BaseModel):
    job_description: str = Field(..., description="The target JD text")
    linkedin_url: HttpUrl
    github_url: HttpUrl
    codolio_url: Optional[HttpUrl] = None

class ImprovementPoint(BaseModel):
    category: str
    suggestion: str
    original_text: Optional[str] = None
    improved_text: Optional[str] = None

class AnalyzerResponse(BaseModel):
    match_score: int = Field(..., ge=0, le=100)
    missing_keywords: List[str]
    scraped_insights: List[str]
    improvement_points: List[ImprovementPoint]
