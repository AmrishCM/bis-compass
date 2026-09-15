from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
from app.services.products.product_understanding import ProductUnderstanding
from app.services.standards.applicability_service import get_standard_applicability_service
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever
from app.core.config import get_settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

@dataclass
class StandardMatch:
    """Represents a matched standard with applicability scoring"""
    standard_id: int
    standard_number: str
    title: str
    applicability_score: int  # 0-100
    confidence: int  # 0-100
    reasoning: List[str]
    supporting_clauses: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    status: str = "APPLICABLE"
    confirmed_attributes: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)

class StandardsMatchingEngine:
    """
    Open-World Standards Matching Engine.
    Fuses hybrid search candidates with StandardApplicabilityService to ensure
    only genuinely applicable standards survive and false positives are strictly rejected.
    """

    def __init__(self):
        self.settings = get_settings()
        self.applicability_service = get_standard_applicability_service()
        self.last_rejected_candidates: List[Dict[str, Any]] = []

    async def find_applicable_standards(
        self,
        product_understanding: ProductUnderstanding,
        limit: int = 10
    ) -> List[StandardMatch]:
        """Backward-compatible method returning surviving applicable standards"""
        applicable, rejected = await self.find_applicable_standards_with_rejections(
            product_understanding, limit=limit
        )
        return applicable

    async def find_applicable_standards_with_rejections(
        self,
        product_understanding: ProductUnderstanding,
        limit: int = 10
    ) -> Tuple[List[StandardMatch], List[Dict[str, Any]]]:
        """
        Open-world matching workflow:
        1. Dynamic query expansion
        2. Candidate retrieval (hybrid search)
        3. Scope & contradiction verification (StandardApplicabilityService)
        4. Hard rejection of false positives
        5. Ranking of verified applicable standards
        """
        try:
            logger.info(f"Evaluating applicable standards for: '{product_understanding.product_name}'")
            self.last_rejected_candidates = []

            # If clarification is required due to vague input, do not guess
            if product_understanding.clarification_required:
                logger.info("Product understanding marked clarification_required; abstaining from premature matching.")
                return [], []

            # Step 1: Generate dynamic search representations
            search_queries = self._generate_search_queries(product_understanding)
            logger.info(f"Generated search queries: {search_queries}")

            # Step 2: Retrieve candidate standards
            all_results = []
            for query in search_queries:
                db = next(get_db())
                try:
                    retriever = get_hybrid_retriever(db)
                    results = await retriever.hybrid_search(
                        query=query,
                        limit=limit * 3,
                        min_confidence=0.05
                    )
                    all_results.extend(results)
                finally:
                    db.close()

            unique_results = self._deduplicate_results(all_results)
            logger.info(f"Retrieved {len(unique_results)} candidate standards before applicability verification.")

            # Step 3: Evaluate every candidate with open-world applicability engine
            applicable_matches: List[StandardMatch] = []
            rejected_candidates: List[Dict[str, Any]] = []

            for result in unique_results:
                standard_data = {
                    "standard_id": result.get("standard_id"),
                    "standard_number": result.get("standard_number", ""),
                    "title": result.get("standard_title", ""),
                    "scope": result.get("scope", "")
                }

                clauses = self._extract_supporting_clauses(result, product_understanding)
                decision = self.applicability_service.evaluate_applicability(
                    product=product_understanding,
                    standard=standard_data,
                    retrieved_clauses=clauses
                )

                if decision.decision == "APPLICABLE":
                    # Build StandardMatch with verified reasons
                    match = StandardMatch(
                        standard_id=result.get("standard_id"),
                        standard_number=result.get("standard_number", ""),
                        title=result.get("standard_title", ""),
                        applicability_score=int(round(decision.score)),
                        confidence=int(round(max(60.0, decision.score * 0.95))),
                        reasoning=decision.reasons if decision.reasons else ["Scope and product identity align."],
                        supporting_clauses=decision.supporting_evidence if decision.supporting_evidence else clauses[:3],
                        metadata={
                            "search_scores": {
                                "lexical": result.get("lexical_score", 0.0),
                                "semantic": result.get("semantic_score", 0.0),
                                "combined": result.get("combined_score", 0.0)
                            },
                            "decision": decision.decision,
                            "authority_level": result.get("authority_level", 1)
                        }
                    )
                    applicable_matches.append(match)
                else:
                    # Record explicit rejection with reason
                    rejection_reason = decision.contradictions[0] if decision.contradictions else "Product does not fall under this standard's mandatory scope."
                    rejected_candidates.append({
                        "standard_id": result.get("standard_id"),
                        "standard_number": result.get("standard_number", "Unknown"),
                        "title": result.get("standard_title", ""),
                        "reason": rejection_reason,
                        "score": decision.score
                    })

            # Sort applicable matches by score descending
            applicable_matches.sort(key=lambda x: x.applicability_score, reverse=True)
            self.last_rejected_candidates = rejected_candidates

            logger.info(f"Applicability check: {len(applicable_matches)} APPLICABLE, {len(rejected_candidates)} REJECTED.")
            return applicable_matches[:limit], rejected_candidates

        except Exception as e:
            logger.error(f"Error in standards matching engine: {e}", exc_info=True)
            return [], []

    def _generate_search_queries(self, product: ProductUnderstanding) -> List[str]:
        """Generate targeted search queries from product understanding"""
        queries = []

        # 1. Use pre-expanded search terms
        if product.search_terms:
            queries.extend(product.search_terms)

        # 2. Product name + intended use
        if product.product_name:
            queries.append(f"{product.product_name} {product.intended_use}".strip())

        # 3. Product family + materials
        if product.product_family and product.materials:
            queries.append(f"{product.product_family} {product.materials[0]}".strip())

        # 4. Canonical name alone
        if product.normalized_product_name:
            queries.append(product.normalized_product_name)

        seen = set()
        unique_queries = []
        for q in queries:
            q_clean = q.lower().strip()
            if q_clean and q_clean not in seen:
                seen.add(q_clean)
                unique_queries.append(q_clean)

        return unique_queries[:5]

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate search results by standard_id"""
        seen_standards = set()
        unique_results = []

        for result in results:
            standard_id = result.get("standard_id")
            if standard_id and standard_id not in seen_standards:
                seen_standards.add(standard_id)
                unique_results.append(result)

        return unique_results

    def _extract_supporting_clauses(
        self,
        search_result: Dict[str, Any],
        product_understanding: ProductUnderstanding
    ) -> List[Dict[str, Any]]:
        """Extract supporting clauses from search result"""
        clauses = []
        clause_results = search_result.get("clause_results", [])

        if clause_results:
            for clause in clause_results:
                clauses.append({
                    "clause_number": clause.get("clause_number", "General"),
                    "heading": clause.get("heading", "Requirement"),
                    "text": clause.get("text", "")[:300] + ("..." if len(clause.get("text", "")) > 300 else ""),
                    "page": clause.get("page", 1),
                    "relevance_score": clause.get("score", 0.0)
                })
        elif search_result.get("text"):
            clauses.append({
                "clause_number": search_result.get("clause_number", "Scope"),
                "heading": "Standard Scope",
                "text": search_result.get("text", "")[:300],
                "page": search_result.get("page", 1),
                "relevance_score": search_result.get("combined_score", 0.0)
            })

        return clauses


# Global instance
_standards_matching_engine: Optional[StandardsMatchingEngine] = None

def get_standards_matching_engine() -> StandardsMatchingEngine:
    """Get or create standards matching engine instance"""
    global _standards_matching_engine
    if _standards_matching_engine is None:
        _standards_matching_engine = StandardsMatchingEngine()
    return _standards_matching_engine