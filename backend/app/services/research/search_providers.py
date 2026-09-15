"""
Modular Search Provider Abstraction for Open-World Compliance Discovery.
Supports live DuckDuckGo Search (via ddgs), official portal scrapers, and external APIs.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Standardized search hit from any search provider"""
    title: str
    url: str
    snippet: str
    domain: str
    published_date: Optional[str] = None
    raw_score: float = 0.0

OFFICIAL_BIS_DOMAINS = [
    "bis.gov.in",
    "services.bis.gov.in",
    "standards.bis.gov.in",
    "lims.bis.gov.in",
    "standardsbis.bsbedge.com",
    "manakonline.in"
]

def is_official_source(url: str) -> bool:
    """Check if URL belongs to an authoritative BIS or Indian Government domain"""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if any(netloc == d or netloc.endswith("." + d) for d in OFFICIAL_BIS_DOMAINS):
            return True
        if netloc.endswith(".gov.in") or netloc.endswith(".nic.in"):
            return True
        return False
    except Exception:
        return False

class SearchProvider(ABC):
    """Abstract base class for search provider adapters"""

    @abstractmethod
    async def search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[SearchResult]:
        """Execute search query and return list of SearchResult objects"""
        pass

    def _extract_domain(self, url: str) -> str:
        """Extract clean lowercased domain from URL"""
        try:
            netloc = urlparse(url).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

class DDGSSearchProvider(SearchProvider):
    """
    Live web search provider using the `ddgs` library.
    Executes live search queries against current web sources without requiring paid API keys.
    """

    def __init__(self, timeout: int = 8):
        self.timeout = timeout

    async def search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[SearchResult]:
        return await asyncio.to_thread(self._sync_search, query, domains, max_results)

    def _sync_search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                logger.warning("ddgs library not installed; live search unavailable.")
                return []

        search_query = query
        if domains:
            if any("bis.gov.in" in d for d in domains):
                search_query = f"site:bis.gov.in {query}"
            elif len(domains) == 1:
                search_query = f"site:{domains[0]} {query}"
            else:
                search_query = f"site:{domains[0]} {query}"

        results: List[SearchResult] = []
        try:
            with DDGS(timeout=self.timeout) as ddgs:
                raw_hits = list(ddgs.text(search_query, max_results=max_results * 2))
                for hit in raw_hits:
                    url = hit.get("href") or hit.get("link") or hit.get("url", "")
                    if not url or not url.startswith("http"):
                        continue
                    domain = self._extract_domain(url)
                    if domains:
                        # Allow matching domain or subdomain
                        match = any(domain == d or domain.endswith("." + d) or d.endswith("." + domain) for d in domains)
                        if not match:
                            continue

                    results.append(SearchResult(
                        title=hit.get("title", url),
                        url=url,
                        snippet=hit.get("body") or hit.get("snippet", ""),
                        domain=domain,
                        published_date=hit.get("date")
                    ))
                    if len(results) >= max_results:
                        break

            logger.info(f"DDGS search '{query[:40]}' found {len(results)} authoritative candidates.")
            return results

        except Exception as e:
            logger.warning(f"DDGS live search exception for '{query[:40]}': {e}")
            # Resilient fallback: Retry simple query without site operator if site search failed
            if "site:" in search_query:
                try:
                    with DDGS(timeout=self.timeout) as ddgs:
                        raw_hits = list(ddgs.text(query, max_results=max_results))
                        for hit in raw_hits:
                            url = hit.get("href") or hit.get("link") or hit.get("url", "")
                            if not url or not url.startswith("http"):
                                continue
                            domain = self._extract_domain(url)
                            results.append(SearchResult(
                                title=hit.get("title", url),
                                url=url,
                                snippet=hit.get("body") or hit.get("snippet", ""),
                                domain=domain,
                                published_date=hit.get("date")
                            ))
                            if len(results) >= max_results:
                                break
                    return results
                except Exception:
                    pass
            return []

class OfficialBISSearchProvider(SearchProvider):
    """
    Direct targeted search provider targeting services.bis.gov.in and bis.gov.in portals.
    """

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.fallback = DDGSSearchProvider(timeout=timeout)

    async def search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[SearchResult]:
        # Target official BIS domain specifically
        bis_domains = ["bis.gov.in", "services.bis.gov.in"]
        return await self.fallback.search(f"{query} site:bis.gov.in", domains=bis_domains, max_results=max_results)

class ExternalAPISearchProvider(SearchProvider):
    """
    Adapter for external search APIs (Tavily, Brave, SerpAPI) when configured in .env.
    """

    def __init__(self, api_key: str, endpoint: str = "tavily"):
        self.api_key = api_key
        self.endpoint = endpoint.lower()

    async def search(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[SearchResult]:
        import httpx
        if "tavily" in self.endpoint:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    payload: Dict[str, Any] = {
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_domains": domains or []
                    }
                    resp = await client.post("https://api.tavily.com/search", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        return [
                            SearchResult(
                                title=r.get("title", ""),
                                url=r.get("url", ""),
                                snippet=r.get("content", ""),
                                domain=self._extract_domain(r.get("url", ""))
                            )
                            for r in data.get("results", [])
                        ]
            except Exception as e:
                logger.warning(f"External search API error: {e}")
        return []

def get_search_provider() -> SearchProvider:
    """Factory function returning the configured SearchProvider instance"""
    provider_type = os.getenv("WEB_SEARCH_PROVIDER", "ddgs").lower()
    api_key = os.getenv("WEB_SEARCH_API_KEY", "")

    if provider_type in ["tavily", "brave", "serp"] and api_key:
        logger.info(f"Using external search API provider: {provider_type}")
        return ExternalAPISearchProvider(api_key=api_key, endpoint=provider_type)

    logger.info("Using default live DDGS Search Provider.")
    return DDGSSearchProvider()
