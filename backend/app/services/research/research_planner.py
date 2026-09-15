"""
Compliance Research Planner for Open-World Standards Discovery.
Dynamically constructs multi-dimensional search concepts and queries from product understanding.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class SearchDimension:
    """Individual targeted research vector"""
    dimension_name: str  # e.g., 'standard_discovery', 'qco_mandate', 'testing_requirements', 'certification_scheme'
    query: str
    target_domains: List[str]
    priority: int  # 1 = Highest (Tier 1 official BIS), 2 = Government, 3 = General
    expected_evidence_type: str

@dataclass
class ComplianceResearchPlan:
    """Complete dynamic search and research plan for an arbitrary product"""
    product_name: str
    normalized_name: str
    dimensions: List[SearchDimension] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    search_concepts: List[str] = field(default_factory=list)
    tier1_domains: List[str] = field(default_factory=lambda: ["bis.gov.in", "services.bis.gov.in"])
    tier2_domains: List[str] = field(default_factory=lambda: ["gov.in", "nic.in"])
    tier3_domains: List[str] = field(default_factory=lambda: ["iso.org", "iec.ch"])

class ComplianceResearchPlanner:
    """
    Engine responsible for planning targeted authoritative investigations.
    Avoids searching single raw user sentences; builds structured multi-angle search plans
    with dynamic concept expansion.
    """

    def generate_research_plan(
        self,
        product_understanding: Any,
        include_testing_search: bool = True
    ) -> ComplianceResearchPlan:
        """
        Construct dynamic search plan from structured product understanding with query expansion.
        """
        p_name = getattr(product_understanding, "product_name", "") or "product"
        p_norm = getattr(product_understanding, "normalized_product_name", "") or p_name
        p_use = getattr(product_understanding, "intended_use", "") or ""
        materials = getattr(product_understanding, "materials", []) or []
        mat_str = " ".join(materials[:2]) if materials else ""

        # Query Expansion Concepts for official BIS & regulatory discovery
        concepts = self._expand_product_concepts(p_name, p_norm, materials)

        plan = ComplianceResearchPlan(
            product_name=p_name,
            normalized_name=p_norm,
            search_concepts=concepts
        )

        dimensions: List[SearchDimension] = []

        # Vector 1: Core BIS Standards Discovery (Tier 1 priority)
        dimensions.append(SearchDimension(
            dimension_name="standards_discovery",
            query=f"BIS standard Indian Standard IS {p_norm}",
            target_domains=["bis.gov.in", "services.bis.gov.in"],
            priority=1,
            expected_evidence_type="standard_number_and_scope"
        ))

        # Vector 2: Mandatory Quality Control Order (QCO) & Ministry Mandates
        dimensions.append(SearchDimension(
            dimension_name="qco_mandate",
            query=f"Quality Control Order QCO mandatory BIS {p_norm} gazette",
            target_domains=["bis.gov.in", "gov.in", "nic.in"],
            priority=1,
            expected_evidence_type="qco_mandatory_timeline"
        ))

        # Vector 3: Functional / Technical Application standard
        if mat_str and mat_str.lower() not in p_norm.lower():
            dimensions.append(SearchDimension(
                dimension_name="material_application_standard",
                query=f"BIS IS specification {mat_str} {p_norm}",
                target_domains=["bis.gov.in", "services.bis.gov.in", "gov.in"],
                priority=2,
                expected_evidence_type="scope_and_specifications"
            ))
        elif p_use:
            clean_use = p_use[:40].replace('"', '')
            dimensions.append(SearchDimension(
                dimension_name="intended_use_standard",
                query=f"BIS Indian Standard {p_norm} {clean_use}",
                target_domains=["bis.gov.in", "gov.in"],
                priority=2,
                expected_evidence_type="application_clauses"
            ))

        # Vector 4: Certification Scheme & Licensing (ISI Mark / CRS)
        dimensions.append(SearchDimension(
            dimension_name="certification_scheme",
            query=f"BIS certification scheme ISI mark CRS license {p_norm}",
            target_domains=["bis.gov.in", "services.bis.gov.in"],
            priority=2,
            expected_evidence_type="licensing_requirements"
        ))

        # Vector 5: Domain-Specific Regulatory Vector
        industry = getattr(product_understanding, "industry_context", "") or getattr(product_understanding, "product_family", "")
        reg_domains = getattr(product_understanding, "possible_regulatory_domains", []) or []
        reg_str = " ".join(reg_domains).lower()

        if "food" in industry.lower() or "fssai" in reg_str or any(k in p_norm.lower() for k in ["oil", "food", "beverage", "tea", "coffee", "spice", "grain", "wheat", "rice"]):
            dimensions.append(SearchDimension(
                dimension_name="food_regulatory_framework",
                query=f"FSSAI food safety standard regulations {p_norm} BIS FAD India",
                target_domains=["fssai.gov.in", "bis.gov.in", "gov.in"],
                priority=1,
                expected_evidence_type="food_safety_regulations"
            ))
        elif "electrical" in industry.lower() or "electronics" in industry.lower() or "meity" in reg_str:
            dimensions.append(SearchDimension(
                dimension_name="electronics_crs_framework",
                query=f"MeitY Compulsory Registration Scheme CRS BIS {p_norm}",
                target_domains=["meity.gov.in", "bis.gov.in", "gov.in"],
                priority=1,
                expected_evidence_type="compulsory_registration_orders"
            ))
        elif "textile" in industry.lower() or "apparel" in industry.lower():
            dimensions.append(SearchDimension(
                dimension_name="textile_qco_framework",
                query=f"Ministry of Textiles QCO mandatory BIS Indian Standard {p_norm}",
                target_domains=["texmin.nic.in", "bis.gov.in", "gov.in"],
                priority=1,
                expected_evidence_type="textiles_quality_control_order"
            ))

        # Vector 6: Testing Requirements & Laboratory Recognition
        if include_testing_search:
            dimensions.append(SearchDimension(
                dimension_name="testing_and_labs",
                query=f"BIS recognized laboratory testing requirements {p_norm}",
                target_domains=["bis.gov.in", "gov.in", "nic.in"],
                priority=2,
                expected_evidence_type="accredited_test_methods"
            ))

        plan.dimensions = dimensions
        plan.search_queries = [dim.query for dim in dimensions]
        return plan

    def _expand_product_concepts(self, p_name: str, p_norm: str, materials: List[str]) -> List[str]:
        """
        Dynamically expand product into search concepts for official BIS discovery.
        e.g., '100% Combed Cotton T-Shirt' -> ['cotton knitted sports shirt', 'cotton t-shirt', 't-shirt', 'shirt', 'knitted apparel']
        """
        concepts: List[str] = [p_norm]
        clean_lower = p_norm.lower()

        # Remove percentages or counts (e.g. 100%, 50%)
        stripped = re.sub(r'\b\d+%\s*', '', clean_lower).strip()
        if stripped and stripped != clean_lower:
            concepts.append(stripped)

        # Apparel / T-Shirt expansions
        if "t-shirt" in clean_lower or "t shirt" in clean_lower or "tshirt" in clean_lower:
            concepts.extend([
                "cotton knitted sports shirt",
                "cotton knitted shirt",
                "cotton t-shirt",
                "knitted t-shirt",
                "shirt",
                "knitted sports shirt"
            ])
        elif any(k in clean_lower for k in ["flask", "bottle", "drinkware", "vessel", "water bottle"]):
            concepts.extend([
                "vacuum flask",
                "stainless steel vacuum flask",
                "vacuum bottle",
                "insulated flask",
                "domestic vacuum flask",
                "stainless steel bottle",
                "drinking bottle",
                "water bottle"
            ])
        elif "cable" in clean_lower or "wire" in clean_lower:
            concepts.extend([
                "pvc insulated cable",
                "electric cable",
                "insulated cable for working voltages"
            ])
        elif "oil" in clean_lower:
            concepts.extend([
                "groundnut oil",
                "edible oil",
                "expressed groundnut oil",
                "refined groundnut oil"
            ])
        elif "water" in clean_lower and ("packaged" in clean_lower or "drinking" in clean_lower):
            concepts.extend([
                "packaged drinking water",
                "packaged natural mineral water"
            ])
        elif any(k in clean_lower for k in ["shoe", "footwear", "boot", "sandal", "sneaker"]):
            concepts.extend([
                "safety footwear",
                "leather footwear",
                "footwear",
                "shoes"
            ])
        elif any(k in clean_lower for k in ["cement", "concrete", "mortar"]):
            concepts.extend([
                "portland cement",
                "ordinary portland cement",
                "cement"
            ])
        elif any(k in clean_lower for k in ["steel bar", "rebar", "tmt", "structural steel"]):
            concepts.extend([
                "high strength deformed steel bars",
                "tmt bars",
                "structural steel",
                "steel bars"
            ])
        elif any(k in clean_lower for k in ["toy", "toys"]):
            concepts.extend([
                "safety of toys",
                "electric toys",
                "mechanical toys"
            ])

        # General open-world fallback: extract short 1-2 word concepts from stripped name
        words = [w for w in stripped.split() if len(w) > 2 and w not in ["the", "for", "and", "with", "item", "article", "use", "make", "manufacture"]]
        if len(words) >= 2:
            concepts.append(" ".join(words[-2:]))
        if len(words) >= 1:
            concepts.append(words[-1])

        # Material-article combinations
        for m in materials:
            if m.lower() not in clean_lower:
                concepts.append(f"{m} {stripped}")

        # Deduplicate preserving order
        unique_concepts: List[str] = []
        for c in concepts:
            c_clean = c.strip()
            if c_clean and c_clean not in unique_concepts:
                unique_concepts.append(c_clean)

        return unique_concepts

_research_planner_instance: Optional[ComplianceResearchPlanner] = None

def get_research_planner() -> ComplianceResearchPlanner:
    global _research_planner_instance
    if _research_planner_instance is None:
        _research_planner_instance = ComplianceResearchPlanner()
    return _research_planner_instance
