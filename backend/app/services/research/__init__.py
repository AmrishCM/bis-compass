"""
Open-World Compliance Research Subsystem for BIS-Compass.
Provides dynamic search planning, authoritative web discovery, official document extraction,
and live evidence indexing.
"""
from .search_providers import SearchProvider, get_search_provider
from .research_planner import ComplianceResearchPlanner, get_research_planner
from .web_research_engine import WebResearchEngine, get_web_research_engine

__all__ = [
    "SearchProvider",
    "get_search_provider",
    "ComplianceResearchPlanner",
    "get_research_planner",
    "WebResearchEngine",
    "get_web_research_engine",
]
