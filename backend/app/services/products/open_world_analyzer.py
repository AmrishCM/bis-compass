"""
Open-World Product Understanding & Entity Extraction Analyzer.
Dynamically infers product identity, commercial intent, materials, intended use,
technical attributes, and regulatory scope for any arbitrary product using the NVIDIA LLM.
Strictly separates Product Identity, Material, Intended Use, and Commercial Intent.
"""
from typing import Dict, Any, List, Optional
import logging
import json
import re

from app.services.products.product_understanding import ProductUnderstanding
from app.services.products.product_profile import ProductProfile, MultiProductDetection
from app.services.llm.provider_factory import get_llm_provider
from app.core.exceptions import AIServiceUnavailableException

logger = logging.getLogger(__name__)

VAGUE_MATERIAL_ONLY_PATTERNS = [
    r'^(?:we\s+manufacture|we\s+sell|i\s+make|we\s+make|we\s+produce|we\s+deal\s+in|i\s+manufacture)?\s*(?:steel|iron|plastic|copper|aluminum|glass|rubber|paper|fabric|wood|chemical)\s*(?:products?|items?|goods?|materials?)?\.?$'
]

class OpenWorldProductAnalyzer:
    """
    Open-World Product Analyzer.
    Uses NVIDIA NIM LLM for genuine semantic extraction and strictly separates
    product identity from commercial intent and subordinate materials.
    """

    def __init__(self):
        self.llm_provider = get_llm_provider()

    async def analyze_product(self, raw_input: str) -> ProductUnderstanding:
        """Analyze arbitrary user description into structured product intelligence"""
        clean_text = raw_input.strip()
        logger.info(f"Open-world product analysis for: '{clean_text[:60]}'")

        # 1. Immediate pre-check for vague material-only inputs
        if self._is_vague_material_input(clean_text):
            return self._build_clarification_response(clean_text)

        # 2. Call NVIDIA LLM for structured product understanding
        system_prompt = (
            "You are an Open-World Product Intelligence and Compliance Extraction Engine.\n"
            "Analyze the user's natural-language product input and output ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "product_name": "Specific manufactured or processed article noun phrase (e.g. \'Groundnut Oil\', \'Cotton T-Shirt\', \'Stainless Steel Vacuum Flask\', \'Biodegradable Seaweed Packaging Film\')",\n'
            '  "normalized_name": "Singular canonical product name without conversational filler",\n'
            '  "commercial_intent": "Commercial action: Sell, Manufacture, Import, Distribute, Export, or Test",\n'
            '  "materials": ["List of component materials, e.g. \'Groundnut\', \'Cotton\', \'Stainless Steel\'"],\n'
            '  "components": ["List of constituent components or parts, e.g. \'Flask Body\', \'Vacuum Seal\', \'Screw Cap\'"],\n'
            '  "intended_use": "Specific practical use or application",\n'
            '  "application": "Operational application context (e.g. beverage storage, apparel, food packaging)",\n'
            '  "industry": "Specific industry sector accurately representing the finished article (e.g. \'Consumer Goods & Household\', \'Food Contact & Utensils\', \'Textiles & Apparel\', \'Food & Agriculture\', \'Mechanical & Metallurgy\', \'Electrical & Electronics\') or \'Not confidently identified\'",\n'
            '  "physical_form": "Physical form (e.g. Liquid, Knitted garment, Double-walled container, Thin film) or \'Not specified\'",\n'
            '  "technical_attributes": {},\n'
            '  "hypothesized_domains": [\n'
            '    {"domain": "Domain Name", "reason": "Specific justification based strictly on product characteristics"}\n'
            '  ],\n'
            '  "clarification_required": false,\n'
            '  "clarification_questions": []\n'
            "}\n\n"
            "STRICT RULES:\n"
            "1. STRIP ALL CONVERSATIONAL PHRASING: Never include 'Want to sell', 'I manufacture', 'We make', 'across India' in product_name!\n"
            "2. SEPARATE PRODUCT FROM MATERIAL: Groundnut is raw material; Groundnut Oil is product. Cotton is material; T-Shirt is product.\n"
            "3. DOMAIN JUSTIFICATION: Every hypothesized domain MUST have an explicit reason derived from product characteristics. For cotton T-shirts: Textiles/Apparel. NEVER hypothesize unrelated domains like energy efficiency or heavy machinery without factual evidence!\n"
            "4. NO FAKE DEFAULTS: If industry or family is ambiguous, set 'Not confidently identified'. NEVER default to 'General Manufacturing'!\n"
            "5. NO FAKE PHYSICAL FORMS: If physical form is not explicitly stated or inferred, set 'Not specified'. NEVER default to 'Manufactured Item'!\n"
            "6. NO FALSE ELECTRICAL CLASSIFICATION: Household drinking bottles, flasks, cookware, tableware, food containers, and manual vessels are NEVER in 'Electrical & Electronics'. They belong to 'Consumer Goods', 'Food Contact & Utensils', or 'Mechanical & Metallurgy'.\n"
            "7. Return ONLY valid JSON, no surrounding text."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f'Input: "{clean_text}"'}
        ]

        try:
            response = await self.llm_provider.chat(messages=messages, temperature=0.05, max_tokens=450)
            raw_content = response.content.strip()

            # Clean JSON formatting
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.startswith("```"):
                raw_content = raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            raw_content = raw_content.strip()

            parsed = json.loads(raw_content)

        except json.JSONDecodeError as json_err:
            logger.warning(f"Failed to parse JSON from LLM: {json_err}. Raw: {raw_content[:200]}")
            # Try regex extraction
            match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                except Exception:
                    parsed = self._fallback_deterministic_parse(clean_text)
            else:
                parsed = self._fallback_deterministic_parse(clean_text)

        except Exception as llm_err:
            logger.warning(f"NVIDIA LLM reasoning encountered issue: {llm_err}. Using deterministic semantic parser.")
            parsed = self._fallback_deterministic_parse(clean_text)

        # 3. Post-process extracted fields to guarantee clean product identity
        raw_p_name = parsed.get("product_name") or clean_text
        product_name = self._sanitize_product_name(raw_p_name)
        normalized_name = parsed.get("normalized_name") or self._normalize_name(product_name)
        commercial_intent = parsed.get("commercial_intent") or self._detect_commercial_intent(clean_text)
        materials = parsed.get("materials") or []
        components = parsed.get("components") or []
        intended_use = parsed.get("intended_use") or f"Functional usage of {product_name}"
        application = parsed.get("application") or intended_use
        physical_form = parsed.get("physical_form") or "Not specified"
        if physical_form.lower() in ["manufactured item", "general item", "unknown", "item"]:
            physical_form = "Not specified"
        technical_attributes = parsed.get("technical_attributes") or {}

        industry = parsed.get("industry")
        if not industry or industry.lower() in ["general manufacturing", "general", "none", "unknown"]:
            industry = "Not confidently identified"

        # Domains with factual reasons
        hypo_domains_data = parsed.get("hypothesized_domains") or []
        reg_domains: List[str] = []
        domain_reasons: Dict[str, str] = {}
        if isinstance(hypo_domains_data, list):
            for d in hypo_domains_data:
                if isinstance(d, dict) and d.get("domain"):
                    name = d["domain"]
                    reg_domains.append(name)
                    domain_reasons[name] = d.get("reason", "Inferred from product identity")
                elif isinstance(d, str):
                    reg_domains.append(d)

        # Cross-field validation to catch domain mismatch (Bug 1 fix)
        p_name_lower = product_name.lower()
        mat_lower = [m.lower() for m in materials]
        desc_lower = clean_text.lower()
        is_drinkware_or_cookware = any(k in p_name_lower or k in desc_lower for k in [
            "bottle", "flask", "drinkware", "drinking", "cup", "mug", "tumbler", "jug",
            "utensil", "cookware", "pan", "pot", "vessel", "food container", "tiffin"
        ])

        has_electrical_specs = any(k in desc_lower for k in [
            "electric", "geyser", "heating element", "battery", "electronic", "motor",
            "voltage", "watt", "sensor patch", "conductor", "cable", "wire"
        ])

        if is_drinkware_or_cookware and not has_electrical_specs:
            # Overrule any erroneous electrical classification for manual drinkware/cookware
            if "electrical" in industry.lower() or "electronic" in industry.lower():
                industry = "Consumer Goods & Utensils"
            # Strip electrical from reg_domains
            reg_domains = [d for d in reg_domains if "electrical" not in d.lower() and "electronic" not in d.lower()]
            if not reg_domains:
                reg_domains = ["Consumer Goods", "Food Contact & Utensils"]
                domain_reasons["Consumer Goods"] = "Domestic beverage storage/consumption article"
                domain_reasons["Food Contact & Utensils"] = "Food/beverage contact materials and containers"

        # Fallback to plausible domains if empty
        if not reg_domains:
            if any(k in normalized_name.lower() for k in ["shirt", "t-shirt", "garment", "fabric", "textile", "cotton"]):
                reg_domains = ["Textiles & Apparel", "Garments"]
            elif any(k in normalized_name.lower() for k in ["oil", "food", "edible"]):
                reg_domains = ["Food & Agricultural Products", "Food Safety (FSSAI)"]
            elif is_drinkware_or_cookware:
                reg_domains = ["Consumer Goods", "Food Contact & Utensils"]

        # Deduplicate reg_domains preserving order
        unique_reg_domains = []
        for d in reg_domains:
            if d not in unique_reg_domains:
                unique_reg_domains.append(d)
        reg_domains = unique_reg_domains

        # Build deduplicated possible_domains list
        all_domains = []
        if industry != "Not confidently identified":
            all_domains.append(industry)
        for d in reg_domains:
            if d not in all_domains:
                all_domains.append(d)
        possible_domains = all_domains if all_domains else ["Consumer Products"]

        # Inferred product family
        product_family = industry
        if is_drinkware_or_cookware and ("electrical" in product_family.lower() or product_family in ["Not confidently identified", "General Manufacturing"]):
            product_family = "Drinkware & Insulated Containers"

        clarification_req = bool(parsed.get("clarification_required", False))
        clarification_q = parsed.get("clarification_questions") or []

        # Secondary guard: check if product_name itself is just a material
        if self._is_vague_material_input(product_name):
            return self._build_clarification_response(clean_text)

        # Calculate dynamic confidence based on extraction factors (Requirement 45)
        calc_conf = 0.70
        if len(product_name) > 3 and product_name.lower() != clean_text.lower():
            calc_conf += 0.10
        if materials:
            calc_conf += 0.08
        if intended_use and "functional usage" not in intended_use.lower():
            calc_conf += 0.07
        if clarification_req:
            calc_conf -= 0.30
        final_confidence = round(max(0.40, min(0.95, calc_conf)), 2)

        # Build dynamic search terms targeting verified article
        search_terms = [
            f"{normalized_name} Indian Standard",
            f"BIS standard {normalized_name}",
            f"{normalized_name} specification requirements India"
        ]
        if "Food" in industry or any("FSSAI" in d for d in reg_domains):
            search_terms.append(f"{normalized_name} FSSAI standard regulation India")

        # Detect multiple products if present
        multi_detection = self._detect_multi_product(clean_text)

        # Build structured ProductProfile
        profile = self._build_product_profile(
            clean_text=clean_text,
            product_name=product_name,
            industry=industry,
            materials=materials,
            intended_use=intended_use,
            physical_form=physical_form,
            technical_attributes=technical_attributes
        )

        return ProductUnderstanding(
            product_name=product_name,
            normalized_product_name=normalized_name,
            product_description=clean_text,
            product_family=product_family,
            commercial_intent=commercial_intent,
            materials=materials,
            components=components,
            intended_use=intended_use,
            application=application,
            industry_context=industry,
            physical_form=physical_form,
            technical_attributes=technical_attributes,
            regulatory_characteristics={"domains": reg_domains, "domain_reasons": domain_reasons},
            possible_regulatory_domains=reg_domains,
            possible_domains=possible_domains,
            confidence=final_confidence,
            clarification_required=clarification_req,
            clarification_questions=clarification_q,
            search_terms=search_terms,
            product_profile=profile.dict(),
            multi_product_detected=multi_detection.dict() if multi_detection.is_multi_product else None
        )

    def _detect_multi_product(self, text: str) -> MultiProductDetection:
        """Detect multi-product lists in user description (Section 29)"""
        lower = text.lower().strip()
        # Separate primary product description from additional component / material details
        primary_text = re.split(r'additional\s+details\s*:', lower)[0].strip()
        cleaned = re.sub(r'^(?:we\s+manufacture|i\s+manufacture|we\s+make|i\s+make|we\s+produce|we\s+sell)\s*', '', primary_text)
        parts = re.split(r',\s*|\s+and\s+', cleaned)
        valid_items = [p.strip() for p in parts if len(p.strip().split()) >= 1 and len(p.strip()) > 3]

        # Ignore parts that are clearly subcomponents, materials, or accessories rather than distinct finished products
        non_product_indicators = [
            "food-grade", "food contact", "silicone", "gasket", "screw cap", "cap", "liner",
            "lid", "washer", "handle", "coating", "sleeve", "accessory", "packaging", "box"
        ]

        keywords = ["bottle", "cable", "switch", "pipe", "heater", "helmet", "battery", "toy", "t-shirt", "cement", "wire", "oil", "food", "textile", "valve"]
        distinct_found = []
        for item in valid_items:
            # Skip if it is an accessory or component specification
            if any(ind in item for ind in non_product_indicators):
                continue
            for kw in keywords:
                # Disallow matching 'food' in 'food-grade' or 'food contact'
                if kw == "food" and ("food-grade" in item or "food contact" in item or "food safe" in item):
                    continue
                # Whole word / token match for keywords to avoid partial matches
                if re.search(r'\b' + re.escape(kw) + r'\b', item) and not any(re.search(r'\b' + re.escape(kw) + r'\b', existing.lower()) for existing in distinct_found):
                    distinct_found.append(item.title())
                    break

        if len(distinct_found) >= 2:
            return MultiProductDetection(
                is_multi_product=True,
                detected_products=distinct_found,
                message=f"You mentioned manufacturing {len(distinct_found)} distinct products: {', '.join(distinct_found)}. Please choose which one to evaluate first."
            )
        return MultiProductDetection(is_multi_product=False)

    def _build_product_profile(
        self,
        clean_text: str,
        product_name: str,
        industry: str,
        materials: List[str],
        intended_use: str,
        physical_form: str,
        technical_attributes: Dict[str, Any]
    ) -> ProductProfile:
        """Constructs structured product profile with confirmed vs unknown attributes"""
        text_lower = clean_text.lower()
        p_lower = product_name.lower()

        # Insulation
        insulation = None
        if any(k in text_lower for k in ["vacuum insulated", "vacuum flask", "vacuum"]):
            insulation = "vacuum insulated"
        elif any(k in text_lower for k in ["insulated", "thermal"]):
            insulation = "insulated"
        elif "single wall" in text_lower or "single-wall" in text_lower or "uninsulated" in text_lower:
            insulation = "single-wall"

        # Construction
        construction = None
        if "double wall" in text_lower or "double-wall" in text_lower:
            construction = "double-wall"
        elif "single wall" in text_lower or "single-wall" in text_lower:
            construction = "single-wall"

        # Capacity
        capacity = None
        cap_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:ml|l|litre|litres|liter|liters|kg|g))\b', text_lower)
        if cap_match:
            capacity = cap_match.group(1)

        # Voltage
        voltage = None
        volt_match = re.search(r'\b(\d+(?:\.\d+)?\s*(?:kv|v|volts?))\b', text_lower)
        if volt_match:
            voltage = volt_match.group(1)

        # Operating Environment
        environment = None
        if any(k in text_lower for k in ["domestic", "household", "home"]):
            environment = "domestic"
        elif any(k in text_lower for k in ["industrial", "commercial"]):
            environment = "industrial"

        # Conductor
        conductor = None
        if "copper" in text_lower:
            conductor = "copper"
        elif "aluminium" in text_lower or "aluminum" in text_lower:
            conductor = "aluminium"

        # Identify unknown attributes based on domain
        unknowns = []
        is_bottle = any(k in p_lower or k in text_lower for k in ["bottle", "flask", "drinkware", "vessel", "tumbler", "mug"])
        if is_bottle:
            if not insulation:
                unknowns.append("insulation")
            if not construction:
                unknowns.append("construction")
            if not capacity:
                unknowns.append("capacity")
            if not environment:
                unknowns.append("operating_environment")

        is_cable = any(k in p_lower or k in text_lower for k in ["cable", "wire", "conductor"])
        if is_cable:
            if not voltage:
                unknowns.append("voltage_range")
            if not conductor:
                unknowns.append("conductor_material")

        is_garment = any(k in p_lower or k in text_lower for k in ["t-shirt", "shirt", "garment", "apparel"])
        if is_garment:
            if not any(k in text_lower for k in ["knitted", "knit", "woven"]):
                unknowns.append("fabric_construction")
            if not any(k in text_lower for k in ["men", "women", "kids", "unisex"]):
                unknowns.append("demographic_category")

        mat_str = ", ".join(materials) if materials else None

        return ProductProfile(
            product_name=product_name,
            product_category=industry if industry != "Not confidently identified" else None,
            material=mat_str,
            intended_use=intended_use if intended_use and "functional usage" not in intended_use.lower() else None,
            insulation=insulation,
            construction=construction,
            capacity=capacity,
            voltage_rating=voltage,
            conductor_material=conductor,
            operating_environment=environment,
            unknown_attributes=unknowns,
            additional_attributes=technical_attributes or {}
        )

    def _is_vague_material_input(self, text: str) -> bool:
        lower = text.lower().strip()
        for pat in VAGUE_MATERIAL_ONLY_PATTERNS:
            if re.match(pat, lower):
                return True
        words = lower.split()
        if len(words) <= 3 and any(m in lower for m in ["steel", "plastic", "copper", "iron", "rubber", "polymer"]):
            if not any(article in lower for article in [
                "flask", "bottle", "wire", "cable", "pipe", "tube", "fitting",
                "valve", "plate", "sheet", "rebar", "fastener", "screw", "nut", "oil", "film"
            ]):
                return True
        return False

    def _build_clarification_response(self, text: str) -> ProductUnderstanding:
        material = "material"
        for m in ["steel", "plastic", "copper", "iron", "aluminum", "rubber", "glass"]:
            if m in text.lower():
                material = m
                break

        return ProductUnderstanding(
            product_name=f"Unspecified {material.capitalize()} Product",
            normalized_product_name=f"Unspecified {material}",
            product_description=text,
            product_family="Unspecified",
            materials=[material.capitalize()],
            intended_use="Unspecified",
            confidence=0.2,
            clarification_required=True,
            clarification_questions=[
                f"What specific {material} article do you manufacture (e.g. pipes, structural bars, vacuum flasks, utensils, or fasteners)?",
                "What is the intended operational environment (e.g. domestic, high-pressure industrial, food-contact, or electrical)?",
                "What are the relevant dimensions, ratings, or technical grades (e.g. diameter, wall thickness, voltage rating)?",
                "Is the product intended for consumer retail or industrial construction?"
            ]
        )

    def _sanitize_product_name(self, name: str) -> str:
        """Strip conversational and marketing preambles from product name"""
        cleaned = re.sub(
            r'^(?:i\s+want\s+to\s+sell|want\s+to\s+sell|i\s+manufacture|we\s+manufacture|we\s+produce|we\s+make|we\s+are\s+developing|we\s+sell|we\s+import|looking\s+to\s+sell|looking\s+to\s+export|my)\s+',
            '',
            name,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'\s+(?:across\s+india|in\s+india|for\s+domestic\s+use|for\s+household|for\s+commercial|for\s+export|under\s+bis)\b.*$',
            '',
            cleaned,
            flags=re.IGNORECASE
        )
        cleaned = cleaned.strip('.?,! ')
        return cleaned.title() if cleaned else "Unspecified Product"

    def _normalize_name(self, name: str) -> str:
        """Linguistic singularization"""
        n = name.strip()
        lower = n.lower()
        if lower.endswith("ies") and len(lower) > 4:
            return n[:-3] + "y"
        elif lower.endswith("es") and not lower.endswith("sses") and len(lower) > 3:
            return n[:-2]
        elif lower.endswith("s") and not lower.endswith("ss") and len(lower) > 2:
            return n[:-1]
        return n

    def _detect_commercial_intent(self, text: str) -> str:
        lower = text.lower()
        if "sell" in lower or "distribute" in lower:
            return "Sell / Distribute"
        if "import" in lower:
            return "Import"
        if "export" in lower:
            return "Export"
        if "test" in lower:
            return "Testing & Certification"
        return "Manufacture"

    def _fallback_deterministic_parse(self, text: str) -> Dict[str, Any]:
        """Strict deterministic fallback if LLM encounters transient error or JSON parsing fails"""
        p_name = self._sanitize_product_name(text)
        lower = text.lower()
        extracted_materials = []
        for m in ["stainless steel", "steel", "cotton", "pvc", "copper", "aluminum", "plastic", "rubber", "glass", "leather", "polymer", "seaweed", "paper", "wood", "jute", "silk", "wool", "ceramic"]:
            if m in lower and m.title() not in extracted_materials:
                extracted_materials.append(m.title())

        # Also capture hyphenated material compounds like 'seaweed-based'
        based_match = re.search(r'\b([a-zA-Z]+)-based\b', lower)
        if based_match:
            cand = based_match.group(1).title()
            if cand not in extracted_materials and cand.lower() not in ["bio", "plant", "water", "oil"]:
                extracted_materials.append(cand)

        industry = "Consumer Goods & Household"
        if any(k in lower for k in ["cable", "wire", "switch", "motor", "electronic", "battery"]):
            industry = "Electrical & Electronics"
        elif any(k in lower for k in ["t-shirt", "shirt", "garment", "fabric", "textile"]):
            industry = "Textiles & Apparel"
        elif any(k in lower for k in ["oil", "edible", "food", "beverage"]):
            industry = "Food & Agriculture"
        elif any(k in lower for k in ["flask", "bottle", "vessel", "utensil", "cookware"]):
            industry = "Consumer Goods & Household"

        return {
            "product_name": p_name,
            "normalized_name": self._normalize_name(p_name),
            "commercial_intent": self._detect_commercial_intent(text),
            "materials": extracted_materials,
            "intended_use": f"Standard functional use of {p_name}",
            "industry": industry,
            "possible_regulatory_domains": [industry],
            "clarification_required": False,
            "clarification_questions": []
        }
