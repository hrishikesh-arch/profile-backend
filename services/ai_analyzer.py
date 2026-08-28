import os
import google.generativeai as genai
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configure the Gemini API with the key from .env
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use the latest lightweight but capable model
model = genai.GenerativeModel('gemini-1.5-flash')

def analyze_cv_and_jd(job_description: str, scraped_profile_data: str) -> dict:
    """
    Sends the JD and Scraped Web Data to Gemini to perform a deep gap analysis.
    Forces Gemini to return the exact JSON structure required by our FastAPI schema.
    """
    
    prompt = f"""
    You are an expert technical recruiter and resume optimizer. 
    Analyze the provided Job Description against the candidate's scraped web profile data (LinkedIn/GitHub/Codolio).
    
    Job Description:
    {job_description}
    
    Candidate's Scraped Profile Data:
    {scraped_profile_data}
    
    You MUST output valid JSON matching this exact structure:
    {{
        "match_score": 85, // integer 0-100
        "missing_keywords": ["keyword1", "keyword2"], // List of strings
        "scraped_insights": ["Insight about their GitHub", "Insight about LinkedIn"], // List of strings
        "improvement_points": [
            {{
                "category": "Action Verbs", // string
                "suggestion": "string explaining how to improve",
                "original_text": "string (optional)",
                "improved_text": "string (optional)"
            }}
        ]
    }}
    
    Return ONLY JSON. No markdown backticks, no explanations outside the JSON object.
    """

    try:
        logger.info("Sending payload to Gemini LLM for analysis...")
        response = model.generate_content(prompt)
        
        # Clean up the response in case Gemini includes markdown backticks like ```json
        raw_json = response.text.replace('```json', '').replace('```', '').strip()
        
        # Parse into a dictionary
        result_dict = json.loads(raw_json)
        logger.info("Gemini analysis completed successfully.")
        return result_dict

    except Exception as e:
        logger.error(f"Gemini AI failed: {e}")
        # Fallback response in case of API failure or bad JSON format
        return {
            "match_score": 0,
            "missing_keywords": ["Error occurred during AI analysis"],
            "scraped_insights": ["Please try again or check API key quota."],
            "improvement_points": []
        }
