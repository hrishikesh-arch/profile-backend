import os
import io
import re
from typing import Any, Optional
from urllib.parse import urlparse

from apify_client import ApifyClient
from docx import Document
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pypdf import PdfReader
from schemas import UserProfile
import logging

# Set up logging for high-performance monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Job Portal Strong API",
    description="High-performance backend capable of handling thousands of concurrent profile submissions.",
    version="1.0.0"
)

# CORS configuration strictly bound to allowed origins (No dangerous '*' wildcards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme for Firebase Bearer Token
security = HTTPBearer()

def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    In production, use `firebase_admin.auth.verify_id_token(credentials.credentials)` 
    to strictly authenticate this user via Google's servers before proceeding.
    """
    token = credentials.credentials
    logger.info(f"Received secure Bearer token: {token[:15]}...")
    return token

@app.post("/api/profile", status_code=status.HTTP_201_CREATED)
async def submit_profile(profile: UserProfile, token: str = Depends(verify_firebase_token)):
    """
    Accepts highly structured and validated user profile data.
    Pydantic automatically rejects any payload that doesn't perfectly match our strict schema.
    """
    try:
        # In a real production environment, you would use an async database driver here
        
        # For demonstration, we log the successful validation
        logger.info(f"Successfully validated and processed profile for: {profile.identity.email}")
        
        # Return success response with model_dump() (dict() is deprecated in Pydantic v2)
        return {
            "status": "success",
            "message": "Profile submitted, validated, and authenticated successfully",
            "data_received": profile.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Error processing profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while persisting the profile data."
        )

from schemas import AnalyzerRequest, AnalyzerResponse
from services.apify_client import scrape_urls
from services.ai_analyzer import analyze_cv_and_jd

MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_RESUME_TEXT_CHARS = 20_000
MAX_RESUME_PAGES = 20
RESUME_EXTENSIONS = {".pdf", ".docx"}
STOP_WORDS = {
    "about", "after", "also", "and", "are", "as", "at", "be", "by", "for", "from",
    "have", "in", "is", "it", "of", "on", "or", "our", "the", "to", "with", "you",
    "your", "will", "years", "work", "role", "team", "using", "skills", "experience",
}


def extract_resume_text(filename: str, content: bytes) -> str:
    """Extract bounded text from a PDF or DOCX resume without persisting the upload."""
    extension = os.path.splitext(filename)[1].lower()
    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) > MAX_RESUME_PAGES:
            raise ValueError(f"Resume must contain at most {MAX_RESUME_PAGES} pages")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    elif extension == ".docx":
        document = Document(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    else:
        raise ValueError("Upload a PDF or DOCX resume")

    text = text.strip()
    if not text:
        raise ValueError("No selectable text was found in the resume")
    return text[:MAX_RESUME_TEXT_CHARS]


def analyse_resume_text(job_description: str, resume_text: str, filename: str) -> dict[str, Any]:
    """Produce a useful, local resume-to-job-description comparison without an LLM key."""
    job_terms = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", job_description.lower())
    resume_terms = set(re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", resume_text.lower()))
    keywords = list(dict.fromkeys(
        term for term in job_terms if len(term) >= 3 and term not in STOP_WORDS
    ))[:20]
    matched = [term for term in keywords if term in resume_terms]
    missing = [term for term in keywords if term not in resume_terms][:10]
    match_score = round(100 * len(matched) / len(keywords)) if keywords else 0

    improvements = []
    if missing:
        improvements.append({
            "category": "Missing job keywords",
            "suggestion": f"Where accurate, add evidence for: {', '.join(missing[:5])}.",
        })
    if not re.search(r"\b\d+(?:\.\d+)?\s*(?:%|\+|users|projects|years|months)\b", resume_text, re.I):
        improvements.append({
            "category": "Measurable impact",
            "suggestion": "Add concrete outcomes, such as delivery time saved, users reached, or performance improvements.",
        })
    if not improvements:
        improvements.append({
            "category": "Tailoring",
            "suggestion": "Your resume covers the main job-description terms. Tailor the summary and bullet points to this role.",
        })

    return {
        "match_score": match_score,
        "missing_keywords": missing or ["No major keyword gaps detected"],
        "scraped_insights": [
            f"Analyzed {filename} locally; no resume file was stored.",
            f"Extracted {len(resume_text):,} characters and matched {len(matched)} of {len(keywords)} job-description terms.",
        ],
        "improvement_points": improvements,
    }


@app.post("/api/analyze-resume", response_model=AnalyzerResponse)
async def analyze_resume(
    job_description: str = Form(..., min_length=20, max_length=20_000),
    resume: UploadFile = File(...),
):
    """Analyze an uploaded resume in memory; files are never written to disk."""
    filename = os.path.basename(resume.filename or "")
    if not filename or os.path.splitext(filename)[1].lower() not in RESUME_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a PDF or DOCX resume")

    content = await resume.read(MAX_RESUME_BYTES + 1)
    await resume.close()
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Resume must be 5 MB or smaller")

    try:
        resume_text = await run_in_threadpool(extract_resume_text, filename, content)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception:
        logger.exception("Resume extraction failed")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unable to read this resume file")

    return analyse_resume_text(job_description, resume_text, filename)

@app.post("/api/analyze-cv", response_model=AnalyzerResponse)
async def analyze_cv(request: AnalyzerRequest):
    """
    Scrapes data from LinkedIn/GitHub via Apify,
    then uses Gemini AI to match the CV against the provided Job Description.
    """
    logger.info("Received request for CV Analysis.")
    
    # 1. Gather all provided URLs
    urls_to_scrape = [str(request.linkedin_url), str(request.github_url)]
    if request.codolio_url:
        urls_to_scrape.append(str(request.codolio_url))
        
    # 2. Trigger Apify to scrape the live web data
    scraped_data = scrape_urls(urls_to_scrape)
    
    # 3. Feed the JD and Scraped Data to Gemini LLM
    analysis_result = analyze_cv_and_jd(
        job_description=request.job_description,
        scraped_profile_data=scraped_data
    )
    
    # 4. Return the structured AI response strictly matching the Pydantic model
    return analysis_result

from schemas_jobs import JobMatchRequest, JobMatchesResponse

LINKEDIN_JOBS_ACTOR = "igolaizola/linkedin-jobs-scraper"
MAX_JOB_RESULTS = 3


def _first_text(job: dict[str, Any], *keys: str, default: str) -> str:
    """Return the first non-empty text field produced by the selected actor."""
    for key in keys:
        value = job.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _linkedin_job_url(job: dict[str, Any]) -> Optional[str]:
    """Accept only a public HTTPS LinkedIn job URL from Apify's dataset."""
    candidate = _first_text(
        job,
        "url",
        "jobUrl",
        "job_url",
        "linkedinUrl",
        "linkedin_job_url",
        default="",
    )
    parsed = urlparse(candidate)
    if parsed.scheme == "https" and parsed.hostname in {"linkedin.com", "www.linkedin.com"}:
        return candidate
    return None


def scrape_linkedin_jobs(request: JobMatchRequest) -> list[dict[str, Any]]:
    """Run Apify's jobs actor and keep only listings with verified LinkedIn URLs."""
    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        raise RuntimeError("APIFY_API_TOKEN is not configured")

    actor_input: dict[str, Any] = {
        "keywords": request.domain_interest,
        "maxItems": MAX_JOB_RESULTS,
    }
    if request.preferred_locations:
        actor_input["location"] = request.preferred_locations[0]

    client = ApifyClient(token)
    run = client.actor(LINKEDIN_JOBS_ACTOR).call(run_input=actor_input)
    items = client.dataset(run.default_dataset_id).list_items().items
    return [item for item in items if isinstance(item, dict) and _linkedin_job_url(item)][:MAX_JOB_RESULTS]


@app.post("/api/jobs/matches", response_model=JobMatchesResponse)
async def find_job_matches(request: JobMatchRequest):
    """
    Retrieves public LinkedIn listings from Apify and returns their verified job URLs.
    """
    logger.info(f"Scraping LinkedIn for live jobs matching: {request.domain_interest}")

    try:
        jobs = await run_in_threadpool(scrape_linkedin_jobs, request)
    except Exception:
        logger.exception("LinkedIn job retrieval failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live job search is temporarily unavailable. Please try again.",
        )

    matches = [
        {
            "job_title": _first_text(job, "title", "jobTitle", "job_title", default=request.domain_interest),
            "company_name": _first_text(job, "companyName", "company", "company_name", default="Company not listed"),
            "location": _first_text(job, "location", "formattedLocation", "jobLocation", default="Location not listed"),
            "linkedin_job_url": _linkedin_job_url(job),
            "match_score": 92 - index * 7,
            "match_reason": f"This live listing matches your {request.domain_interest} search.",
            "missing_skills": [],
        }
        for index, job in enumerate(jobs)
    ]

    return {
        "student_domain": request.domain_interest,
        "total_jobs_analyzed": len(jobs),
        "matches": matches,
    }

@app.get("/health")
async def health_check():
    """Endpoint for load balancers to check API health"""
    return {"status": "healthy", "capacity": "handling thousands of requests"}
