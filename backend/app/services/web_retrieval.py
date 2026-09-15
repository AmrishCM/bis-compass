"""
Web retrieval service with domain authority ranking.
Fetches information from the web and ranks results based on domain authority.
"""

import logging
import re
import asyncio
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Domain authority scores (higher is more authoritative)
DOMAIN_AUTHORITY_SCORES = {
    # Government domains
    "gov.in": 95,
    "nic.in": 90,
    "org.in": 85,
    # Educational
    "edu.in": 80,
    "ac.in": 80,
    # Known authoritative sites for standards
    "bis.org.in": 100,
    "nbc.org.in": 95,
    "nist.gov": 95,
    "iso.org": 90,
    "iec.ch": 90,
    # News and reliable sources
    "bbc.com": 85,
    "reuters.com": 85,
    # Fallback
    "default": 10,
}

@dataclass
class WebSearchResult:
    """Result from a web search with authority ranking."""
    url: str
    title: str
    snippet: str
    domain: str
    authority_score: int
    relevance_score: float = 0.0
    combined_score: float = 0.0
    fetch_time: float = 0.0
    status_code: Optional[int] = None
    error: Optional[str] = None

class WebRetrievalService:
    """Service for retrieving information from the web with authority ranking."""

    def __init__(self, timeout: int = 5, user_agent: str = "BIS-Compass/1.0"):
        self.timeout = timeout
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www.
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _get_authority_score(self, domain: str) -> int:
        """Get authority score for a domain."""
        # Exact match
        if domain in DOMAIN_AUTHORITY_SCORES:
            return DOMAIN_AUTHORITY_SCORES[domain]
        # Check for subdomains (e.g., www.bis.org.in -> bis.org.in)
        # Actually we already stripped www, but check for other subdomains.
        # We'll try to match by suffix.
        for known_domain, score in DOMAIN_AUTHORITY_SCORES.items():
            if domain.endswith("." + known_domain):
                return score
        return DOMAIN_AUTHORITY_SCORES["default"]

    def _fetch_page(self, url: str) -> tuple[Optional[str], int, Optional[str]]:
        """Fetch a single page and return (text, status_code, error)."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            status_code = response.status_code
            if status_code == 200:
                # Parse HTML and extract text
                soup = BeautifulSoup(response.content, "html.parser")
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator=" ", strip=True)
                # Limit length
                if len(text) > 10000:
                    text = text[:10000] + "..."
                return text, status_code, None
            else:
                return None, status_code, f"HTTP {status_code}"
        except requests.exceptions.Timeout:
            return None, 408, "Timeout"
        except requests.exceptions.RequestException as e:
            return None, 0, str(e)
        except Exception as e:
            return None, 0, f"Unexpected error: {e}"

    def _extract_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Extract a snippet from text relevant to the query."""
        if not text:
            return ""
        # Simple approach: find first occurrence of query terms
        query_terms = query.lower().split()
        text_lower = text.lower()
        best_pos = 0
        best_count = 0
        # Sliding window to find dense query term matches
        words = re.findall(r'\b\w+\b', text_lower)
        if not words:
            return text[:max_length]
        # For simplicity, just return first max_length chars
        snippet = text[:max_length]
        # Try to improve by looking for query terms
        for term in query_terms:
            pos = text_lower.find(term)
            if pos != -1:
                start = max(0, pos - 100)
                end = min(len(text), pos + len(term) + 100)
                snippet = text[start:end]
                break
        return snippet.strip()

    async def search(
        self,
        query: str,
        max_results: int = 10,
        domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[WebSearchResult]:
        """
        Perform an asynchronous web search and return ranked results.
        Fetches candidate authoritative URLs concurrently.
        """
        logger.info(f"Performing web search for query: '{query}'")

        candidate_urls = self._generate_candidate_urls(query, domains, exclude_domains)
        target_urls = candidate_urls[:max_results * 2]

        async def fetch_single(url: str) -> Optional[WebSearchResult]:
            try:
                start_time = time.time()
                text, status_code, error = await asyncio.to_thread(self._fetch_page, url)
                fetch_time = time.time() - start_time

                domain = self._get_domain(url)
                authority_score = self._get_authority_score(domain)

                if text is not None and error is None:
                    snippet = self._extract_snippet(text, query)
                    relevance_score = self._calculate_relevance(text, query)
                    combined_score = (authority_score * 0.4) + (relevance_score * 100 * 0.6)
                    return WebSearchResult(
                        url=url,
                        title=self._extract_title(text) or url,
                        snippet=snippet,
                        domain=domain,
                        authority_score=authority_score,
                        relevance_score=relevance_score,
                        combined_score=combined_score,
                        fetch_time=fetch_time,
                        status_code=status_code,
                    )
            except Exception as ex:
                logger.debug(f"Failed to fetch {url}: {ex}")
            return None

        # Fetch in parallel with timeout safeguard
        try:
            tasks = [fetch_single(url) for url in target_urls]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            results = [r for r in raw_results if isinstance(r, WebSearchResult) and r is not None]
        except Exception as e:
            logger.warning(f"Concurrent web search error: {e}")
            results = []

        # Sort by combined score descending
        results.sort(key=lambda x: x.combined_score, reverse=True)
        results = results[:max_results]
        logger.info(f"Web search returned {len(results)} results")
        return results

    def search_sync(
        self,
        query: str,
        max_results: int = 10,
        domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[WebSearchResult]:
        """Synchronous wrapper for search."""
        try:
            return asyncio.run(self.search(query, max_results, domains, exclude_domains))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.search(query, max_results, domains, exclude_domains))

    def _generate_candidate_urls(
        self,
        query: str,
        domains: Optional[List[str]],
        exclude_domains: Optional[List[str]],
    ) -> List[str]:
        """Generate candidate URLs to fetch based on query and domain restrictions."""
        # This is a placeholder. In a real implementation, you would:
        # 1. Use a search API to get URLs
        # 2. Or maintain a crawl/index of known authoritative sites
        # For now, we return a few known authoritative sites if they match the query.

        known_sites = [
            "https://www.bis.org.in",
            "https://www.niscair.res.in",
            "https://www.iitk.ac.in",
            "https://www.iisc.ac.in",
            "https://www.dst.gov.in",
            "https://www.dbib.gov.in",
            "https://www.daemi.gov.in",
            "https://www.indiastat.com",
            "https://www.statista.com",
            "https://www.wto.org",
            "https://www.iso.org",
            "https://www.iec.ch",
        ]

        # Filter by domains if specified
        if domains:
            allowed = set(domains)
            filtered = []
            for url in known_sites:
                domain = self._get_domain(url)
                if any(domain.endswith("." + d) or domain == d for d in allowed):
                    filtered.append(url)
            known_sites = filtered

        # Exclude domains
        if exclude_domains:
            excluded = set(exclude_domains)
            filtered = []
            for url in known_sites:
                domain = self._get_domain(url)
                if not any(domain.endswith("." + d) or domain == d for d in excluded):
                    filtered.append(url)
            known_sites = filtered

        # If no known sites match, return a generic list (maybe from a search API)
        if not known_sites:
            # Fallback to a few generic sites
            known_sites = [
                "https://www.google.com/search?q=" + requests.utils.quote(query),
                "https://www.bing.com/search?q=" + requests.utils.quote(query),
                "https://duckduckgo.com/?q=" + requests.utils.quote(query),
            ]

        return known_sites

    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from HTML text."""
        # Look for <title> tag
        title_match = re.search(r'<title>([^<]+)</title>', text, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        # Otherwise, first line that looks like a title
        lines = text.split('\n')
        for line in lines[:5]:
            if line.strip() and len(line.strip()) < 100:
                return line.strip()
        return None

    def _calculate_relevance(self, text: str, query: str) -> float:
        """Calculate a simple relevance score based on query term frequency."""
        if not text or not query:
            return 0.0
        text_lower = text.lower()
        query_terms = query.lower().split()
        if not query_terms:
            return 0.0
        total_score = 0
        for term in query_terms:
            # Count occurrences
            count = text_lower.count(term)
            total_score += count
        # Normalize by text length (avoid bias towards longer texts)
        # Use a simple normalization: score per 1000 characters
        if len(text) == 0:
            return 0.0
        score_per_char = total_score / len(text)
        # Scale to a reasonable range (0-10)
        relevance = min(score_per_char * 1000, 10.0)
        return relevance

# Convenience function
def get_web_retrieval_service() -> WebRetrievalService:
    """Get or create a web retrieval service instance."""
    # In a more complex system, you might want to reuse a session.
    return WebRetrievalService()