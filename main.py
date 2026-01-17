from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
from pdf_parser import extract_text_from_pdf
from llm_providers import get_llm_provider

app = FastAPI(title="BioScan API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisResult(BaseModel):
    success_probability: int
    critical_issues: List[Dict[str, str]]
    warnings: List[Dict[str, str]]
    passed_checks: List[Dict[str, str]]
    estimated_cost: Optional[str] = None
    estimated_time: Optional[str] = None
    suggestions: List[str]
    raw_analysis: str

@app.get("/")
async def root():
    return {
        "app": "BioScan - Protocol Validator",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze_protocol(file: UploadFile = File(...)):
    """
    Analyze an experimental protocol for issues and success probability
    
    Args:
        file: PDF file containing the experimental protocol
        
    Returns:
        AnalysisResult with flagged issues, success probability, and suggestions
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check file size (max 20MB)
    contents = await file.read()
    file_size = len(contents)
    if file_size > 20 * 1024 * 1024:  # 20MB
        raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")
    
    try:
        # Extract text from PDF
        protocol_text = extract_text_from_pdf(contents)
        
        if not protocol_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. Make sure it's not a scanned image.")
        
        # Get LLM provider and analyze
        llm_provider = get_llm_provider()
        analysis_result = llm_provider.analyze_protocol(protocol_text)
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing protocol: {str(e)}")

@app.get("/api/providers")
async def get_available_providers():
    """Get available LLM providers"""
    return {
        "available": ["groq", "claude", "openai"],
        "current": os.getenv("LLM_PROVIDER", "groq")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
