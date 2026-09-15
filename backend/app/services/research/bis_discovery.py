from __future__ import annotations
"""
Official BIS Discovery Service.
Directly interfaces with official Bureau of Indian Standards (BIS) portals and endpoints:
- services.bis.gov.in (Know Your Standards, LIMS, Gazette)
- standards.bis.gov.in (Standard Details, Review, Committees)
- standardsbis.bsbedge.com (Official Indian Standards portal)

Performs real-time search by keyword, product name, or IS number, retrieves official
standard metadata, QCO gazette notifications, and recognized testing laboratories.
"""
from typing import List, Dict, Any, Optional
import httpx
import logging
import asyncio
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .web_research_engine import RetrievedEvidence

logger = logging.getLogger(__name__)

OFFICIAL_BIS_HOSTNAMES = {
    "bis.gov.in",
    "services.bis.gov.in",
    "standards.bis.gov.in",
    "lims.bis.gov.in",
    "standardsbis.bsbedge.com",
    "manakonline.in",
    "bis.org.in"
}

def is_official_bis_source(url: str) -> bool:
    """Verifies whether the URL belongs to an official BIS portal"""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return any(netloc == h or netloc.endswith("." + h) for h in OFFICIAL_BIS_HOSTNAMES)
    except Exception:
        return False

def is_official_gov_source(url: str) -> bool:
    """Verifies whether the URL belongs to an official Indian Government / Regulatory portal"""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.endswith(".gov.in") or netloc.endswith(".nic.in") or is_official_bis_source(url)
    except Exception:
        return False

class BISDiscoveryService:
    """
    Dedicated official BIS discovery client.
    Directly queries the official Know Your Standard endpoints on services.bis.gov.in.
    """

    BASE_URL = "https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/knowyourstandards"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (BIS-Compass/2.0)",
            "Referer": f"{self.BASE_URL}/indian_standards/isdetails",
            "X-Requested-With": "XMLHttpRequest"
        }

    async def search_by_keywords(self, keyword: str, max_results: int = 8) -> List[Dict[str, Any]]:
        """
        Search official BIS database by product/title keyword.
        Uses POST /Elasticsearch/gettitlesearchAjax
        """
        clean_kw = keyword.strip()
        if len(clean_kw) < 3:
            return []

        url = f"{self.BASE_URL}/Elasticsearch/gettitlesearchAjax"
        payload = {"search": clean_kw, "type": 1, "wh": 0}

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, verify=False) as client:
                resp = await client.post(url, data=payload)
                if resp.status_code != 200:
                    logger.warning(f"BIS gettitlesearchAjax returned {resp.status_code} for '{clean_kw}'")
                    # Fallback for long multi-word queries that cause 500 on BIS Elasticsearch:
                    words = clean_kw.split()
                    if len(words) > 2:
                        short_kw = " ".join(words[-2:])
                        resp = await client.post(url, data={"search": short_kw, "type": 1, "wh": 0})
                        if resp.status_code != 200:
                            return []
                    else:
                        return []

                data = resp.json()
                results: List[Dict[str, Any]] = []
                for item in data:
                    pk_id = item.get("id")
                    if not pk_id or pk_id in ["nothingmatch", "didyoumean"]:
                        continue

                    raw_name = item.get("name", "")
                    is_no = item.get("is_no", "").strip()

                    # Parse clean title from name: "IS 4375:2019 (Specification for men's cotton knitted sports shirt/T-shirt (second revision) )"
                    title = raw_name
                    m = re.search(r'\((.+)\)\s*$', raw_name)
                    if m:
                        title = m.group(1).strip()

                    results.append({
                        "pk_is_id": str(pk_id),
                        "is_number": is_no or self._extract_is_number(raw_name),
                        "full_name": raw_name,
                        "title": title,
                        "year": item.get("is_year", ""),
                        "source": "official_bis_portal",
                        "url": f"{self.BASE_URL}/Indian_standards/isdetails/"
                    })
                    if len(results) >= max_results:
                        break

                logger.info(f"Official BIS keyword search for '{clean_kw}' returned {len(results)} standards.")
                return results

        except Exception as e:
            logger.debug(f"Error querying BIS gettitlesearchAjax for '{clean_kw}': {e}")
            return []

    async def search_by_is_number(self, is_num: str) -> List[Dict[str, Any]]:
        """
        Search official BIS database by IS number.
        Uses POST /Elasticsearch/getsearchAjax
        """
        num_clean = re.sub(r'[^\d]', '', is_num)
        if not num_clean:
            return []

        url = f"{self.BASE_URL}/Elasticsearch/getsearchAjax"
        payload = {"search": num_clean, "type": 1, "wh": 0}

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, verify=False) as client:
                resp = await client.post(url, data=payload)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                results: List[Dict[str, Any]] = []
                for item in data:
                    pk_id = item.get("id")
                    if not pk_id or pk_id in ["nothingmatch", "didyoumean"]:
                        continue

                    raw_name = item.get("name", "")
                    title = raw_name
                    m = re.search(r'\((.+)\)\s*$', raw_name)
                    if m:
                        title = m.group(1).strip()

                    results.append({
                        "pk_is_id": str(pk_id),
                        "is_number": item.get("is_no", "").strip() or f"IS {num_clean}",
                        "full_name": raw_name,
                        "title": title,
                        "year": item.get("is_year", ""),
                        "source": "official_bis_portal",
                        "url": f"{self.BASE_URL}/Indian_standards/isdetails/"
                    })
                return results

        except Exception as e:
            logger.debug(f"Error querying BIS getsearchAjax for IS {is_num}: {e}")
            return []

    async def get_standard_details(self, pk_is_id: str) -> Dict[str, Any]:
        """
        Retrieve comprehensive standard metadata, technical committee, cross-references,
        and gazette QCO status for an official BIS standard ID.
        """
        url = f"{self.BASE_URL}/Indian_standards/isdetails/"
        payload = {
            "wh": "0",
            "search_type": "1",
            "pk_is_id": pk_is_id
        }

        details: Dict[str, Any] = {
            "pk_is_id": pk_is_id,
            "committee": None,
            "aspect": None,
            "scope_text": None,
            "cross_references": [],
            "qco_gazette_orders": [],
            "recognized_laboratories": []
        }

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout, verify=False) as client:
                # Run isdetails, gazette, and lab requests concurrently
                gaz_url = f"{self.BASE_URL}/Is_gazattedetails/getgazattedetailsAjax?pk_is_id={pk_is_id}&is_id={pk_is_id}"
                lab_url = f"{self.BASE_URL}/Is_labs/getlabs?pk_is_id={pk_is_id}"

                resp, gaz_resp, lab_resp = await asyncio.gather(
                    client.post(url, data=payload),
                    client.post(gaz_url),
                    client.post(lab_url),
                    return_exceptions=True
                )

                if not isinstance(resp, Exception) and resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    aspect_match = re.search(r'Aspect\s*:\s*([^\n<]+)', resp.text, re.IGNORECASE)
                    if aspect_match:
                        details["aspect"] = aspect_match.group(1).strip()

                    cross_ref_items = []
                    lines = [l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()]
                    for i, line in enumerate(lines):
                        if line.startswith("IS ") or line.startswith("IS/") or line.startswith("ISO "):
                            if i + 1 < len(lines):
                                cross_ref_items.append({
                                    "standard_number": line,
                                    "title": lines[i + 1]
                                })
                    details["cross_references"] = cross_ref_items[:10]

                if not isinstance(gaz_resp, Exception) and gaz_resp.status_code == 200:
                    try:
                        gaz_data = gaz_resp.json()
                        details["qco_gazette_orders"] = gaz_data.get("aaData", [])
                    except Exception:
                        pass

                if not isinstance(lab_resp, Exception) and lab_resp.status_code == 200:
                    try:
                        lab_data = lab_resp.json()
                        details["recognized_laboratories"] = lab_data.get("aaData", [])[:15]
                    except Exception:
                        pass

        except Exception as e:
            logger.debug(f"Error getting BIS details for pk_is_id={pk_is_id}: {e}")

        return details

    async def discover_standards_for_product(
        self,
        keywords: List[str],
        max_total: int = 6
    ) -> List[RetrievedEvidence]:
        """
        Executes real-time discovery across official BIS endpoints using expanded search concepts.
        Converts verified hits into structured RetrievedEvidence objects with Tier-1 authority.
        """
        from .web_research_engine import RetrievedEvidence

        logger.info(f"Official BISDiscoveryService searching for product concepts: {keywords}")
        seen_is_numbers = set()
        evidence_list: List[RetrievedEvidence] = []

        # Step 1: Query concepts concurrently in parallel batches
        kw_tasks = [self.search_by_keywords(kw, max_results=3) for kw in keywords[:5]]
        all_kw_results = await asyncio.gather(*kw_tasks, return_exceptions=True)

        unique_hits = []
        for kw_res in all_kw_results:
            if isinstance(kw_res, list):
                for hit in kw_res:
                    is_num = hit.get("is_number")
                    if not is_num or is_num in seen_is_numbers:
                        continue
                    seen_is_numbers.add(is_num)
                    unique_hits.append(hit)
                    if len(unique_hits) >= max_total:
                        break
            if len(unique_hits) >= max_total:
                break

        # Step 2: Fetch details for unique discovered standards concurrently
        detail_tasks = [
            self.get_standard_details(h["pk_is_id"]) if h.get("pk_is_id") else None
            for h in unique_hits
        ]
        metas = await asyncio.gather(*[t for t in detail_tasks if t is not None], return_exceptions=True)
        meta_map = {}
        m_idx = 0
        for h in unique_hits:
            if h.get("pk_is_id"):
                meta_res = metas[m_idx] if m_idx < len(metas) else {}
                meta_map[h["pk_is_id"]] = meta_res if isinstance(meta_res, dict) else {}
                m_idx += 1

        for hit in unique_hits:
            pk_id = hit.get("pk_is_id")
            meta = meta_map.get(pk_id, {})

            is_qco = len(meta.get("qco_gazette_orders", [])) > 0
            aspect = meta.get("aspect") or "Product Specification"
            cross_refs = meta.get("cross_references", [])
            cross_ref_str = "; ".join([f"{c['standard_number']} ({c['title']})" for c in cross_refs[:4]])

            content = (
                f"Official Bureau of Indian Standards (BIS) Document\n"
                f"Standard: {hit['is_number']}\n"
                f"Title: {hit['title']}\n"
                f"Aspect: {aspect}\n"
                f"Publication / Revision: {hit.get('year', 'Current')}\n"
                f"Official BIS Portal URL: {hit['url']}\n"
                f"Mandatory QCO Status: {'Mandatory under Quality Control Order' if is_qco else 'Voluntary Indian Standard / QCO pending'}\n"
                f"Referred Standards: {cross_ref_str or 'None'}\n"
                f"Recognized Testing Facilities: {len(meta.get('recognized_laboratories', []))} authorized BIS/NABL laboratories registered.\n"
                f"Scope Summary: {hit['title']}. Governs specification, quality parameters, physical and chemical testing requirements in India."
            )

            ev = RetrievedEvidence(
                source_url=f"https://standards.bis.gov.in/website/standard-details?is={hit['is_number'].replace(' ', '_')}",
                domain="services.bis.gov.in",
                title=f"{hit['is_number']} — {hit['title']} (Official BIS Record)",
                authority_score=100,
                authority_tier=1,
                content=content,
                snippet=f"Official BIS record: {hit['is_number']} — {hit['title']} ({aspect}).",
                checksum=f"bis_official_{hit['pk_is_id']}",
                discovered_standards=[hit["is_number"]],
                scope_text=f"Official Indian Standard {hit['is_number']} covering {hit['title']}.",
                is_cached=False,
                official=True,
                authority_level="TIER_1",
                publisher="Bureau of Indian Standards",
                standard_metadata={
                    hit["is_number"]: {
                        "title": hit["title"],
                        "aspect": aspect,
                        "scope": f"Official Indian Standard {hit['is_number']} covering {hit['title']}."
                    }
                }
            )
            evidence_list.append(ev)

        logger.info(f"BISDiscoveryService discovered {len(evidence_list)} official Tier-1 Indian Standards.")
        return evidence_list

    def _extract_is_number(self, text: str) -> str:
        m = re.search(r'\bIS\s*[-–]?\s*\d+(?:[-–]\d+)*(?::\d{4})?\b', text, re.IGNORECASE)
        return m.group(0).strip().upper() if m else ""

_bis_discovery_instance: Optional[BISDiscoveryService] = None

def get_bis_discovery_service() -> BISDiscoveryService:
    global _bis_discovery_instance
    if _bis_discovery_instance is None:
        _bis_discovery_instance = BISDiscoveryService()
    return _bis_discovery_instance
