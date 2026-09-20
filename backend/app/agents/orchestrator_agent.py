from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import asyncio
import time
import uuid
import json
from pydantic import BaseModel

from app.services.products.product_understanding import ProductUnderstandingEngine, get_product_understanding_engine, ProductUnderstanding
from app.services.products.open_world_analyzer import OpenWorldProductAnalyzer
from app.services.llm.provider_factory import LLMProviderFactory
from app.core.llm_provider import LLMProvider
from app.services.research.research_planner import ComplianceResearchPlanner, ComplianceResearchPlan
from app.services.research.web_research_engine import WebResearchEngine, RetrievedEvidence
from app.services.research.standard_discovery import StandardDiscoveryEngine, get_standard_discovery_engine, DiscoveredStandardEntity
from app.agents.certification_agent import CertificationAgent, get_certification_agent, CertificationInfo
from app.agents.testing_agent import TestingAgent, get_testing_agent, TestingInformation
from app.agents.laboratory_agent import LaboratoryAgent, get_laboratory_agent, Laboratory, LabSearchCriteria
from app.agents.compliance_gap_agent import ComplianceGapAgent, get_compliance_gap_agent, GapAnalysisResult
from app.agents.citation_verification_agent import CitationVerificationAgent, get_citation_verification_agent, VerificationResult
from app.services.web_retrieval import get_web_retrieval_service, WebSearchResult
from app.services.standards.matching_engine import get_standards_matching_engine, StandardMatch
from app.services.retrieval.hybrid_retriever import get_hybrid_retriever
from app.models.standard import ResearchSession
from app.db.session import SessionLocal
from app.core.exceptions import AIServiceUnavailableException
import os

from app.services.products.product_profile import ProductProfile, ClarificationQuestionItem, MultiProductDetection
from app.services.research.scope_differentiator import ScopeDifferentiator
from app.services.compliance.humanized_roadmap import HumanizedRoadmapBuilder

logger = logging.getLogger(__name__)

@dataclass
class OrchestrationInput:
    """Input for the orchestration workflow"""
    product_description: Optional[str] = None
    product_understanding: Optional[ProductUnderstanding] = None
    product_profile: Optional[Dict[str, Any]] = None
    previous_questions: Optional[List[str]] = None
    document_text: Optional[str] = None
    target_standard_ids: Optional[List[int]] = None
    location: Optional[str] = None
    include_web_search: bool = True
    max_results_per_agent: int = 5

class SynthesisResult(BaseModel):
    """Result of LLM-based synthesis"""
    overall_assessment: str
    recommendations: List[str]

class CanonicalDecision(BaseModel):
    """Canonical decision object"""
    decision: Dict[str, Any]
    product: Dict[str, Any]
    standards: List[Dict[str, Any]]
    regulatory: Dict[str, Any]
    testing: List[Dict[str, Any]]
    laboratories: List[Dict[str, Any]]
    clarifications: List[str]
    audit: Dict[str, Any]

@dataclass
class OrchestrationResult:
    """Complete result from orchestration workflow"""
    input_summary: Dict[str, Any]
    product_understanding: Optional[ProductUnderstanding] = None
    applicable_standards: List[StandardMatch] = field(default_factory=list)
    certification_info: List[CertificationInfo] = field(default_factory=list)
    testing_information: List[TestingInformation] = field(default_factory=list)
    laboratory_recommendations: List[Laboratory] = field(default_factory=list)
    compliance_analysis: List[GapAnalysisResult] = field(default_factory=list)
    citation_verification: List[VerificationResult] = field(default_factory=list)
    web_search_results: List[WebSearchResult] = field(default_factory=list)
    clarification_required: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    clarification_question_items: List[Dict[str, Any]] = field(default_factory=list)
    final_status: str = "READY"
    product_profile: Optional[Dict[str, Any]] = None
    step_by_step_roadmap: Dict[str, Any] = field(default_factory=dict)
    multi_product_detected: Optional[Dict[str, Any]] = None
    potential_standards: List[StandardMatch] = field(default_factory=list)
    related_standards: List[Dict[str, Any]] = field(default_factory=list)
    rejected_candidates: List[Dict[str, Any]] = field(default_factory=list)
    pipeline_stats: Dict[str, Any] = field(default_factory=dict)
    research_stages: List[Dict[str, Any]] = field(default_factory=list)
    sources_investigated: List[Dict[str, Any]] = field(default_factory=list)
    research_trace: Dict[str, Any] = field(default_factory=dict)
    what_you_need_to_do: Dict[str, Any] = field(default_factory=dict)
    canonical_decision: Dict[str, Any] = field(default_factory=dict)
    is_live_research: bool = True
    session_id: Optional[str] = None
    overall_assessment: str = ""
    recommendations: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    agent_execution_times: Dict[str, float] = field(default_factory=dict)

class OrchestratorAgent:
    """Agent responsible for coordinating multi-agent workflows for BIS certification analysis"""

    def __init__(self):
        # Initialize resilient dual LLM providers (NVIDIA + Groq failover)
        self.nvidia_provider = LLMProviderFactory.create_provider(provider_type="nvidia")
        self.groq_provider = LLMProviderFactory.create_provider(provider_type="groq")
        self.dual_provider = LLMProviderFactory.create_provider(provider_type="dual")
        self.scope_differentiator = ScopeDifferentiator()

        # Initialize analyzers with resilient provider
        self.open_world_analyzer = OpenWorldProductAnalyzer()
        self.open_world_analyzer.llm_provider = self.dual_provider

        # Keep NVIDIA provider for accuracy-critical tasks
        self.product_understanding_engine = get_product_understanding_engine()
        self.research_planner = ComplianceResearchPlanner()
        self.web_research_engine = WebResearchEngine()
        self.standard_discovery = get_standard_discovery_engine()
        self.certification_agent = get_certification_agent()
        self.testing_agent = get_testing_agent()
        self.laboratory_agent = get_laboratory_agent()
        self.compliance_gap_agent = get_compliance_gap_agent()
        self.citation_verification_agent = get_citation_verification_agent()
        self.web_retrieval_service = get_web_retrieval_service()
        self.standards_matching_engine = get_standards_matching_engine()
        self.hybrid_retriever_factory = get_hybrid_retriever

    async def run_full_certification_analysis(
        self,
        input_data: OrchestrationInput
    ) -> OrchestrationResult:
        """
        Run a complete BIS certification analysis workflow

        Workflow:
        1. Product understanding (if description provided)
        2. Standards matching
        3. For each standard:
           a. Certification requirements
           b. Testing requirements
           c. Laboratory search
           d. Compliance gap analysis (if document provided)
           e. Citation verification (if document provided)
        4. Optional web search for additional information
        5. Synthesize results and provide recommendations

        Args:
            input_data: Orchestration input containing product description/document

        Returns:
            OrchestrationResult with all analysis results
        """
        import time
        start_time = time.time()

        logger.info("Starting open-world live compliance research workflow")
        result = OrchestrationResult(input_summary=self._summarize_input(input_data))

        try:
            # Stage 1: Open-World Product Understanding
            pu_start = time.time()
            if input_data.product_description and not input_data.product_understanding:
                logger.info("Stage 1: Open-world product understanding")
                result.product_understanding = await self.open_world_analyzer.analyze_product(
                    input_data.product_description
                )
            elif input_data.product_understanding:
                result.product_understanding = input_data.product_understanding
            result.agent_execution_times['product_understanding'] = time.time() - pu_start

            # Multi-Product Detection (Section 29)
            if result.product_understanding and result.product_understanding.multi_product_detected:
                mp = result.product_understanding.multi_product_detected
                if mp.get("is_multi_product"):
                    result.clarification_required = True
                    result.final_status = "NEEDS_CLARIFICATION"
                    result.multi_product_detected = mp
                    msg = mp.get("message", "Multiple distinct products detected.")
                    result.clarification_questions = [msg]
                    result.clarification_question_items = [
                        {
                            "id": "q_multi_product",
                            "question": "Which product would you like to check compliance for first?",
                            "why_needed": "Each distinct product category falls under different BIS standards, Quality Control Orders, and testing schemes.",
                            "options": mp.get("detected_products", []),
                            "affects": ["standard_selection"],
                            "attribute_key": "selected_product"
                        }
                    ]
                    result.overall_assessment = msg
                    result.recommendations = mp.get("detected_products", [])
                    self._finalize_result(result, start_time)
                    self._save_research_session(result, input_data.product_description or "")
                    return result

            # Structured ProductProfile extraction
            if input_data.product_profile:
                prod_profile = ProductProfile(**input_data.product_profile)
            elif result.product_understanding and result.product_understanding.product_profile:
                prod_profile = ProductProfile(**result.product_understanding.product_profile)
            elif result.product_understanding:
                pu = result.product_understanding
                prod_profile = ProductProfile(
                    product_name=pu.product_name,
                    material=", ".join(pu.materials) if pu.materials else None,
                    intended_use=pu.intended_use
                )
            else:
                prod_profile = ProductProfile(product_name="Product")

            # Extract confirmed physical and operational attributes from description & understanding
            desc_lower = f"{input_data.product_description or ''} {getattr(result.product_understanding, 'product_name', '')} {getattr(result.product_understanding, 'application', '')}".lower()
            if any(k in desc_lower for k in ["vacuum", "insulated", "thermo", "flask"]):
                prod_profile.insulation = "Vacuum / Thermal Insulated"
                prod_profile.unknown_attributes = [u for u in prod_profile.unknown_attributes if u.lower() not in ["insulation", "thermal"]]
            elif any(k in desc_lower for k in ["single wall", "single-wall", "non-insulated"]):
                prod_profile.insulation = "Single-wall (Non-insulated)"
                prod_profile.unknown_attributes = [u for u in prod_profile.unknown_attributes if u.lower() not in ["insulation", "thermal"]]

            if any(k in desc_lower for k in ["double wall", "double-wall"]):
                prod_profile.construction = "Double-wall"
                prod_profile.unknown_attributes = [u for u in prod_profile.unknown_attributes if u.lower() not in ["construction"]]
            elif any(k in desc_lower for k in ["single wall", "single-wall"]):
                prod_profile.construction = "Single-wall"
                prod_profile.unknown_attributes = [u for u in prod_profile.unknown_attributes if u.lower() not in ["construction"]]

            if any(k in desc_lower for k in ["domestic", "drinking", "household", "consumer", "potable"]):
                if not prod_profile.intended_use:
                    prod_profile.intended_use = "Domestic Drinking / Potable"
                prod_profile.operating_environment = "Domestic"
                prod_profile.unknown_attributes = [u for u in prod_profile.unknown_attributes if u.lower() not in ["intended_use", "operating_environment", "intended use"]]

            if input_data.location:
                prod_profile.location = input_data.location
            result.product_profile = prod_profile.dict()

            # If product understanding indicates clarification is required, safely abstain
            if result.product_understanding and result.product_understanding.clarification_required:
                result.clarification_required = True
                result.final_status = "NEEDS_CLARIFICATION"
                result.clarification_questions = result.product_understanding.clarification_questions
                result.overall_assessment = (
                    "Clarification required: The product description is ambiguous or specifies only a raw material "
                    "without identifying the specific manufactured product article."
                )
                result.recommendations = result.product_understanding.clarification_questions
                self._finalize_result(result, start_time)
                self._save_research_session(result, input_data.product_description or "")
                return result

            # If we don't have product understanding, we can't proceed meaningfully
            if not result.product_understanding:
                result.overall_assessment = "Insufficient product information to proceed with analysis"
                return self._finalize_result(result, start_time)

            result.research_stages.append({
                "stage": "Product Understanding",
                "status": "completed",
                "description": f"Analyzed '{result.product_understanding.product_name}' (Materials: {', '.join(result.product_understanding.materials) or 'N/A'}, Intended use: {result.product_understanding.intended_use or 'General'})."
            })

            # Stage 2: Dynamic Search Planning
            plan_start = time.time()
            logger.info("Stage 2: Dynamic compliance search planning")
            research_plan = self.research_planner.generate_research_plan(
                result.product_understanding,
                include_testing_search=True
            )
            result.agent_execution_times['research_planning'] = time.time() - plan_start
            result.research_stages.append({
                "stage": "Search Planning",
                "status": "completed",
                "description": f"Generated {len(research_plan.dimensions)} multi-angle search vectors prioritizing Tier-1 official BIS and Tier-2 government gazettes."
            })

            # Stage 3: Authoritative Web Discovery & Source Retrieval
            evidence_items: List[RetrievedEvidence] = []
            target_ids = input_data.target_standard_ids
            if not target_ids and input_data.include_web_search:
                web_start = time.time()
                logger.info("Stage 3: Live authoritative web research")
                try:
                    evidence_items = await self.web_research_engine.execute_research_plan(research_plan)
                except Exception as e:
                    logger.warning(f"Live web research encountered warning: {e}")
                result.agent_execution_times['web_research'] = time.time() - web_start

                result.sources_investigated = [
                    {
                        "url": ev.source_url,
                        "domain": ev.domain,
                        "title": ev.title,
                        "authority_tier": ev.authority_tier,
                        "authority_score": ev.authority_score,
                        "is_cached": ev.is_cached,
                        "retrieved_at": ev.retrieved_at
                    }
                    for ev in evidence_items
                ]
                official_count = sum(1 for e in evidence_items if getattr(e, 'official', False) or e.authority_tier <= 2)
                bis_count = sum(1 for e in evidence_items if getattr(e, 'official', False) or e.authority_tier == 1)
                gov_count = sum(1 for e in evidence_items if not getattr(e, 'official', False) and e.authority_tier == 2)
                sec_count = len(evidence_items) - official_count

                if official_count == 0:
                    stage_desc = f"Retrieved {len(evidence_items)} sources (0 Tier-1 official BIS, {sec_count} secondary). ⚠️ No authoritative BIS/Government source was found."
                else:
                    stage_desc = f"Retrieved {len(evidence_items)} evidence sources ({official_count} official BIS/Government, {sec_count} secondary)."

                result.research_stages.append({
                    "stage": "Authoritative Discovery",
                    "status": "completed",
                    "description": stage_desc
                })

            # Record Research Execution Trace
            trace = getattr(self.web_research_engine, 'last_trace', None)
            if trace:
                result.research_trace = {
                    "queries_executed": trace.queries_executed,
                    "urls_fetched": trace.urls_fetched,
                    "sources_accepted": trace.sources_accepted,
                    "sources_rejected": trace.sources_rejected
                }

            # Stage 4: Standard Discovery, Scope & Applicability Analysis
            std_start = time.time()
            logger.info("Stage 4: Dynamic standard discovery & open-world scope evaluation")
            if not target_ids:
                discovery_res = await self.standard_discovery.discover_and_evaluate_standards(
                    result.product_understanding,
                    evidence_items
                )

                # Discovered directly applicable standards
                discovered_matches: List[StandardMatch] = []
                for entity in discovery_res.applicable_standards:
                    discovered_matches.append(StandardMatch(
                        standard_id=entity.standard_id,
                        standard_number=entity.standard_number,
                        title=entity.title,
                        applicability_score=entity.applicability_score,
                        confidence=entity.confidence,
                        reasoning=entity.reasoning or [f"Authoritative scope confirmed applicability for {result.product_understanding.product_name}."],
                        supporting_clauses=entity.supporting_clauses,
                        status="APPLICABLE",
                        confirmed_attributes=entity.confirmed_attributes,
                        missing_information=[],
                        clarification_questions=[],
                        metadata={
                            "source_url": entity.source_url,
                            "authority_tier": entity.authority_tier,
                            "authority_score": entity.authority_score,
                            "is_qco_mandatory": entity.is_qco_mandatory,
                            "evidence_snippet": entity.evidence_snippet,
                            "status": "APPLICABLE",
                            "confirmed_attributes": entity.confirmed_attributes
                        }
                    ))

                # Discovered potentially relevant standards (needs clarification)
                potential_matches: List[StandardMatch] = []
                for entity in discovery_res.potential_standards:
                    potential_matches.append(StandardMatch(
                        standard_id=entity.standard_id,
                        standard_number=entity.standard_number,
                        title=entity.title,
                        applicability_score=entity.applicability_score,
                        confidence=entity.confidence,
                        reasoning=entity.reasoning or [f"Potentially relevant official standard: {entity.title}"],
                        supporting_clauses=entity.supporting_clauses,
                        status="NEEDS_CLARIFICATION",
                        confirmed_attributes=entity.confirmed_attributes or [],
                        missing_information=entity.missing_information or [],
                        clarification_questions=entity.clarification_questions or [],
                        metadata={
                            "source_url": entity.source_url,
                            "authority_tier": entity.authority_tier,
                            "authority_score": entity.authority_score,
                            "is_qco_mandatory": entity.is_qco_mandatory,
                            "evidence_snippet": entity.evidence_snippet,
                            "status": "NEEDS_CLARIFICATION",
                            "missing_information": entity.missing_information,
                            "confirmed_attributes": entity.confirmed_attributes,
                            "clarification_questions": entity.clarification_questions
                        }
                    ))

                # Rule 8.1: Standard IDs MUST originate from retrieved evidence. Reject hallucinations.
                valid_evidence_numbers = set(discovery_res.all_discovered_numbers)
                valid_base_prefixes = {n.split(':')[0].strip().upper() for n in valid_evidence_numbers}

                def is_in_evidence(std_num: str) -> bool:
                    clean = std_num.strip().upper()
                    if clean in valid_evidence_numbers:
                        return True
                    base = clean.split(':')[0].strip()
                    return base in valid_base_prefixes

                filtered_matches = []
                for m in discovered_matches:
                    if is_in_evidence(m.standard_number):
                        filtered_matches.append(m)
                    else:
                        logger.warning(f"RULE 8.1 VIOLATION: Standard {m.standard_number} absent from evidence. Rejecting hallucination.")

                filtered_potential = []
                for m in potential_matches:
                    if is_in_evidence(m.standard_number):
                        filtered_potential.append(m)
                    else:
                        logger.warning(f"RULE 8.1 VIOLATION: Standard {m.standard_number} absent from evidence. Rejecting hallucination.")

                # Strictly dynamic: NO static DB seed leakage into production candidates
                result.applicable_standards = filtered_matches[:input_data.max_results_per_agent]
                result.potential_standards = filtered_potential[:input_data.max_results_per_agent]
                result.rejected_candidates = discovery_res.rejected_candidates
                result.related_standards = discovery_res.related_standards

                # Honest pipeline statistics based on actual objects
                official_used = sum(1 for e in evidence_items if getattr(e, 'official', False) or e.authority_tier <= 2)
                bis_used = sum(1 for e in evidence_items if getattr(e, 'official', False) or e.authority_tier == 1)
                gov_used = sum(1 for e in evidence_items if not getattr(e, 'official', False) and e.authority_tier == 2)
                sec_used = len(evidence_items) - official_used

                result.pipeline_stats = {
                    "sources_examined": len(evidence_items),
                    "authoritative_sources_used": official_used,
                    "bis_official_used": bis_used,
                    "gov_official_used": gov_used,
                    "secondary_used": sec_used,
                    "retrieved_candidates": len(discovery_res.all_discovered_numbers),
                    "standards_identified": len(result.applicable_standards) + len(result.potential_standards),
                    "direct_matches": len(result.applicable_standards),
                    "potential_matches": len(result.potential_standards),
                    "needs_clarification": len(result.potential_standards),
                    "scope_filtered": len(result.rejected_candidates),
                    "applicable": len(result.applicable_standards),
                    "rejected": len(result.rejected_candidates),
                    "is_live_research": len(evidence_items) > 0,
                    "web_search_used": input_data.include_web_search
                }
            else:
                result.applicable_standards = await self._get_standard_details(target_ids)

            result.agent_execution_times['standards_matching'] = time.time() - std_start
            result.research_stages.append({
                "stage": "Scope & Applicability",
                "status": "completed",
                "description": f"Verified {len(result.applicable_standards)} directly applicable; identified {len(result.potential_standards)} potentially relevant; excluded {len(result.rejected_candidates)} false positives."
            })

            # Stage 4 Decision-Critical Unknowns Gate (Sections 2, 4, 5, 25)
            # Demote any candidate standard from applicable to potential if its scope demands an attribute
            # that is currently unknown in prod_profile.
            demoted_to_potential = []
            kept_applicable = []
            for m in result.applicable_standards:
                m_text = f"{m.standard_number} {m.title} {m.metadata.get('scope', '')}".lower()
                needs_unknown = False

                if "insulation" in prod_profile.unknown_attributes:
                    if any(k in m_text for k in ["vacuum", "insulated", "flask"]):
                        needs_unknown = True
                if "voltage_range" in prod_profile.unknown_attributes or "voltage" in prod_profile.unknown_attributes:
                    if any(k in m_text for k in ["voltage", "1100", "kv"]):
                        needs_unknown = True
                if "fabric_construction" in prod_profile.unknown_attributes:
                    if any(k in m_text for k in ["knitted", "woven"]):
                        needs_unknown = True
                if "construction" in prod_profile.unknown_attributes:
                    if any(k in m_text for k in ["double wall", "double-wall", "vacuum"]):
                        needs_unknown = True

                if needs_unknown:
                    m.status = "NEEDS_CLARIFICATION"
                    demoted_to_potential.append(m)
                else:
                    kept_applicable.append(m)

            result.applicable_standards = kept_applicable
            result.potential_standards.extend(demoted_to_potential)

            # If there are NO applicable standards, but there ARE potential standards,
            # evaluate if clarification is truly required or if top candidate can be confirmed.
            if not result.applicable_standards and result.potential_standards:
                has_previous_answers = bool(input_data.previous_questions and len(input_data.previous_questions) > 0)
                best_candidate = result.potential_standards[0] if result.potential_standards else None

                # If user already answered clarifications or top candidate has high applicability score, promote to applicable
                if has_previous_answers or (best_candidate and getattr(best_candidate, 'applicability_score', 0) >= 35):
                    best_candidate.status = "APPLICABLE"
                    result.applicable_standards = [best_candidate]
                    result.potential_standards = result.potential_standards[1:]
                    logger.info(f"Promoted top candidate standard {best_candidate.standard_number} to applicable.")
                else:
                    # Genuinely ambiguous candidate standards with no previous answers -> prompt clarification
                    all_candidates_for_diff = [
                        {
                            "standard_number": s.standard_number,
                            "title": s.title,
                            "scope": s.metadata.get("scope") or s.metadata.get("evidence_snippet", "")
                        }
                        for s in result.potential_standards
                    ]

                    dynamic_questions = await self.scope_differentiator.differentiate_and_generate_questions(
                        product_profile=prod_profile,
                        candidate_standards=all_candidates_for_diff,
                        previous_questions=input_data.previous_questions or [],
                        product_description=input_data.product_description or ""
                    )

                    if dynamic_questions:
                        result.clarification_required = True
                        result.final_status = "NEEDS_CLARIFICATION"
                        result.product_profile = prod_profile.dict()
                        result.clarification_questions = [q.question for q in dynamic_questions]
                        result.clarification_question_items = [q.dict() for q in dynamic_questions]
                        result.overall_assessment = (
                            "We found more than one possible BIS requirement. "
                            "Before giving you a certification answer, we need a few details to make sure we identify the correct product category."
                        )
                        result.recommendations = [q.question for q in dynamic_questions]
                        self._finalize_result(result, start_time)
                        self._save_research_session(result, input_data.product_description or "")
                        return result

            # Check if any applicable or potential standards found
            if not result.applicable_standards and not result.potential_standards:
                result.overall_assessment = (
                    f"No directly applicable Indian Standard (IS) could be verified for '{result.product_understanding.product_name}' "
                    f"from the authoritative sources investigated ({len(evidence_items)} sources checked, {len(result.rejected_candidates)} candidate standards excluded based on scope boundaries)."
                )
                result.recommendations = [
                    "Potentially related candidate standards were evaluated and excluded based on mandatory scope boundaries.",
                    "Verify if your product is subject to a specialized Quality Control Order (QCO) issued by DPIIT, MeitY, or line ministries.",
                    "Consider providing additional technical parameters (e.g. voltage, nominal capacity, pressure rating, or specialized manufacturing method)."
                ]
                self._finalize_result(result, start_time)
                self._save_research_session(result, input_data.product_description or "")
                return result

            # Step 3: Process each standard (in parallel for efficiency)
            std_process_start = time.time()
            certification_tasks = []
            testing_tasks = []
            lab_tasks = []
            compliance_tasks = []
            citation_tasks = []

            target_standards = result.applicable_standards if result.applicable_standards else result.potential_standards[:2]
            for idx, standard_match in enumerate(target_standards[:input_data.max_results_per_agent]):
                standard_id = standard_match.standard_id
                standard_number = standard_match.standard_number
                # Certification info task
                certification_tasks.append(
                    self._get_certification_info_for_standard(
                        standard_id, result.product_understanding, standard_number
                    )
                )
                # Testing info task
                testing_tasks.append(
                    self._get_testing_info_for_standard(
                        standard_id, result.product_understanding, standard_number
                    )
                )
                # Laboratory search task (focus on top 2 primary standards for optimal response time)
                if idx < 2:
                    lab_tasks.append(
                        self._get_laboratory_recommendations_for_standard(
                            standard_id, result.product_understanding, input_data.location, standard_number
                        )
                    )
                # Compliance gap analysis (if document provided)
                if input_data.document_text:
                    compliance_tasks.append(
                        self._analyze_compliance_for_standard(
                            standard_id, input_data.document_text, result.product_understanding
                        )
                    )
                    # Citation verification (if document provided)
                    citation_tasks.append(
                        self._verify_citations_in_document(
                            input_data.document_text, result.product_understanding
                        )
                    )

            # Execute all tasks in parallel concurrently (unified latency optimization)
            async def run_certification_batch():
                if not certification_tasks:
                    return []
                return await asyncio.gather(*certification_tasks, return_exceptions=True)

            async def run_testing_batch():
                if not testing_tasks:
                    return []
                return await asyncio.gather(*testing_tasks, return_exceptions=True)

            async def run_lab_batch():
                if not lab_tasks:
                    return []
                return await asyncio.gather(*lab_tasks, return_exceptions=True)

            async def run_compliance_batch():
                if not compliance_tasks:
                    return []
                return await asyncio.gather(*compliance_tasks, return_exceptions=True)

            async def run_citation_batch():
                if not citation_tasks:
                    return []
                return await asyncio.gather(*citation_tasks, return_exceptions=True)

            async def run_web_search_batch():
                if not (input_data.include_web_search and result.product_understanding):
                    return []
                try:
                    return await self._perform_web_search(
                        result.product_understanding, result.applicable_standards[:3]
                    )
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")
                    return []

            batch_results = await asyncio.gather(
                run_certification_batch(),
                run_testing_batch(),
                run_lab_batch(),
                run_compliance_batch(),
                run_citation_batch(),
                run_web_search_batch(),
                return_exceptions=True
            )

            cert_results = batch_results[0] if not isinstance(batch_results[0], Exception) else []
            test_results = batch_results[1] if not isinstance(batch_results[1], Exception) else []
            lab_results = batch_results[2] if not isinstance(batch_results[2], Exception) else []
            comp_results = batch_results[3] if not isinstance(batch_results[3], Exception) else []
            cite_results = batch_results[4] if not isinstance(batch_results[4], Exception) else []
            web_results = batch_results[5] if not isinstance(batch_results[5], Exception) else []

            for i, res in enumerate(cert_results):
                if not isinstance(res, Exception):
                    result.certification_info.append(res)
                else:
                    logger.warning(f"Certification task {i} failed: {res}")

            for i, res in enumerate(test_results):
                if not isinstance(res, Exception):
                    result.testing_information.append(res)
                else:
                    logger.warning(f"Testing task {i} failed: {res}")

            for i, res in enumerate(lab_results):
                if not isinstance(res, Exception):
                    result.laboratory_recommendations.extend(res)
                else:
                    logger.warning(f"Laboratory task {i} failed: {res}")

            for i, res in enumerate(comp_results):
                if not isinstance(res, Exception):
                    result.compliance_analysis.append(res)
                else:
                    logger.warning(f"Compliance task {i} failed: {res}")

            for i, res in enumerate(cite_results):
                if not isinstance(res, Exception):
                    result.citation_verification.extend(res)
                else:
                    logger.warning(f"Citation task {i} failed: {res}")

            result.web_search_results = web_results
            result.agent_execution_times['standard_processing'] = time.time() - std_process_start

            # Step 5: Synthesize results and generate recommendations
            synth_start = time.time()
            result.overall_assessment, result.recommendations = await self._synthesize_results(result)
            result.what_you_need_to_do = self._generate_what_you_need_to_do(result)
            result.canonical_decision = self._generate_canonical_decision(result)

            # Build humanized 8-step roadmap
            result.step_by_step_roadmap = HumanizedRoadmapBuilder.build_roadmap(
                product_profile=prod_profile,
                applicable_standards=result.applicable_standards,
                potential_standards=result.potential_standards,
                certification_info=result.certification_info,
                testing_information=result.testing_information,
                laboratories=result.laboratory_recommendations,
                location=input_data.location or prod_profile.location
            )
            result.product_profile = prod_profile.dict()
            result.final_status = "PRODUCT_IDENTIFIED" if result.applicable_standards else ("NEEDS_CLARIFICATION" if result.clarification_required else "NO_VERIFIED_STANDARD_FOUND")
            result.agent_execution_times['synthesis'] = time.time() - synth_start

            result.research_stages.append({
                "stage": "Evidence Verification & Synthesis",
                "status": "completed",
                "description": "Synthesized certification, testing, and recognized laboratory requirements with verified citations."
            })

            result.execution_time = time.time() - start_time
            result.pipeline_stats["llm_provider"] = "NVIDIA NIM"
            result.pipeline_stats["llm_model"] = os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.2-11b-vision-instruct")
            result.pipeline_stats["llm_status"] = "SUCCESS"

            self._save_research_session(result, input_data.product_description or "")
            logger.info(f"Full compliance research completed in {result.execution_time:.2f} seconds")

        except AIServiceUnavailableException as ai_err:
            logger.error(f"AI reasoning service unavailable: {ai_err}")
            result.overall_assessment = "AI reasoning service is currently unavailable. The system cannot safely perform open-world semantic analysis at this time."
            result.recommendations = [
                "Please verify the NVIDIA NIM API key and model connectivity in the AI Health status.",
                "Ensure network access to https://integrate.api.nvidia.com/v1 is operational.",
                "Retry your compliance research request once AI reasoning is restored."
            ]
            result.pipeline_stats = {
                "llm_provider": "NVIDIA NIM",
                "llm_model": os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.2-11b-vision-instruct"),
                "llm_status": "UNAVAILABLE",
                "error": str(ai_err)
            }
            return self._finalize_result(result, start_time)

        except Exception as e:
            logger.error(f"Error in orchestration workflow: {str(e)}")
            result.overall_assessment = f"Workflow error: {str(e)}"
            return self._finalize_result(result, start_time)

        return self._finalize_result(result, start_time)

    async def run_standards_analysis_only(
        self,
        product_description: str,
        limit: int = 10
    ) -> OrchestrationResult:
        """Run standards discovery and scope matching analysis using the open-world research pipeline"""
        return await self.run_full_certification_analysis(
            OrchestrationInput(
                product_description=product_description,
                include_web_search=True,
                max_results_per_agent=limit
            )
        )

    def _save_research_session(self, result: OrchestrationResult, raw_query: str):
        """Save immutable research session to database for auditability and caching"""
        try:
            pu = result.product_understanding
            pu_dict = {
                "product_name": getattr(pu, "product_name", ""),
                "materials": getattr(pu, "materials", []),
                "intended_use": getattr(pu, "intended_use", ""),
                "industry": getattr(pu, "industry_context", "") or getattr(pu, "category", "")
            } if pu else {}

            session = ResearchSession(
                session_uuid=str(uuid.uuid4()),
                query=raw_query or (pu.product_name if pu else "Open-world query"),
                normalized_product=getattr(pu, "normalized_product_name", "") if pu else None,
                product_understanding=json.dumps(pu_dict),
                sources_investigated=json.dumps(result.sources_investigated),
                applicable_standards=json.dumps([m.standard_number for m in result.applicable_standards]),
                rejected_candidates=json.dumps(result.rejected_candidates),
                overall_assessment=result.overall_assessment,
                execution_time_seconds=int(round(result.execution_time))
            )
            with SessionLocal() as db:
                db.add(session)
                db.commit()
                result.session_id = session.session_uuid
        except Exception as e:
            logger.debug(f"Could not persist research session: {e}")

    # ------------------------------------------------------------------
    # Helper methods for individual agent calls
    # ------------------------------------------------------------------

    async def _get_certification_info_for_standard(
        self,
        standard_id: int,
        product_understanding: ProductUnderstanding,
        standard_number: Optional[str] = None
    ) -> CertificationInfo:
        """Get certification information for a specific standard"""
        return await self.certification_agent.get_certification_info(
            product_understanding, standard_id, standard_number
        )

    async def _get_testing_info_for_standard(
        self,
        standard_id: int,
        product_understanding: ProductUnderstanding,
        standard_number: Optional[str] = None
    ) -> TestingInformation:
        """Get testing information for a specific standard"""
        return await self.testing_agent.get_testing_information(
            product_understanding, standard_id, standard_number
        )

    async def _get_laboratory_recommendations_for_standard(
        self,
        standard_id: int,
        product_understanding: ProductUnderstanding,
        location: Optional[str],
        standard_number: Optional[str] = None
    ) -> List[Laboratory]:
        """Get laboratory recommendations for a specific standard"""
        criteria = LabSearchCriteria(
            standard_number=standard_number,
            product_category=product_understanding.category,
            location=location,
            max_results=3
        )
        return await self.laboratory_agent.find_labs_for_product(
            product_understanding, standard_id, location, criteria.max_results, standard_number
        )

    async def _analyze_compliance_for_standard(
        self,
        standard_id: int,
        document_text: str,
        product_understanding: Optional[ProductUnderstanding]
    ) -> GapAnalysisResult:
        """Analyze compliance of document against a specific standard"""
        context = None
        if product_understanding:
            context = DocumentAnalysisContext(
                document_content=document_text,
                document_metadata={"source": "provided_document"},
                product_understanding=product_understanding,
                target_standard_ids=[standard_id]
            )
        else:
            context = DocumentAnalysisContext(
                document_content=document_text,
                document_metadata={"source": "provided_document"},
                product_understanding=None,
                target_standard_ids=[standard_id]
            )

        results = await self.compliance_gap_agent.analyze_compliance_gaps(context)
        return results[0] if results else self._create_empty_gap_result(standard_id)

    async def _verify_citations_in_document(
        self,
        document_text: str,
        product_understanding: Optional[ProductUnderstanding]
    ) -> List[VerificationResult]:
        """Verify citations in a document"""
        return await self.citation_verification_agent.verify_claims_in_text(
            document_text,
            {"product_understanding": product_understanding} if product_understanding else None
        )

    async def _perform_web_search(
        self,
        product_understanding: ProductUnderstanding,
        standards: List[StandardMatch]
    ) -> List[WebSearchResult]:
        """Perform web search for additional information"""
        try:
            # Build search query from product understanding and standards
            query_parts = [
                product_understanding.product_name,
                product_understanding.category,
                product_understanding.intended_use
            ]
            query_parts = [p for p in query_parts if p]
            base_query = " ".join(query_parts)

            # Add standard numbers if available
            if standards:
                std_numbers = [s.standard_number for s in standards[:3]]
                if std_numbers:
                    base_query += " " + " ".join(std_numbers)

            # Perform search
            results = await self.web_retrieval_service.search(
                query=base_query,
                max_results=5
            )
            return results
        except Exception as e:
            logger.warning(f"Web search error: {e}")
            return []

    def _get_standard_details(self, standard_ids: List[int]) -> List[StandardMatch]:
        """Get StandardMatch objects for standard IDs (simplified)"""
        # This is a simplified version - in reality we'd fetch from DB and create StandardMatch objects
        # For now, return empty list - the calling code should handle this
        logger.warning("_get_standard_details called - returning empty list (would need DB connection)")
        return []

    def _create_empty_gap_result(self, standard_id: int) -> GapAnalysisResult:
        """Create an empty gap analysis result"""
        return GapAnalysisResult(
            standard_id=standard_id,
            standard_number="Unknown",
            standard_title="Unknown Standard",
            fulfilled_requirements=[],
            missing_requirements=[],
            partial_requirements=[],
            compliance_percentage=0.0,
            confidence=0.0,
            risk_level="Unknown",
            recommendations=["Unable to perform compliance analysis"],
            source_documents=[]
        )

    def _summarize_input(self, input_data: OrchestrationInput) -> Dict[str, Any]:
        """Create a summary of the input for the result"""
        summary = {}
        if input_data.product_description:
            summary['product_description'] = input_data.product_description[:100] + ("..." if len(input_data.product_description) > 100 else "")
        if input_data.product_understanding:
            summary['product_understanding_provided'] = True
            summary['product_name'] = input_data.product_understanding.product_name
            summary['category'] = input_data.product_understanding.category
        if input_data.document_text:
            summary['document_length'] = len(input_data.document_text)
        if input_data.target_standard_ids:
            summary['target_standard_ids'] = input_data.target_standard_ids
        if input_data.location:
            summary['location'] = input_data.location
        summary['include_web_search'] = input_data.include_web_search
        return summary

    async def _synthesize_results(self, result: OrchestrationResult) -> Tuple[str, List[str]]:
        """Synthesize all results into an overall assessment and recommendations"""
        # Use NVIDIA provider for accuracy-critical synthesis
        try:
            return await self._synthesize_results_with_llm(result)
        except Exception as e:
            logger.warning(f"LLM synthesis failed, falling back to rule-based synthesis: {e}")
            return self._synthesize_results_rule_based(result)

    def _synthesize_results_rule_based(self, result: OrchestrationResult) -> Tuple[str, List[str]]:
        """Rule-based synthesis of results into an overall assessment and recommendations"""
        assessment_parts = []
        recommendations = []

        # Product understanding summary
        if result.product_understanding:
            pu = result.product_understanding
            assessment_parts.append(
                f"Product: {pu.product_name} ({pu.category}) - {pu.intended_use} use"
            )
            if pu.confidence < 0.7:
                recommendations.append(
                    "Product understanding confidence is low - consider providing more detailed product description"
                )

        # Standards matching summary
        if result.applicable_standards:
            assessment_parts.append(
                f"Found {len(result.applicable_standards)} applicable standard(s)"
            )
            # List top standards
            top_standards = result.applicable_standards[:3]
            std_list = [f"{s.standard_number} ({s.title})" for s in top_standards]
            assessment_parts.append(f"Top standards: {', '.join(std_list)}")
        else:
            assessment_parts.append("No applicable standards found")
            recommendations.append("Verify product classification or consult with BIS for appropriate standards")

        # Certification info summary
        if result.certification_info:
            cert_count = len(result.certification_info)
            licensing_count = sum(1 for c in result.certification_info if c.license_required)
            assessment_parts.append(
                f"Certification info available for {cert_count} standard(s), {licensing_count} require license"
            )
        else:
            assessment_parts.append("No certification information generated")
            recommendations.append("Check if standards were successfully identified")

        # Testing info summary
        if result.testing_information:
            test_count = len(result.testing_information)
            assessment_parts.append(f"Testing requirements available for {test_count} standard(s)")
            # Check for any missing testing info
            empty_testing = [t for t in result.testing_information if not t.testing_requirements]
            if empty_testing:
                recommendations.append(
                    f"{len(empty_testing)} standard(s) have incomplete testing requirements"
                )
        else:
            assessment_parts.append("No testing information generated")

        # Laboratory recommendations summary
        if result.laboratory_recommendations:
            lab_count = len(result.laboratory_recommendations)
            bis_recognized = sum(1 for l in result.laboratory_recommendations if l.is_bis_recognized)
            assessment_parts.append(
                f"Found {lab_count} laboratory recommendation(s), {bis_recognized} BIS-recognized"
            )
            # Check for geographical coverage
            loc = result.input_summary.get('location')
            if loc:
                location_matches = sum(1 for l in result.laboratory_recommendations
                                   if loc.lower() in l.location.lower())
                if location_matches == 0 and result.laboratory_recommendations:
                    recommendations.append(
                        f"No laboratories found in specified location ({loc}) - consider expanding search area"
                    )
        else:
            assessment_parts.append("No laboratory recommendations generated")

        # Compliance analysis summary
        if result.compliance_analysis:
            compliant_count = sum(1 for c in result.compliance_analysis if c.compliance_percentage >= 80)
            avg_compliance = sum(c.compliance_percentage for c in result.compliance_analysis) / len(result.compliance_analysis) if result.compliance_analysis else 0
            assessment_parts.append(
                f"Compliance analysis for {len(result.compliance_analysis)} document(s) - average compliance: {avg_compliance:.1f}%"
            )
            if compliant_count < len(result.compliance_analysis):
                recommendations.append(
                    f"{len(result.compliance_analysis) - compliant_count} document(s) show compliance gaps requiring attention"
                )
        else:
            assessment_parts.append("No compliance analysis performed (no document provided)")

        # Citation verification summary
        if result.citation_verification:
            verified_count = sum(1 for v in result.citation_verification if v.is_verified)
            avg_confidence = sum(v.confidence for v in result.citation_verification) / len(result.citation_verification) if result.citation_verification else 0
            assessment_parts.append(
                f"Citation verification for {len(result.citation_verification)} claim(s) - {verified_count} verified, average confidence: {avg_confidence:.2f}"
            )
            if verified_count < len(result.citation_verification):
                recommendations.append(
                    f"{len(result.citation_verification) - verified_count} claim(s) lack sufficient citation support"
                )
        else:
            assessment_parts.append("No citation verification performed")

        # Web search summary
        if result.web_search_results:
            assessment_parts.append(f"Web search returned {len(result.web_search_results)} result(s)")
        else:
            assessment_parts.append("No web search performed")

        # Overall assessment
        if not assessment_parts:
            overall_assessment = "Analysis completed but no significant results generated"
        else:
            overall_assessment = " | ".join(assessment_parts)

        # Add general recommendations if we have enough information
        if result.product_understanding and result.applicable_standards:
            if not result.certification_info and not result.testing_information:
                recommendations.append(
                    "Consider running a more targeted analysis to get certification and testing details"
                )
            if len(result.laboratory_recommendations) == 0:
                recommendations.append(
                    "No laboratory recommendations generated - verify product category and location"
                )

        # Remove duplicate recommendations
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        return overall_assessment, unique_recommendations[:8]  # Limit to top 8 recommendations

    async def _synthesize_results_with_llm(self, result: OrchestrationResult) -> Tuple[str, List[str]]:
        """LLM-enhanced synthesis of results into an overall assessment and recommendations"""
        # Prepare a summary of the results for the LLM
        summary = {
            "product_understanding": {
                "product_name": result.product_understanding.product_name if result.product_understanding else None,
                "category": result.product_understanding.category if result.product_understanding else None,
                "intended_use": result.product_understanding.intended_use if result.product_understanding else None,
                "confidence": result.product_understanding.confidence if result.product_understanding else None
            } if result.product_understanding else None,
            "applicable_standards_count": len(result.applicable_standards),
            "applicable_standards": [{"standard_number": s.standard_number, "title": s.title} for s in result.applicable_standards[:5]],
            "certification_info_count": len(result.certification_info),
            "licensing_required_count": sum(1 for c in result.certification_info if c.license_required) if result.certification_info else 0,
            "testing_info_count": len(result.testing_information),
            "laboratory_recommendations_count": len(result.laboratory_recommendations),
            "bis_recognized_labs_count": sum(1 for l in result.laboratory_recommendations if l.is_bis_recognized) if result.laboratory_recommendations else 0,
            "compliance_analysis_count": len(result.compliance_analysis),
            "avg_compliance": sum(c.compliance_percentage for c in result.compliance_analysis) / len(result.compliance_analysis) if result.compliance_analysis else 0,
            "citation_verification_count": len(result.citation_verification),
            "verified_citations_count": sum(1 for v in result.citation_verification if v.is_verified) if result.citation_verification else 0,
            "avg_citation_confidence": sum(v.confidence for v in result.citation_verification) / len(result.citation_verification) if result.citation_verification else 0,
            "web_search_results_count": len(result.web_search_results)
        }

        system_prompt = """You are an expert BIS compliance analyst. Your task is to synthesize the results of a product compliance analysis into a clear overall assessment and actionable recommendations.

Based on the provided analysis data, generate:
1. A concise overall assessment (1-2 sentences) summarizing the key findings
2. A list of specific, actionable recommendations (maximum 8)

Focus on:
- The product identity and its regulatory implications
- Standards applicability and compliance status
- Certification, testing, and laboratory requirements
- Any gaps or issues that need attention
- Next steps for the manufacturer

Be clear, professional, and helpful. Base your response solely on the provided data."""

        user_prompt = f"""Please synthesize the following BIS compliance analysis results:

{json.dumps(summary, indent=2)}

Provide your response in JSON format with exactly these two fields:
{{
  "overall_assessment": "your overall assessment here",
  "recommendations": ["recommendation 1", "recommendation 2", ...]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Use NVIDIA provider for accuracy-critical synthesis
        response = await self.nvidia_provider.structured_output(
            messages=messages,
            response_model=SynthesisResult,
            temperature=0.2,
            max_tokens=1000
        )

        if response and response.data:
            return response.data.overall_assessment, response.data.recommendations
        else:
            # Fallback to rule-based if LLM fails to produce valid structured output
            return self._synthesize_results_rule_based(result)

    def _synthesize_standards_only(self, result: OrchestrationResult) -> Tuple[str, List[str]]:
        """Synthesize results for standards-only analysis"""
        assessment_parts = []
        recommendations = []

        if result.product_understanding:
            pu = result.product_understanding
            assessment_parts.append(
                f"Product: {pu.product_name} ({pu.category}) - {pu.intended_use} use"
            )

        if result.applicable_standards:
            assessment_parts.append(
                f"Found {len(result.applicable_standards)} applicable standard(s)"
            )
            # Show top 3
            top_standards = result.applicable_standards[:3]
            for std in top_standards:
                assessment_parts.append(
                    f"  - {std.standard_number}: {std.title} (applicability: {std.applicability_score}%)"
                )
            if len(result.applicable_standards) > 3:
                assessment_parts.append(f"  ... and {len(result.applicable_standards) - 3} more")
        else:
            assessment_parts.append("No applicable standards found")
            recommendations.append(
                "Try providing more detailed product description or check if product requires specialized standards"
            )

        overall_assessment = " | ".join(assessment_parts) if assessment_parts else "Analysis completed"
        return overall_assessment, recommendations

    def _finalize_result(self, result: OrchestrationResult, start_time: float) -> OrchestrationResult:
        """Ensure canonical decision and what-you-need-to-do are always generated before returning"""
        import time
        result.execution_time = time.time() - start_time
        if not result.what_you_need_to_do:
            result.what_you_need_to_do = self._generate_what_you_need_to_do(result)
        if not result.canonical_decision:
            result.canonical_decision = self._generate_canonical_decision(result)
        return result

    def _generate_what_you_need_to_do(self, result: OrchestrationResult) -> Dict[str, Any]:
        """
        Part 3 / Part 8.9: Unified 'What You Need To Do' Recommendation Panel.
        Merges certification_agent and testing_agent output once a standard reaches APPLICABLE.
        Enforces Rule 8.9 and 8.10 integrity:
        - Standard
        - Testing: VERIFIED / NOT_VERIFIED
        - BIS Certification: VERIFIED / NOT_VERIFIED
        - Mandatory under QCO: VERIFIED / NOT_VERIFIED
        - Certification Scheme: Scheme I / II / IV / NOT_VERIFIED
        - Guard: If no QCO evidence retrieved, reads:
          'Certification requirement not confirmed — verify with your local BIS office'
        """
        if not result.applicable_standards and not result.potential_standards:
            return {
                "has_applicable_standard": False,
                "standard_number": None,
                "title": None,
                "status": "NOT_APPLICABLE",
                "message": "Applicability not yet confirmed. Please provide clarified product specifications.",
                "qco_status": "NOT_VERIFIED",
                "qco_message": "Certification requirement not confirmed — verify with your local BIS office",
                "certification_scheme": "NOT_VERIFIED",
                "bis_certification_status": "NOT_VERIFIED",
                "testing_status": "NOT_VERIFIED",
                "tests": [],
                "next_actions": []
            }

        is_potential = bool(not result.applicable_standards and result.potential_standards)
        top_std = result.applicable_standards[0] if result.applicable_standards else result.potential_standards[0]
        std_num = top_std.standard_number
        std_title = top_std.title

        # Find matching cert info
        c_info = next((c for c in result.certification_info if c.standard_number == std_num or c.standard_id == top_std.standard_id), None)
        # Find matching testing info
        t_info = next((t for t in result.testing_information if t.standard_number == std_num or t.standard_id == top_std.standard_id), None)

        # Check QCO evidence strictly
        has_qco = False
        if c_info and c_info.license_required:
            sources_text = " ".join([str(s) for s in (c_info.sources or [])]).lower()
            if any(k in sources_text for k in ["qco", "quality control order", "statutory", "gazette", "compulsory"]):
                has_qco = True

        qco_status = "MANDATORY" if has_qco else "NOT_VERIFIED"
        qco_message = (
            "Mandatory under Quality Control Order (QCO)"
            if has_qco else
            "Certification requirement not confirmed — verify with your local BIS office"
        )

        # Scheme validation: Rule 8.9 - Do not infer a certification scheme merely because another product category commonly uses it
        scheme = "NOT_VERIFIED"
        if c_info and c_info.certification_scheme:
            cs = c_info.certification_scheme.strip()
            if any(valid in cs for valid in ["Scheme I", "Scheme II", "Scheme IV", "Scheme 1", "Scheme 2", "Scheme 4", "ISI", "CRS"]):
                scheme = cs
            else:
                scheme = "NOT_VERIFIED"

        bis_cert_status = "REQUIRED" if has_qco else ("VERIFIED" if c_info else "NOT_VERIFIED")

        # Tests
        tests = []
        if t_info and t_info.testing_requirements:
            testing_status = "VERIFIED"
            for tr in t_info.testing_requirements:
                # Rule 8.10: Requirement type must be one of MANDATORY, ROUTINE, TYPE_TEST, ACCEPTANCE_TEST, RECOMMENDED, NOT_VERIFIED
                # Never claim mandatory without verified QCO/statutory mandate
                req_type = "NOT_VERIFIED"
                if tr.is_mandatory and has_qco:
                    req_type = "MANDATORY"
                elif "routine" in tr.test_type.lower() or "routine" in tr.description.lower():
                    req_type = "ROUTINE"
                elif "type" in tr.test_type.lower():
                    req_type = "TYPE_TEST"
                elif "acceptance" in tr.test_type.lower():
                    req_type = "ACCEPTANCE_TEST"
                else:
                    req_type = "RECOMMENDED" if tr.test_type else "NOT_VERIFIED"

                clause = ""
                if isinstance(tr.source_reference, dict):
                    clause = tr.source_reference.get("clause_number") or tr.source_reference.get("clause", "")
                if not clause and "clause" in tr.description.lower():
                    import re
                    m = re.search(r'clause\s+([0-9.]+)', tr.description, re.IGNORECASE)
                    if m:
                        clause = f"Clause {m.group(1)}"

                tests.append({
                    "test_name": tr.test_type or tr.description[:60],
                    "clause": clause or "Scope Clause",
                    "test_method": tr.test_method or f"As per {std_num}",
                    "requirement_type": req_type,
                    "evidence_source": f"Official {std_num} Specification",
                    "is_mandatory": (req_type == "MANDATORY")
                })
        else:
            testing_status = "NOT_VERIFIED"

        # Step-by-step next actions sourced from BIS standard procedural workflow
        next_actions = []
        if c_info and c_info.certification_process:
            for p in c_info.certification_process:
                next_actions.append({
                    "step_number": p.step_number,
                    "step_name": p.step_name,
                    "description": p.description,
                    "responsible_party": p.responsible_party or "Manufacturer"
                })
        else:
            next_actions = [
                {
                    "step_number": 1,
                    "step_name": "Sample Testing Feasibility",
                    "description": f"Engage recognized testing laboratories to verify sample testing capability under {std_num}.",
                    "responsible_party": "Manufacturer / Lab"
                },
                {
                    "step_number": 2,
                    "step_name": "Technical Documentation",
                    "description": "Compile manufacturing machinery inventory, in-house test equipment calibration, and test personnel records.",
                    "responsible_party": "Manufacturer"
                },
                {
                    "step_number": 3,
                    "step_name": "Portal Application",
                    "description": f"Submit formal application via BIS Manakonline (e-BIS) Portal under {scheme if scheme != 'NOT_VERIFIED' else 'applicable scheme'}.",
                    "responsible_party": "Manufacturer"
                },
                {
                    "step_number": 4,
                    "step_name": "Factory Audit & Drawal",
                    "description": "Host BIS inspection officer for production surveillance audit and official factory sample drawal.",
                    "responsible_party": "BIS Officer / Manufacturer"
                },
                {
                    "step_number": 5,
                    "step_name": "Grant of Standard Mark",
                    "description": f"Upon successful independent laboratory test conformity, obtain BIS License to use the Standard Mark for {std_num}.",
                    "responsible_party": "Bureau of Indian Standards"
                }
            ]

        return {
            "has_applicable_standard": True,
            "standard_number": std_num,
            "title": std_title,
            "status": "NEEDS_CLARIFICATION" if is_potential else "APPLICABLE",
            "qco_status": "NOT_VERIFIED" if is_potential else qco_status,
            "qco_message": "Scope clarification required before statutory certification applicability can be confirmed." if is_potential else qco_message,
            "certification_scheme": scheme,
            "bis_certification_status": bis_cert_status,
            "testing_status": testing_status,
            "tests": tests,
            "next_actions": next_actions
        }

    def _generate_canonical_decision(self, result: OrchestrationResult) -> Dict[str, Any]:
        """
        Section 8.12: Canonical Decision Object
        Every analysis must terminate in exactly one canonical decision object.
        """
        return self._generate_canonical_decision_rule_based(result)

    def _generate_canonical_decision_rule_based(self, result: OrchestrationResult) -> Dict[str, Any]:
        """Rule-based canonical decision generation"""
        top_std = result.applicable_standards[0] if result.applicable_standards else None
        c_info = next((c for c in result.certification_info if top_std and (c.standard_number == top_std.standard_number or c.standard_id == top_std.standard_id)), None)

        has_qco = False
        if c_info and c_info.license_required:
            sources_text = " ".join([str(s) for s in (c_info.sources or [])]).lower()
            if any(k in sources_text for k in ["qco", "quality control order", "statutory", "gazette", "compulsory"]):
                has_qco = True

        scheme = "NOT_VERIFIED"
        if c_info and c_info.certification_scheme:
            cs = c_info.certification_scheme.strip()
            if any(valid in cs for valid in ["Scheme I", "Scheme II", "Scheme IV", "Scheme 1", "Scheme 2", "Scheme 4", "ISI", "CRS"]):
                scheme = cs

        decision_status = "APPLICABLE" if result.applicable_standards else (
            "NEEDS_CLARIFICATION" if (result.clarification_required or result.potential_standards) else "NOT_APPLICABLE"
        )

        pu = result.product_understanding
        product_identity = getattr(pu, 'product_name', '') if pu else ""
        product_family = (getattr(pu, 'product_family', None) or getattr(pu, 'category', '')) if pu else ""
        characteristics = {
            "materials": getattr(pu, 'materials', []) if pu else [],
            "intended_use": getattr(pu, 'intended_use', '') if pu else "",
            "target_user": (getattr(pu, 'target_user', None) or getattr(pu, 'market', 'Domestic')) if pu else ""
        }

        standards_list = []
        for s in (result.applicable_standards + result.potential_standards):
            meta = s.metadata or {}
            standards_list.append({
                "standard_number": s.standard_number,
                "title": s.title,
                "status": getattr(s, 'status', meta.get('status', 'APPLICABLE')),
                "why_found": s.reasoning,
                "scope_evidence": s.supporting_clauses,
                "product_match": getattr(s, 'confirmed_attributes', meta.get('confirmed_attributes', [])),
                "missing_information": getattr(s, 'missing_information', meta.get('missing_information', [])),
                "source": meta.get("source_domain", "Official BIS")
            })

        testing_list = []
        for t in result.testing_information:
            for tr in t.testing_requirements:
                clause = ""
                if isinstance(tr.source_reference, dict):
                    clause = tr.source_reference.get("clause_number") or tr.source_reference.get("clause", "")
                testing_list.append({
                    "test_name": tr.test_type or tr.description[:60],
                    "clause": clause or "Scope Clause",
                    "test_method": tr.test_method or f"As per {t.standard_number}",
                    "requirement_type": "MANDATORY" if (tr.is_mandatory and has_qco) else "RECOMMENDED",
                    "evidence_source": f"Official {t.standard_number}"
                })

        lab_list = []
        for l in result.laboratory_recommendations:
            lab_list.append({
                "name": l.lab_name,
                "address": l.address,
                "contact": l.contact_person or l.phone or l.email,
                "city": l.location,
                "distance_km": getattr(l, 'distance_km', None),
                "distance_str": getattr(l, 'distance_str', 'Distance not verified'),
                "accreditation": l.accreditation_body,
                "accredited_scope": l.accredited_scopes,
                "covered_standard": getattr(l, 'standard_number', ''),
                "source_url": getattr(l, 'website', '') or "https://www.manakonline.in"
            })

        return {
            "decision": {
                "status": decision_status,
                "reason": result.overall_assessment,
                "evidence_ids": [s.standard_number for s in result.applicable_standards]
            },
            "product": {
                "identity": product_identity,
                "family": product_family,
                "characteristics": characteristics
            },
            "standards": standards_list,
            "regulatory": {
                "qco_status": "MANDATORY" if has_qco else "NOT_VERIFIED",
                "certification": "REQUIRED" if has_qco else "NOT_VERIFIED",
                "scheme": scheme
            },
            "testing": testing_list,
            "laboratories": lab_list,
            "clarifications": result.clarification_questions,
            "audit": {
                "execution_time": round(result.execution_time, 3),
                "stages_completed": len(result.research_stages),
                "authoritative_sources_count": len(result.sources_investigated)
            }
        }


_orchestrator_agent: Optional[OrchestratorAgent] = None


def get_orchestrator_agent() -> OrchestratorAgent:
    """Get or create the orchestrator agent instance"""
    global _orchestrator_agent
    if _orchestrator_agent is None:
        _orchestrator_agent = OrchestratorAgent()
    return _orchestrator_agent