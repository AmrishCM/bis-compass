"""
API Routes Package
"""
from .analyze import router as analyze_router
from .products import router as products_router
from .standards import router as standards_router
from .compliance import router as compliance_router
from .laboratories import router as laboratories_router
from .documents import router as documents_router
from .web import router as web_router
from .sources import router as sources_router
from .evaluation import router as evaluation_router
from .stats import router as stats_router
from .chat import router as chat_router
from .audit import router as audit_router
from .ai_health import router as ai_health_router
from .research_health import router as research_health_router
from .translate import router as translate_router
from .consumer import router as consumer_router
from .updates import router as updates_router
from .voice import router as voice_router

__all__ = [
    "analyze_router",
    "products_router",
    "standards_router",
    "compliance_router",
    "laboratories_router",
    "documents_router",
    "web_router",
    "sources_router",
    "evaluation_router",
    "stats_router",
    "chat_router",
    "audit_router",
    "ai_health_router",
    "research_health_router",
    "translate_router",
    "consumer_router",
    "updates_router",
    "voice_router",
]
