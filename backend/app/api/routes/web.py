from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.services.web_retrieval import get_web_retrieval_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web", tags=["Official Web Retrieval"])

class WebSearchRequest(BaseModel):
    query: str = Field(..., description="Search terms (e.g., 'IS 17526 water bottle BIS QCO mandate')", min_length=3)
    max_results: int = Field(5, ge=1, le=15)

@router.post("/search", summary="Search and Retrieve Authoritative BIS/Gov Web Sources")
async def web_search(payload: WebSearchRequest):
    """
    Search web with domain authority ranking prioritizing:
    - bis.gov.in (100)
    - nic.in / gov.in (90-95)
    - nist / iso / iec (90-95)
    Fetches actual readable passages and reports authority scores.
    """
    try:
        service = get_web_retrieval_service()
        results = await service.search(query=payload.query, max_results=payload.max_results)

        return {
            "success": True,
            "query": payload.query,
            "total_found": len(results),
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "domain": r.domain,
                    "authority_score": r.authority_score,
                    "relevance_score": round(r.relevance_score, 3),
                    "combined_score": round(r.combined_score, 3),
                    "fetch_time_seconds": round(r.fetch_time, 3),
                    "is_official": r.authority_score >= 85
                } for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Web retrieval failed: {e}")
        return {
            "success": False,
            "query": payload.query,
            "total_found": 0,
            "results": [],
            "message": f"Web retrieval unavailable: {str(e)}"
        }
