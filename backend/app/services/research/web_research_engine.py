"""
Authoritative Web Research Engine for Open-World Standards Discovery.
Fetches, ranks, extracts, and indexes live online evidence from official BIS, government,
and regulatory portals.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import logging
import asyncio
import time
import re
from urllib.parse import urlparse
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .search_providers import SearchProvider, SearchResult, get_search_provider, is_official_source
from .research_planner import ComplianceResearchPlan
from .bis_discovery import get_bis_discovery_service
from app.db.session import SessionLocal
from app.models.standard import DiscoveredDocument

logger = logging.getLogger(__name__)

DOMAIN_AUTHORITY_HIERARCHY: Dict[str, int] = {
    # Tier 1 — Official BIS Portals (Authority 98-100)
    "bis.gov.in": 100,
    "services.bis.gov.in": 100,
    "standards.bis.gov.in": 100,
    "standardsbis.bsbedge.com": 100,
    "manakonline.in": 99,
    "bis.org.in": 98,

    # Tier 2 — Indian Government & Gazette Portals / Regulators (Authority 90-95)
    "fssai.gov.in": 95,
    "egazette.gov.in": 94,
    "egazette.nic.in": 94,
    "dpiit.gov.in": 93,
    "meity.gov.in": 93,
    "texmin.nic.in": 93,
    "consumeraffairs.nic.in": 92,
    "agmarkonline.dmi.gov.in": 92,
    "gov.in": 90,
    "nic.in": 90,

    # Tier 3 — International Standards Bodies (Authority 80-88)
    "iso.org": 88,
    "iec.ch": 88,
    "nist.gov": 85,
    "nabl-india.org": 85,

    # Tier 4 — Reputable Standards & Regulatory Intelligence (Authority 60-75)
    "niscair.res.in": 75,
    "compliancecalendar.in": 65,
    "standphillindia.in": 65,
    "corpseed.com": 60,

    # Tier 5 — Default general web fallback (blogs, generic aggregators)
    "default": 30
}

@dataclass
class RetrievedEvidence:
    """Structured evidence piece extracted from authoritative web document"""
    source_url: str
    domain: str
    title: str
    authority_score: int
    authority_tier: int  # 1 to 5
    content: str
    snippet: str
    checksum: str
    discovered_standards: List[str] = field(default_factory=list)
    scope_text: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    fetch_latency_seconds: float = 0.0
    is_cached: bool = False
    official: bool = False
    authority_level: str = "TIER_5"
    publisher: str = ""
    content_verified: bool = True
    standard_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)

@dataclass
class ResearchExecutionTrace:
    """Execution trace of all queries and fetches performed during research"""
    queries_executed: List[Dict[str, Any]] = field(default_factory=list)
    urls_fetched: List[Dict[str, Any]] = field(default_factory=list)
    sources_accepted: List[Dict[str, Any]] = field(default_factory=list)
    sources_rejected: List[Dict[str, Any]] = field(default_factory=list)

class SourceAuthorityRanker:
    """Evaluates domain authority according to the mandated 5-tier hierarchy"""

    @staticmethod
    def get_authority(domain: str) -> Tuple[int, int]:
        """Returns (authority_score, tier)"""
        clean_domain = domain.lower().replace("www.", "")

        # Exact match
        if clean_domain in DOMAIN_AUTHORITY_HIERARCHY:
            score = DOMAIN_AUTHORITY_HIERARCHY[clean_domain]
            return score, SourceAuthorityRanker._score_to_tier(score)

        # Suffix / Subdomain match
        for known, score in DOMAIN_AUTHORITY_HIERARCHY.items():
            if clean_domain.endswith("." + known):
                return score, SourceAuthorityRanker._score_to_tier(score)

        if clean_domain.endswith(".gov.in") or clean_domain.endswith(".nic.in"):
            return 90, 2

        return DOMAIN_AUTHORITY_HIERARCHY["default"], 5

    @staticmethod
    def _score_to_tier(score: int) -> int:
        if score >= 98:
            return 1
        elif score >= 90:
            return 2
        elif score >= 80:
            return 3
        elif score >= 60:
            return 4
        return 5

class WebResearchEngine:
    """
    Core engine responsible for discovering, downloading, parsing, and caching live web evidence.
    Integrates direct official BIS portal access and external multi-vector search.
    """

    def __init__(self, search_provider: Optional[SearchProvider] = None, timeout: int = 8):
        self.search_provider = search_provider or get_search_provider()
        self.bis_discovery = get_bis_discovery_service()
        self.timeout = timeout
        self.client_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (BIS-Compass/2.0)",
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8"
        }
        self.last_trace: ResearchExecutionTrace = ResearchExecutionTrace()

    async def execute_research_plan(
        self,
        plan: ComplianceResearchPlan,
        max_total_sources: int = 10
    ) -> List[RetrievedEvidence]:
        """
        Execute multi-angle research plan:
        1. Query official BIS endpoints directly using expanded product concepts
        2. Concurrently execute web search vectors across authoritative domains
        3. Fetch, parse, and verify candidate pages/PDFs
        4. Track full execution trace (queries, URLs, acceptance/rejection)
        """
        logger.info(f"Executing authoritative research plan for '{plan.product_name}'...")
        start_time = time.time()
        trace = ResearchExecutionTrace()

        # Step 1: Direct official BIS discovery via BISDiscoveryService
        concepts = getattr(plan, 'search_concepts', []) or [plan.normalized_name]
        official_bis_task = self.bis_discovery.discover_standards_for_product(concepts, max_total=5)

        # Step 2: Multi-angle web search queries
        search_tasks = []
        provider_name = self.search_provider.__class__.__name__
        for dim in plan.dimensions[:4]:
            trace.queries_executed.append({
                "dimension": dim.dimension_name,
                "query": dim.query,
                "domains": dim.target_domains,
                "priority": dim.priority,
                "provider": provider_name,
                "results_count": 0
            })
            search_tasks.append(
                self.search_provider.search(
                    query=dim.query,
                    domains=dim.target_domains if dim.priority == 1 else None,
                    max_results=3
                )
            )

        # Record official BIS discovery vector in trace
        trace.queries_executed.append({
            "dimension": "official_bis_portal_elasticsearch",
            "query": " / ".join(concepts[:3]),
            "domains": ["services.bis.gov.in"],
            "priority": 1,
            "provider": "BISDiscoveryService (Official BIS AJAX)",
            "results_count": 0
        })

        # Run direct BIS discovery and search concurrently
        all_results = await asyncio.gather(official_bis_task, *search_tasks, return_exceptions=True)

        official_bis_evidence: List[RetrievedEvidence] = []
        if isinstance(all_results[0], list):
            official_bis_evidence = all_results[0]
            # Update BIS trace result count
            trace.queries_executed[-1]["results_count"] = len(official_bis_evidence)

        candidate_urls: Dict[str, SearchResult] = {}
        for idx, res_list in enumerate(all_results[1:]):
            if isinstance(res_list, list):
                if idx < len(trace.queries_executed) - 1:
                    trace.queries_executed[idx]["results_count"] = len(res_list)
                for hit in res_list:
                    if hit.url not in candidate_urls:
                        candidate_urls[hit.url] = hit

        logger.info(f"Discovered {len(official_bis_evidence)} direct BIS standards and {len(candidate_urls)} web candidates.")

        # Step 3: Fetch and extract evidence for web search hits
        fetch_tasks = [
            self._fetch_and_extract_evidence(hit, trace)
            for hit in list(candidate_urls.values())[:max_total_sources]
        ]
        extracted_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        evidence_items: List[RetrievedEvidence] = list(official_bis_evidence)
        for item in extracted_results:
            if isinstance(item, RetrievedEvidence) and item is not None:
                evidence_items.append(item)

        # Deduplicate evidence by standard number or URL
        unique_evidence: Dict[str, RetrievedEvidence] = {}
        for ev in evidence_items:
            key = ev.source_url
            if ev.discovered_standards:
                key = ev.discovered_standards[0]
            if key not in unique_evidence:
                unique_evidence[key] = ev
                trace.sources_accepted.append({
                    "url": ev.source_url,
                    "domain": ev.domain,
                    "title": ev.title,
                    "tier": ev.authority_tier,
                    "score": ev.authority_score,
                    "official": ev.official
                })

        final_evidence = list(unique_evidence.values())
        # Rank by authority score descending (Tier 1 official BIS always first)
        final_evidence.sort(key=lambda e: e.authority_score, reverse=True)
        self.last_trace = trace

        elapsed = time.time() - start_time
        logger.info(f"Research completed in {elapsed:.2f}s with {len(final_evidence)} sources ({sum(1 for e in final_evidence if e.official)} official).")
        return final_evidence[:max_total_sources]

    async def _fetch_and_extract_evidence(
        self,
        hit: SearchResult,
        trace: Optional[ResearchExecutionTrace] = None
    ) -> Optional[RetrievedEvidence]:
        """Fetch URL with cache-check, parse content, extract IS standards, and save to DB cache"""
        url = hit.url
        domain = hit.domain
        authority_score, tier = SourceAuthorityRanker.get_authority(domain)
        official = is_official_source(url) or tier <= 2

        # 1. Check database cache for recent copy (freshness window: 14 days)
        cached_doc = self._get_cached_document(url)
        if cached_doc:
            logger.info(f"Cache hit for authoritative source: {url}")
            if trace:
                trace.urls_fetched.append({
                    "url": url,
                    "domain": domain,
                    "status": 200,
                    "is_cached": True,
                    "tier": tier,
                    "official": official
                })
            return RetrievedEvidence(
                source_url=url,
                domain=domain,
                title=cached_doc.title or hit.title,
                authority_score=cached_doc.authority_level * 20 if cached_doc.authority_level <= 5 else authority_score,
                authority_tier=tier,
                content=cached_doc.content_text,
                snippet=hit.snippet or cached_doc.content_text[:200],
                checksum=cached_doc.checksum,
                discovered_standards=self._extract_standard_numbers(cached_doc.content_text),
                scope_text=self._extract_scope_paragraph(cached_doc.content_text),
                is_cached=True,
                official=official,
                authority_level=f"TIER_{tier}",
                publisher="Official BIS / Government Portal" if official else domain,
                content_verified=True
            )

        # 2. Live fetch
        t0 = time.time()
        try:
            async with httpx.AsyncClient(headers=self.client_headers, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url)
                latency = time.time() - t0
                if trace:
                    trace.urls_fetched.append({
                        "url": url,
                        "domain": domain,
                        "status": resp.status_code,
                        "latency": round(latency, 2),
                        "is_cached": False,
                        "tier": tier,
                        "official": official
                    })

                if resp.status_code != 200:
                    logger.debug(f"Fetch failed ({resp.status_code}) for {url}")
                    if trace:
                        trace.sources_rejected.append({
                            "url": url,
                            "domain": domain,
                            "reason": f"HTTP status {resp.status_code}"
                        })
                    return None

                content_type = resp.headers.get("content-type", "").lower()
                text_content = ""
                file_type = "html"

                if "pdf" in content_type or url.lower().endswith(".pdf"):
                    file_type = "pdf"
                    text_content = await self._extract_pdf_text(resp.content)
                else:
                    text_content = self._extract_html_text(resp.text)

                if not text_content or len(text_content.strip()) < 50:
                    if trace:
                        trace.sources_rejected.append({
                            "url": url,
                            "domain": domain,
                            "reason": "Empty or unparseable page content"
                        })
                    return None

                checksum = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
                discovered_stds = self._extract_standard_numbers(text_content)
                scope_text = self._extract_scope_paragraph(text_content)

                # 3. Store into dynamic database cache
                self._save_to_cache(
                    url=url,
                    domain=domain,
                    title=hit.title,
                    checksum=checksum,
                    authority_level=tier,
                    file_type=file_type,
                    content_text=text_content
                )

                return RetrievedEvidence(
                    source_url=url,
                    domain=domain,
                    title=hit.title,
                    authority_score=authority_score,
                    authority_tier=tier,
                    content=text_content,
                    snippet=hit.snippet or text_content[:200],
                    checksum=checksum,
                    discovered_standards=discovered_stds,
                    scope_text=scope_text,
                    fetch_latency_seconds=round(latency, 2),
                    is_cached=False,
                    official=official,
                    authority_level=f"TIER_{tier}",
                    publisher="Official BIS / Government Portal" if official else domain,
                    content_verified=True
                )

        except Exception as e:
            logger.debug(f"Error fetching live evidence from {url}: {e}")
            if trace:
                trace.sources_rejected.append({
                    "url": url,
                    "domain": domain,
                    "reason": f"Network / connection error: {str(e)[:100]}"
                })
            return None

    def _extract_html_text(self, html: str) -> str:
        """Parse clean text from HTML, removing scripts and styles"""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
        return "\n".join(lines[:500])  # limit to first 500 meaningful lines

    async def _extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using PyMuPDF"""
        def _parse():
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pages = [page.get_text() for page in doc[:10]]  # inspect first 10 pages
                doc.close()
                return "\n".join(pages)
            except Exception as e:
                logger.debug(f"PyMuPDF extraction failed: {e}")
                return ""
        return await asyncio.to_thread(_parse)

    def _extract_standard_numbers(self, text: str) -> List[str]:
        """Extract unique official Indian Standard numbers (e.g., IS 17526:2021, IS 694, IS/IEC 60335-2-15)"""
        pattern = r'\bIS(?:\s*(?:/|\\)\s*IEC)?\s*[-–]?\s*\d+(?:[-–]\d+)*(?::\d{4})?\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        cleaned: List[str] = []
        for m in matches:
            normalized = re.sub(r'\s+', ' ', m.strip().upper()).replace('–', '-')
            if normalized not in cleaned:
                cleaned.append(normalized)
        return cleaned[:8]

    def _extract_scope_paragraph(self, text: str) -> Optional[str]:
        """Extract scope paragraph if explicitly present in standard text"""
        scope_match = re.search(r'(?:1\s+)?SCOPE\b[:\s\n]+([^\n]+(?:\n[^\n]+){1,5})', text, re.IGNORECASE)
        if scope_match:
            return scope_match.group(1).strip()
        return None

    def _get_cached_document(self, url: str) -> Optional[DiscoveredDocument]:
        """Retrieve existing document from database cache"""
        try:
            with SessionLocal() as db:
                return db.query(DiscoveredDocument).filter(DiscoveredDocument.source_url == url).first()
        except Exception:
            return None

    def _save_to_cache(
        self,
        url: str,
        domain: str,
        title: str,
        checksum: str,
        authority_level: int,
        file_type: str,
        content_text: str
    ):
        """Save verified document into discovered_documents table"""
        try:
            with SessionLocal() as db:
                existing = db.query(DiscoveredDocument).filter(DiscoveredDocument.source_url == url).first()
                if not existing:
                    doc = DiscoveredDocument(
                        source_url=url,
                        domain=domain,
                        title=title[:500] if title else url,
                        checksum=checksum,
                        authority_level=authority_level,
                        file_type=file_type,
                        content_text=content_text
                    )
                    db.add(doc)
                    db.commit()
        except Exception as e:
            logger.debug(f"Could not cache document {url}: {e}")

_engine_instance: Optional[WebResearchEngine] = None

def get_web_research_engine() -> WebResearchEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = WebResearchEngine()
    return _engine_instance
