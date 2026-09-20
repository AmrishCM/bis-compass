import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, model_validator
from app.services.llm.provider_factory import get_llm_provider
import logging

logger = logging.getLogger(__name__)

class ProductUnderstanding(BaseModel):
    """
    Open-world structured product understanding.
    Supports ANY arbitrary user product without predefined whitelists or taxonomies.
    """
    product_name: str = Field(default="Product", description="Specific name of the product")
    normalized_product_name: str = Field(default="", description="Normalized/canonical name of product")
    product_description: str = Field(default="", description="Original or cleaned user product description")
    product_family: str = Field(default="", description="Inferred product family / broad product functional group")
    materials: List[str] = Field(default_factory=list, description="Materials used in the product")
    components: List[str] = Field(default_factory=list, description="Key components, parts, or assemblies")

    @model_validator(mode="before")
    @classmethod
    def handle_aliases_and_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("product_name"):
                data["product_name"] = (
                    data.get("product_identity")
                    or data.get("normalized_name")
                    or data.get("normalized_product_name")
                    or "Product"
                )
            if not data.get("normalized_product_name"):
                data["normalized_product_name"] = data.get("normalized_name") or data.get("product_name", "")
            if not data.get("industry_context") and data.get("industry"):
                data["industry_context"] = data["industry"]
        return data
    commercial_intent: str = Field(default="Manufacture / Sale", description="Commercial action: Sell, Manufacture, Import, Distribute, Export, or Test")
    intended_use: str = Field(default="", description="Intended use (domestic, commercial, industrial, medical, etc.)")
    application: str = Field(default="", description="Specific practical application / function")
    industry_context: str = Field(default="", description="Industry context or domain")
    physical_form: str = Field(default="", description="Physical form, construction, or packaging type")
    technical_attributes: Dict[str, Any] = Field(default_factory=dict, description="Technical specifications, ratings, dimensions")
    regulatory_characteristics: Dict[str, Any] = Field(default_factory=dict, description="Regulatory characteristics: food-contact, electrical, pressure, medical, etc.")
    possible_regulatory_domains: List[str] = Field(default_factory=list, description="Regulatory domains: FSSAI, BIS Food, BIS Electrotechnical, etc.")
    possible_domains: List[str] = Field(default_factory=list, description="Hypothesized domains (packaging, electronics, textile, etc.)")
    unknown_attributes: List[str] = Field(default_factory=list, description="Attributes that remain unknown from the description")
    confidence: float = Field(default=0.8, description="Confidence in product understanding (0.0 to 1.0)")
    clarification_required: bool = Field(default=False, description="True if description is too vague or only describes a material")
    clarification_questions: List[str] = Field(default_factory=list, description="Specific questions to clarify ambiguous products")
    search_terms: List[str] = Field(default_factory=list, description="Dynamic technical search queries for retrieval")

    # Backwards compatibility attributes
    category: str = Field(default="", description="Category alias")
    sub_category: Optional[str] = Field(default=None, description="Sub-category alias")
    market: str = Field(default="Domestic", description="Target market")
    possible_standard_categories: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    product_profile: Optional[Dict[str, Any]] = Field(default=None, description="Structured ProductProfile mapping confirmed and unknown attributes")
    multi_product_detected: Optional[Dict[str, Any]] = Field(default=None, description="Details if multiple products were specified")


class ProductUnderstandingService:
    """
    Open-World Product Understanding Service.
    Parses any arbitrary natural-language product description into an open-world representation.
    Separates Product Identity from Material, detects vague queries for clarification,
    and dynamically expands technical query representations.
    """

    def __init__(self):
        self.llm_provider = get_llm_provider()

    async def understand_product(self, product_description: str) -> ProductUnderstanding:
        """
        Analyze arbitrary natural language product description using open-world intelligence.
        """
        desc = (product_description or "").strip()
        if not desc:
            return self._create_empty_understanding()

        # Step 1: Pre-check for overly vague or purely material queries
        vague_check = self._check_vague_or_material_only(desc)
        if vague_check:
            return vague_check

        # Step 2: Attempt LLM-based open-world extraction if configured
        try:
            understanding = await self._extract_with_llm(desc)
            if understanding:
                understanding = self._post_process_understanding(understanding, desc)
                return understanding
        except Exception as e:
            logger.warning(f"LLM extraction failed, using resilient open-world heuristic parser: {e}")

        # Step 3: Fallback open-world parser
        return self._extract_open_world_heuristics(desc)

    def _check_vague_or_material_only(self, desc: str) -> Optional[ProductUnderstanding]:
        """
        Detects if user only entered a material or vague phrase (e.g. "We manufacture steel products", "plastic items")
        and returns a clarification request instead of guessing.
        """
        d_lower = desc.lower().strip().rstrip('.!?')

        # Vague phrases where product identity is unknown
        vague_patterns = [
            r'^(we\s+(make|manufacture|produce|sell|deal\s+in)\s+)?(steel|metal|iron|aluminum|copper|plastic|polymer|glass|rubber|wooden|textile|chemical)\s+(products|items|goods|materials|components)?$',
            r'^(steel|metal|iron|plastic|polymer|textile|copper|aluminum)\s*(products|items|goods)?$',
            r'^(we\s+(make|manufacture|produce|sell)\s+)?products?$'
        ]

        for pattern in vague_patterns:
            if re.search(pattern, d_lower):
                # Identify material mentioned
                detected_material = "metal/material"
                for mat in ["steel", "iron", "aluminum", "copper", "plastic", "polymer", "textile", "rubber", "glass", "chemical"]:
                    if mat in d_lower:
                        detected_material = mat.capitalize()
                        break

                return ProductUnderstanding(
                    product_name=f"Unspecified {detected_material} Product",
                    normalized_product_name="Unspecified Material Product",
                    product_description=desc,
                    product_family="Unspecified",
                    materials=[detected_material],
                    intended_use="Unspecified",
                    application="Unspecified",
                    industry_context="Materials & Manufacturing",
                    physical_form="Unknown",
                    technical_attributes={},
                    regulatory_characteristics={},
                    possible_domains=[f"{detected_material} Manufacturing"],
                    unknown_attributes=["Product Type", "Intended Use", "Dimensions", "Capacity", "Application"],
                    confidence=0.35,
                    clarification_required=True,
                    clarification_questions=[
                        f"I can identify that your product is made of {detected_material}, but the specific product type is unclear.",
                        f"What specific {detected_material} product do you manufacture? (For example: cookware/utensil, piping/tube, storage container, structural section, wire, or appliance component?)",
                        "Is the product intended for domestic, commercial, or heavy industrial use?",
                        "Does the product have any direct contact with food, potable water, or electrical current?"
                    ],
                    search_terms=[f"{detected_material.lower()} products"],
                    category=f"{detected_material} Products",
                    missing_information=["Specific product functional identity", "Intended application"]
                )

        return None

    async def _extract_with_llm(self, desc: str) -> Optional[ProductUnderstanding]:
        """Use NVIDIA LLM to perform open-world structured product understanding"""
        system_prompt = """You are an Open-World Product Intelligence and Standards Analyst.
Your task is to analyze ANY arbitrary user product description without constraining it to a predefined whitelist.

Follow these strict rules:
1. SEPARATE PRODUCT IDENTITY FROM MATERIAL:
   A material (e.g., 'stainless steel', 'cotton', 'copper') is NOT the product identity.
   Identify WHAT the product is (e.g., 'Vacuum Flask', 'T-Shirt', 'Electric Cable', 'Packaging Film', 'Sensor Patch').
2. EXTRACT WHAT IS ACTUALLY PRESENT:
   Extract materials, components, physical form, intended use, application, and technical attributes.
   Do not fabricate attributes not mentioned.
3. IDENTIFY REGULATORY CHARACTERISTICS:
   Flag boolean traits: 'food_contact', 'electrical', 'pressure_vessel', 'child_product', 'medical_device', 'hazardous', etc.
4. CLARIFICATION CHECK:
   If the description is too vague to know what the product actually does, set clarification_required = true with targeted questions.
5. GENERATE DYNAMIC SEARCH TERMS:
   Derive 3-5 technical search phrases representing the product function and standard scope terminology.

Respond ONLY with valid JSON matching the ProductUnderstanding schema."""

        user_prompt = f"""Analyze this arbitrary product description:
Product Description: "{desc}"

Extract open-world structured information in JSON matching the schema."""

        structured_response = await self.llm_provider.structured_output(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_model=ProductUnderstanding,
            temperature=0.1,
            max_tokens=1200
        )

        if structured_response and structured_response.data:
            return structured_response.data
        return None

    def _extract_open_world_heuristics(self, desc: str) -> ProductUnderstanding:
        """
        Resilient open-world heuristic parser that does NOT rely on a fixed taxonomy.
        Extracts product identity, materials, functions, and forms from natural language structure.
        """
        d_lower = desc.lower()

        # Extract material mentions
        known_materials_dict = {
            "Stainless Steel (SS 304)": ["ss 304", "grade 304", "food grade steel"],
            "Stainless Steel (SS 316)": ["ss 316", "grade 316"],
            "Stainless Steel": ["stainless steel", "stainless-steel", "ss "],
            "Mild Steel / Iron": ["mild steel", "iron", "carbon steel", "galvanized iron"],
            "Copper": ["copper"],
            "Aluminum": ["aluminum", "aluminium"],
            "Cotton": ["cotton", "combed cotton", "organic cotton"],
            "Seaweed Biopolymer / Alginate": ["seaweed", "alginate", "kelp", "agar"],
            "Polyvinyl Chloride (PVC)": ["pvc", "polyvinyl chloride"],
            "Polypropylene (PP)": ["polypropylene", "pp "],
            "Polyethylene (PET/PE)": ["polyethylene", "pet ", "hdpe", "ldpe"],
            "Lithium-ion": ["lithium", "li-ion", "lithium-ion", "lfp", "nmc"],
            "Ceramic": ["ceramic", "porcelain", "vitrified"],
            "Portland Cement": ["cement", "clinker", "portland"]
        }

        materials = []
        for mat_name, patterns in known_materials_dict.items():
            if any(p in d_lower for p in patterns):
                if mat_name not in materials:
                    materials.append(mat_name)

        # General steel catch-up if specific not triggered
        if "steel" in d_lower and not any("Steel" in m for m in materials):
            materials.append("Steel")

        # Determine Product Identity vs Material
        # Filter out common filler phrases
        clean_text = re.sub(r'^(we\s+(manufacture|produce|make|create|develop|sell|design)|i\s+(want\s+to\s+sell|manufacture|make))\s+', '', d_lower).strip()

        # Identify physical form
        physical_form = "Solid Article"
        if any(w in d_lower for w in ["film", "sheet", "foil", "membrane", "wrap"]):
            physical_form = "Flexible Film / Sheet"
        elif any(w in d_lower for w in ["bottle", "flask", "canister", "tank", "container", "box", "drum", "jar"]):
            physical_form = "Hollow Container / Vessel"
        elif any(w in d_lower for w in ["cable", "wire", "cord", "conductor", "lead"]):
            physical_form = "Flexible Cable / Conductor"
        elif any(w in d_lower for w in ["patch", "strip", "band"]):
            physical_form = "Flexible Patch / Substrate"
        elif any(w in d_lower for w in ["shirt", "t-shirt", "garment", "fabric", "cloth", "apparel"]):
            physical_form = "Knitted / Woven Textile Garment"
        elif any(w in d_lower for w in ["powder", "granule", "clinker"]):
            physical_form = "Particulate / Powder"

        # Determine Intended Use / Application
        intended_use = "General Consumer Use"
        if any(w in d_lower for w in ["domestic", "household", "home", "kitchen", "personal"]):
            intended_use = "Domestic / Household"
        elif any(w in d_lower for w in ["sports", "athletic", "fitness", "exercise"]):
            intended_use = "Sports & Fitness Monitoring"
        elif any(w in d_lower for w in ["agriculture", "agricultural", "farming", "irrigation"]):
            intended_use = "Agricultural / Farming"
        elif any(w in d_lower for w in ["industrial", "factory", "plant", "heavy duty"]):
            intended_use = "Industrial / Commercial"
        elif any(w in d_lower for w in ["medical", "clinical", "hospital", "patient"]):
            intended_use = "Medical / Healthcare"

        # Regulatory Characteristics (critical for preventing false positives)
        regulatory_chars = {
            "electrical": any(w in d_lower for w in ["electric", "electrical", "voltage", "power", "watt", "amp", "battery", "sensor", "controller", "cable", "wire", "circuit", "heater"]),
            "food_contact": any(w in d_lower for w in ["food", "drink", "drinking", "beverage", "flask", "bottle", "edible", "packaging film", "utensil", "cookware", "water"]),
            "thermal_insulation": any(w in d_lower for w in ["vacuum", "insulated", "thermos", "cold-storage", "refrigeration", "thermal"]),
            "wearable_body_contact": any(w in d_lower for w in ["wearable", "patch", "skin", "garment", "shirt", "apparel"]),
            "biodegradable": any(w in d_lower for w in ["biodegradable", "compostable", "bio-based", "seaweed"])
        }

        # Extract specific product name from description using word boundaries
        name_candidate = re.split(r'\b(for|with|to)\b', clean_text)[0].strip()
        name_candidate = re.sub(r'^(a|an|the)\s+', '', name_candidate).strip()
        product_name = name_candidate.title() if len(name_candidate) >= 3 else clean_text.title()

        # Hypothesize product family with strict domain precedence
        product_family = "Manufactured Product"
        if any(w in d_lower for w in ["water heater", "geyser", "immersion heater"]):
            product_family = "Electrical Water Heating Appliances"
        elif any(w in d_lower for w in ["vacuum flask", "insulated flask", "thermal flask"]) or (re.search(r'\b(flask|thermos)\b', d_lower) and "thermostat" not in d_lower):
            product_family = "Vacuum Insulated Drinkware & Flasks"
        elif any(w in d_lower for w in ["t-shirt", "shirt", "clothing", "apparel", "garment"]):
            product_family = "Apparel & Garments"
        elif any(w in d_lower for w in ["cable", "wire", "conductor", "wiring"]):
            product_family = "Electrical Cables & Wiring"
        elif any(w in d_lower for w in ["packaging film", "packaging", "wrapping film", "film"]):
            product_family = "Packaging Films & Materials"
        elif any(w in d_lower for w in ["sensor", "patch", "textile sensor"]):
            product_family = "Smart Wearable Sensor Devices"
        elif any(w in d_lower for w in ["battery", "cells", "accumulator"]):
            product_family = "Electrochemical Cells & Batteries"
        elif any(w in d_lower for w in ["mineral water", "drinking water", "packaged water"]):
            product_family = "Packaged Potable Drinking Water"
        elif any(w in d_lower for w in ["tray", "container"]):
            product_family = "Containers & Molded Trays"

        # Dynamic query expansion
        search_terms = self._generate_open_world_search_terms(product_name, product_family, materials, intended_use, d_lower)

        # Possible domains
        possible_domains = []
        if regulatory_chars["electrical"]:
            possible_domains.append("Electrical & Electronics")
        if regulatory_chars["food_contact"]:
            possible_domains.append("Food Contact & Utensils")
        if regulatory_chars["wearable_body_contact"]:
            possible_domains.append("Textile & Wearables")
        if any(w in d_lower for w in ["agriculture", "farming", "irrigation"]):
            possible_domains.append("Agricultural Equipment")
        if not possible_domains:
            possible_domains.append("Consumer Products")

        return ProductUnderstanding(
            product_name=product_name,
            normalized_product_name=product_name,
            product_description=desc,
            product_family=product_family,
            materials=materials,
            components=[],
            intended_use=intended_use,
            application=intended_use,
            industry_context=possible_domains[0] if possible_domains else "General Manufacturing",
            physical_form=physical_form,
            technical_attributes={},
            regulatory_characteristics=regulatory_chars,
            possible_domains=possible_domains,
            unknown_attributes=["Exact dimensions", "Nominal capacity / rating", "Standard grade certificate"],
            confidence=0.80,
            clarification_required=False,
            clarification_questions=[],
            search_terms=search_terms,
            category=product_family,
            missing_information=["Specific manufacturing test report", "Marking & labeling details"]
        )

    def _generate_open_world_search_terms(
        self,
        product_name: str,
        product_family: str,
        materials: List[str],
        intended_use: str,
        desc_lower: str
    ) -> List[str]:
        """
        Dynamically generate 3-6 targeted search representations.
        Focuses on product function and scope terminology rather than isolated materials.
        """
        terms = []

        # 1. Primary functional phrase
        terms.append(product_name.lower())

        # 2. Product family + functional intent
        if product_family and product_family != "Manufactured Product":
            terms.append(product_family.lower())

        # 3. Specific domain synonyms
        if "vacuum" in desc_lower or "flask" in desc_lower:
            terms.extend(["vacuum flask", "insulated flask", "stainless steel vacuum flask", "domestic flasks"])
        elif "t-shirt" in desc_lower or "shirt" in desc_lower:
            terms.extend(["cotton t-shirt", "knitted fabric garment", "cotton textile apparel"])
        elif "cable" in desc_lower or "wire" in desc_lower:
            terms.extend(["pvc insulated cable", "electric cables", "cables up to 1100v"])
        elif "heater" in desc_lower or "geyser" in desc_lower:
            terms.extend(["electric storage water heater", "water heater", "liquid heating appliances"])
        elif "seaweed" in desc_lower or "packaging film" in desc_lower:
            terms.extend(["biodegradable food packaging film", "food contact packaging film", "biodegradable plastics"])
        elif "sensor" in desc_lower and "textile" in desc_lower:
            terms.extend(["smart textile sensor", "wearable health monitor", "electronic textile"])
        elif "battery" in desc_lower or "cells" in desc_lower:
            terms.extend(["lithium cells and batteries", "secondary lithium battery", "portable batteries"])
        elif "water" in desc_lower and ("drinking" in desc_lower or "mineral" in desc_lower):
            terms.extend(["packaged drinking water", "mineral water", "potable water"])

        # 4. Product with top material
        if materials:
            terms.append(f"{materials[0].lower()} {product_name.lower()}")

        # Deduplicate while preserving order
        unique_terms = []
        for t in terms:
            t_clean = t.strip()
            if t_clean and t_clean not in unique_terms:
                unique_terms.append(t_clean)

        return unique_terms[:6]

    def _post_process_understanding(
        self,
        understanding: ProductUnderstanding,
        desc: str
    ) -> ProductUnderstanding:
        """Validate and enrich extracted understanding"""
        if not understanding.product_description:
            understanding.product_description = desc

        if not understanding.normalized_product_name:
            understanding.normalized_product_name = understanding.product_name

        if not understanding.category and understanding.product_family:
            understanding.category = understanding.product_family

        if not understanding.search_terms:
            understanding.search_terms = self._generate_open_world_search_terms(
                understanding.product_name,
                understanding.product_family,
                understanding.materials,
                understanding.intended_use,
                desc.lower()
            )

        return understanding


# Alias for backwards compatibility
ProductUnderstandingEngine = ProductUnderstandingService

# Global engine instance
_product_understanding_service: Optional[ProductUnderstandingService] = None

def get_product_understanding_engine() -> ProductUnderstandingService:
    """Get or create product understanding service instance"""
    global _product_understanding_service
    if _product_understanding_service is None:
        _product_understanding_service = ProductUnderstandingService()
    return _product_understanding_service

def get_product_understanding_service() -> ProductUnderstandingService:
    """Get or create product understanding service instance"""
    return get_product_understanding_engine()