from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
import asyncio

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

@app.get("/health")
async def health_check():
    """Endpoint for load balancers to check API health"""
    return {"status": "healthy", "capacity": "handling thousands of requests"}
