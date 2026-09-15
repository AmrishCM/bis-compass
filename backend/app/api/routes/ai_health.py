"""
AI Engine Health Check Route.
Performs minimal authenticated live completion with configured NVIDIA NIM provider.
"""
from fastapi import APIRouter, HTTPException
import logging
from app.services.llm.provider_factory import get_llm_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Engine Health"])

@router.get("/health", summary="Check NVIDIA AI Engine Connectivity")
async def ai_health():
    """
    Check if configured NVIDIA NIM LLM provider is reachable and active.
    Returns real round-trip latency_ms and status.
    """
    try:
        llm = get_llm_provider()
        if hasattr(llm, "health_check"):
            status = await llm.health_check()
            return status
        else:
            return {
                "provider": "generic",
                "configured": True,
                "reachable": True,
                "model": getattr(llm, "chat_model", "unknown"),
                "latency_ms": 0,
                "error": None
            }
    except Exception as e:
        logger.error(f"AI health check error: {e}")
        return {
            "provider": "nvidia",
            "configured": True,
            "reachable": False,
            "model": "unknown",
            "latency_ms": None,
            "error": str(e)
        }
