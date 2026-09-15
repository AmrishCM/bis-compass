from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging

from app.services.products.open_world_analyzer import OpenWorldProductAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Product Understanding"])

class ProductAnalyzeRequest(BaseModel):
    product_description: str = Field(..., description="Description of the product")

@router.post("/analyze", summary="Extract Structured Product Understanding")
async def analyze_product(payload: ProductAnalyzeRequest):
    """
    Extract open-world structured product attributes from arbitrary natural language:
    - Product identity and normalized name
    - Materials and components
    - Intended use and operational environment
    - Industry and regulatory domains
    - Ambiguity detection and clarification questions
    """
    try:
        analyzer = OpenWorldProductAnalyzer()
        understanding = await analyzer.analyze_product(payload.product_description)
        return {
            "success": True,
            "product_understanding": understanding.dict(),
            "clarification_required": understanding.clarification_required,
            "clarification_questions": understanding.clarification_questions
        }
    except Exception as e:
        logger.error(f"Product understanding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
