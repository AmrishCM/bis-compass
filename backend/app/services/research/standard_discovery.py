"""
Dynamic Standard & Regulation Discovery Engine.
Extracts, structures, indexes, and evaluates applicability of Indian Standards from live web evidence.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import re

from .web_research_engine import RetrievedEvidence
from app.services.standards.applicability_service import get_standard_applicability_service, ApplicabilityDecision
from app.db.session import SessionLocal
from app.models.standard import Standard, Clause, Source

logger = logging.getLogger(__name__)

@dataclass
class DiscoveredStandardEntity:
    """Standard entity dynamically discovered from live online evidence"""
    standard_id: int
    standard_number: str
    title: str
    scope: str
    source_url: str
    authority_score: int
    authority_tier: int
    supporting_clauses: List[Dict[str, Any]] = field(default_factory=list)
    applicability_score: int = 0
    confidence: int = 0
    reasoning: List[str] = field(default_factory=list)
    is_qco_mandatory: bool = False
    evidence_snippet: str = ""
    status: str = "APPLICABLE"  # APPLICABLE, NEEDS_CLARIFICATION, RELATED, UNVERIFIED
    missing_information: List[str] = field(default_factory=list)
    confirmed_attributes: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)

@dataclass
class DiscoveryResult:
    """Outcome of standard discovery and open-world applicability evaluation"""
    applicable_standards: List[DiscoveredStandardEntity] = field(default_factory=list)
    potential_standards: List[DiscoveredStandardEntity] = field(default_factory=list)
    related_standards: List[Dict[str, Any]] = field(default_factory=list)
    rejected_candidates: List[Dict[str, Any]] = field(default_factory=list)
    all_discovered_numbers: List[str] = field(default_factory=list)
    safe_abstention: bool = False
    abstention_reason: str = ""
    sources_used: List[Dict[str, Any]] = field(default_factory=list)

class StandardDiscoveryEngine:
    """
    Evaluates live evidence to discover, index, and verify applicability of Indian Standards.
    Works with an empty database: populates the cache dynamically from verified web documents.
    """

    def __init__(self):
        self.applicability_service = get_standard_applicability_service()

    async def discover_and_evaluate_standards(
        self,
        product_understanding: Any,
        evidence_items: List[RetrievedEvidence]
    ) -> DiscoveryResult:
        """
        1. Extract all standard references from evidence
        2. Infer titles, scopes, and clauses
        3. Index new standards into database cache
        4. Run open-world applicability and false-positive suppression
        5. Return directly applicable, potentially relevant (needs clarification), and rejected candidates
        """
        p_name = getattr(product_understanding, "product_name", "") or "product"
        logger.info(f"Discovering standards for '{p_name}' from {len(evidence_items)} evidence documents...")

        result = DiscoveryResult()

        if not evidence_items:
            result.safe_abstention = True
            result.abstention_reason = (
                f"No authoritative online sources could be retrieved for '{p_name}'. "
                "Unable to verify applicable Indian Standards."
            )
            return result

        # Official sources counter (Tier 1 BIS + Tier 2 Gov/Regulatory)
        official_sources_count = sum(1 for e in evidence_items if getattr(e, 'official', False) or e.authority_tier <= 2)

        # Step 1: Collect standard candidates across evidence
        discovered_candidates: Dict[str, Dict[str, Any]] = {}

        for ev in evidence_items:
            result.sources_used.append({
                "url": ev.source_url,
                "domain": ev.domain,
                "title": ev.title,
                "authority_tier": ev.authority_tier,
                "authority_score": ev.authority_score,
                "is_cached": ev.is_cached,
                "official": getattr(ev, 'official', False) or ev.authority_tier <= 2
            })

            # Gate: Secondary / general web sources (Tier 4/5) cannot discover legal standards alone
            if ev.authority_tier > 3 and not getattr(ev, 'official', False):
                logger.info(f"Skipping standard discovery from non-official Tier {ev.authority_tier} source: {ev.source_url}")
                continue

            # Identify primary subject standards of this specific document
            doc_context = f"{getattr(ev, 'title', '')} {getattr(ev, 'source_url', '')}".lower()
            primary_stds_in_doc = set()
            for s in ev.discovered_standards:
                base_s = s.split(":")[0].strip().lower()
                clean_num = base_s.replace("is ", "").replace("is", "")
                if base_s in doc_context or clean_num in doc_context:
                    primary_stds_in_doc.add(s.split(":")[0].strip())

            for std_num in ev.discovered_standards:
                base_std = std_num.split(":")[0].strip()
                if std_num not in discovered_candidates:
                    meta_for_std = getattr(ev, 'standard_metadata', {}).get(std_num, {})
                    title = meta_for_std.get("title") or self._infer_standard_title(std_num, ev.content, getattr(ev, 'title', ''))
                    scope = meta_for_std.get("scope") or ev.scope_text or self._infer_standard_scope(std_num, ev.content, title)
                    qco_mandatory = "qco" in ev.content.lower() or "mandatory" in ev.content.lower() or "quality control order" in ev.content.lower()

                    # Section 27 & 28: Entity Resolution between primary standard vs referenced clause standards
                    rel_type = "PRIMARY_PRODUCT_STANDARD"
                    if primary_stds_in_doc and base_std not in primary_stds_in_doc:
                        rel_type = "REFERENCED_STANDARD"

                    # Check if standard is already in cache to enrich verified title
                    if not title:
                        try:
                            with SessionLocal() as db:
                                existing_std = db.query(Standard).filter(Standard.standard_number.like(f"{base_std}%")).first()
                                if existing_std and existing_std.title:
                                    title = existing_std.title
                        except Exception:
                            pass

                    discovered_candidates[std_num] = {
                        "standard_number": std_num,
                        "title": title,  # Strictly from evidence; NEVER synthetic
                        "scope": scope or "Scope text not explicitly extracted from source.",
                        "source_url": ev.source_url,
                        "authority_score": ev.authority_score,
                        "authority_tier": ev.authority_tier,
                        "relationship_type": rel_type,
                        "is_qco_mandatory": qco_mandatory,
                        "evidence_text": ev.content,
                        "evidence_snippet": ev.snippet,
                        "official": getattr(ev, 'official', False) or ev.authority_tier <= 2
                    }

        # Deduplicate unversioned standard if versioned equivalent exists (e.g. 'IS 17526' vs 'IS 17526:2021')
        versioned_stds = {s.split(":")[0].strip(): s for s in discovered_candidates.keys() if ":" in s}
        to_prune = [s for s in discovered_candidates.keys() if ":" not in s and s in versioned_stds]
        for s in to_prune:
            del discovered_candidates[s]

        result.all_discovered_numbers = list(discovered_candidates.keys())
        logger.info(f"Discovered {len(discovered_candidates)} candidate standards: {result.all_discovered_numbers}")

        if not discovered_candidates:
            result.safe_abstention = True
            result.abstention_reason = (
                f"Authoritative sources were investigated for '{p_name}', but no specific Indian Standard (IS) "
                "or Quality Control Order (QCO) numbers were cited in the retrieved evidence."
            )
            return result

        # Step 2: Dynamically index discovered standards into database cache
        indexed_ids = self._index_standards_in_db(discovered_candidates)

        # Step 3: Evaluate each candidate for true applicability (suppressing false positives)
        for std_num, cand in discovered_candidates.items():
            std_id = indexed_ids.get(std_num, 0)
            standard_dict = {
                "standard_id": std_id,
                "standard_number": std_num,
                "title": cand["title"],
                "scope": cand["scope"],
                "relationship_type": cand.get("relationship_type", "PRIMARY_PRODUCT_STANDARD")
            }

            clauses = self._extract_relevant_clauses(cand["evidence_text"])

            # Evaluate with applicability service
            decision: ApplicabilityDecision = self.applicability_service.evaluate_applicability(
                product=product_understanding,
                standard=standard_dict,
                retrieved_clauses=clauses
            )

            # Section 11 & 21 & 27: Evidence Gate & Entity Relationship Routing
            if cand.get("relationship_type") in ["REFERENCED_STANDARD", "MATERIAL_STANDARD", "TEST_METHOD_STANDARD", "COMPONENT_STANDARD"] or decision.decision == "RELATED" or getattr(decision, "relationship_type", "") in [
                "MATERIAL_STANDARD", "REFERENCED_STANDARD", "TEST_METHOD_STANDARD", "COMPONENT_STANDARD"
            ]:
                # Supporting referenced material/test/component standard (Section 27 & 28)
                result.related_standards.append({
                    "standard_id": std_id,
                    "standard_number": std_num,
                    "title": cand["title"] or f"Referenced standard cited in compliance evidence",
                    "relationship_type": cand.get("relationship_type", getattr(decision, "relationship_type", "REFERENCED_STANDARD")),
                    "reasons": decision.reasons or [f"Supporting referenced standard cited in primary compliance documentation."],
                    "source_url": cand["source_url"],
                    "authority_tier": cand["authority_tier"],
                    "evidence_snippet": cand["evidence_snippet"],
                    "score": int(decision.score) if decision.score > 0 else 50
                })

            elif decision.decision == "APPLICABLE":
                # Evidence Gate: Require at least 1 official BIS / Gov source for verified applicability
                if official_sources_count > 0:
                    entity = DiscoveredStandardEntity(
                        standard_id=std_id,
                        standard_number=std_num,
                        title=cand["title"],
                        scope=cand["scope"],
                        source_url=cand["source_url"],
                        authority_score=cand["authority_score"],
                        authority_tier=cand["authority_tier"],
                        supporting_clauses=clauses,
                        applicability_score=int(decision.score),
                        confidence=int(decision.score),
                        reasoning=decision.reasons,
                        is_qco_mandatory=cand["is_qco_mandatory"],
                        evidence_snippet=cand["evidence_snippet"],
                        status="APPLICABLE",
                        confirmed_attributes=decision.reasons
                    )
                    result.applicable_standards.append(entity)
                else:
                    # Downgrade to potential because no official source verified it
                    entity = DiscoveredStandardEntity(
                        standard_id=std_id,
                        standard_number=std_num,
                        title=cand["title"],
                        scope=cand["scope"],
                        source_url=cand["source_url"],
                        authority_score=cand["authority_score"],
                        authority_tier=cand["authority_tier"],
                        supporting_clauses=clauses,
                        applicability_score=int(decision.score * 0.7),
                        confidence=int(decision.score * 0.7),
                        reasoning=["Standard matches product scope in secondary sources; awaiting official BIS portal verification."],
                        is_qco_mandatory=cand["is_qco_mandatory"],
                        evidence_snippet=cand["evidence_snippet"],
                        status="NEEDS_CLARIFICATION",
                        missing_information=["Official Tier-1 BIS Gazette verification"],
                        clarification_questions=["Awaiting official BIS Gazette confirmation for full statutory applicability."]
                    )
                    result.potential_standards.append(entity)

            elif decision.decision == "NEEDS_CLARIFICATION":
                # Targeted grounded clarification questions (Bug 3 fix)
                questions = []
                c_title_lower = cand["title"].lower()
                c_scope_lower = (cand.get("scope") or "").lower()
                if "shirt" in c_title_lower or "t-shirt" in c_title_lower:
                    questions = [
                        "Is the garment of knitted construction or woven fabric?",
                        "Is it designed as a men's garment or another demographic category?",
                        "Is it intended as a sports shirt/T-shirt or casual general apparel?"
                    ]
                elif any(k in c_title_lower for k in ["flask", "bottle", "vessel", "drinkware", "container"]):
                    questions = [
                        f"{std_num} scope distinguishes single-wall from vacuum double-wall containers — which construction does your product use?",
                        f"{std_num} specifies domestic drinking storage — is your product intended for domestic consumer retail or industrial transport?",
                        f"Does the product volume fall within standard nominal capacity ratings?"
                    ]
                elif decision.missing_information:
                    questions = [f"Scope verification: {m}" for m in decision.missing_information]
                else:
                    questions = [f"{std_num} requires technical confirmation against its published scope: '{cand['title']}'"]

                entity = DiscoveredStandardEntity(
                    standard_id=std_id,
                    standard_number=std_num,
                    title=cand["title"],
                    scope=cand["scope"],
                    source_url=cand["source_url"],
                    authority_score=cand["authority_score"],
                    authority_tier=cand["authority_tier"],
                    supporting_clauses=clauses,
                    applicability_score=int(decision.score),
                    confidence=int(decision.score),
                    reasoning=decision.reasons or [f"Potentially relevant official standard: {cand['title']}"],
                    is_qco_mandatory=cand["is_qco_mandatory"],
                    evidence_snippet=cand["evidence_snippet"],
                    status="NEEDS_CLARIFICATION",
                    missing_information=decision.missing_information,
                    confirmed_attributes=decision.reasons,
                    clarification_questions=questions
                )
                result.potential_standards.append(entity)

            else:
                result.rejected_candidates.append({
                    "standard_id": std_id,
                    "standard_number": std_num,
                    "title": cand["title"],
                    "reason": " ".join(decision.contradictions) if decision.contradictions else "Out of product scope.",
                    "score": int(decision.score)
                })

        if not result.applicable_standards and not result.potential_standards:
            result.safe_abstention = True
            result.abstention_reason = (
                f"No directly applicable Indian Standard (IS) could be verified for '{p_name}' from the "
                f"authoritative sources investigated ({len(evidence_items)} sources checked, "
                f"{len(result.rejected_candidates)} candidate standards excluded based on scope boundaries)."
            )

        return result

    def _infer_standard_title(self, std_num: str, text: str, ev_title: str = "") -> str:
        """Extract title following or preceding standard number in text without inventing titles"""
        escaped = re.escape(std_num)
        base_num = std_num.split(":")[0].strip()

        def is_valid_title(t: str) -> bool:
            if not t or len(t) < 4:
                return False
            upper_t = t.upper().strip()
            if upper_t.startswith("IS ") or "BUREAU OF INDIAN STANDARDS" in upper_t:
                return False
            if upper_t in [
                "KNOW YOUR STANDARD", "PRODUCT MANUAL", "BIS", "INDIAN STANDARDS",
                "SPECIFICATION", "STANDARD", "SCOPE", "INTRODUCTION", "GENERAL"
            ]:
                return False
            return True

        # 1. Check official BIS evidence title ONLY if std_num or base number is in ev_title
        if ev_title and (std_num in ev_title or base_num in ev_title):
            m_pm = re.search(r'Product Manual for\s+([A-Za-z\s/]{4,100}?)(?:\s*\.{3}|\s*\(|\s*$)', ev_title, re.IGNORECASE)
            if m_pm and is_valid_title(m_pm.group(1).strip()):
                return re.sub(r'\s+', ' ', m_pm.group(1).strip())
            m = re.search(r'[-—–:]\s*([A-Za-z][^\n]{4,150}?)(?:\s*\((?:Official BIS|Current|Active).*)?$', ev_title, re.IGNORECASE)
            if m and is_valid_title(m.group(1).strip()):
                return re.sub(r'\s+', ' ', m.group(1).strip())

        # 2. Check explicit Title: label in text e.g. "Standard: IS 4375:2019\nTitle: Specification for..."
        m = re.search(rf'{escaped}[^\n]*\nTitle:\s*([A-Za-z][^\n]{{4,150}})', text, re.IGNORECASE)
        if m and is_valid_title(m.group(1).strip()):
            return re.sub(r'\s+', ' ', m.group(1).strip())

        # 3. Standard text patterns immediately associated with standard number
        patterns = [
            rf'PRODUCT MANUAL\s+FOR\s+([A-Za-z\s/]{{5,100}}?)\s+ACCORDING TO\s+{escaped}',
            rf'([A-Za-z\s/]{{5,100}}?)\s+ACCORDING TO\s+{escaped}',
            rf'{escaped}\s*[:–-]\s*([A-Za-z][^\n\.,;]{{5,100}})',
            rf'{escaped}\s*\(([^)]{{5,80}})\)',
            rf'{escaped}\s+(?:Specification|Requirements?|Standard)\s+(?:for|of)\s+([A-Za-z][^\n\.,;]{{5,100}})',
            rf'(?:Specification|Standard)\s+(?:for|of)\s+([A-Za-z][^\n\.,;]{{5,100}})\s*\(?{escaped}'
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match and is_valid_title(match.group(1).strip()):
                clean_title = re.sub(r'\s+', ' ', match.group(1).strip())
                return clean_title
        return ""

    def _infer_standard_scope(self, std_num: str, text: str, title: str) -> str:
        """Extract scope passage around the standard mention"""
        escaped = re.escape(std_num)
        pos = text.find(std_num)
        if pos != -1:
            snippet = text[max(0, pos - 100):min(len(text), pos + 300)].strip()
            return re.sub(r'\s+', ' ', snippet)
        return title or "Scope text not explicitly extracted from source."

    def _extract_relevant_clauses(self, text: str) -> List[Dict[str, Any]]:
        """Extract structured clauses from document text. Never invent fallback placeholders."""
        clauses: List[Dict[str, Any]] = []
        clause_matches = re.finditer(r'(?:Clause\s+|Section\s+)?(\b\d+\.\d+(?:\.\d+)?)\s+([A-Z][^\n]{3,60})\n([^\n]+(?:\n[^\n]+){1,3})', text)

        count = 0
        for m in clause_matches:
            clauses.append({
                "clause_number": m.group(1).strip(),
                "heading": m.group(2).strip(),
                "text": m.group(3).strip(),
                "relevance_score": 0.9
            })
            count += 1
            if count >= 4:
                break

        # If no explicit clauses found, return empty list (never fabricate generic placeholders)
        return clauses

    def _index_standards_in_db(self, candidates: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """Upsert discovered standards and clauses into the local evidence cache"""
        standard_ids: Dict[str, int] = {}
        try:
            with SessionLocal() as db:
                for std_num, cand in candidates.items():
                    existing = db.query(Standard).filter(Standard.standard_number == std_num).first()
                    if existing:
                        standard_ids[std_num] = existing.id
                    else:
                        new_std = Standard(
                            standard_number=std_num,
                            title=cand["title"],
                            scope=cand["scope"],
                            status="active",
                            source_id=cand.get("source_id") or 1,
                            source_url=cand.get("source_url"),
                            relationship_type=cand.get("relationship_type", "PRIMARY_PRODUCT_STANDARD"),
                            authority_tier=cand.get("authority_tier", 1)
                        )
                        db.add(new_std)
                        db.flush()
                        standard_ids[std_num] = new_std.id

                        # Add initial clause for retriever
                        initial_clause = Clause(
                            standard_id=new_std.id,
                            clause_number="1.0",
                            heading="Scope & Specification",
                            text=cand["scope"]
                        )
                        db.add(initial_clause)

                db.commit()
        except Exception as e:
            logger.warning(f"Notice indexing discovered standards: {e}")
        return standard_ids

_discovery_engine_instance: Optional[StandardDiscoveryEngine] = None

def get_standard_discovery_engine() -> StandardDiscoveryEngine:
    global _discovery_engine_instance
    if _discovery_engine_instance is None:
        _discovery_engine_instance = StandardDiscoveryEngine()
    return _discovery_engine_instance
