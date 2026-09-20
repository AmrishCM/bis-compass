import re
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import logging
from app.services.products.product_understanding import ProductUnderstanding

logger = logging.getLogger(__name__)


class Constraint(BaseModel):
    """Base constraint class"""
    field_name: str
    value: Any


class NumericalRangeConstraint(Constraint):
    """Constraint for numerical ranges (min, max)"""
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    unit: Optional[str] = None


class CategoricalConstraint(Constraint):
    """Constraint for categorical values"""
    allowed_values: List[str] = Field(default_factory=list)


class BooleanConstraint(Constraint):
    """Constraint for boolean values"""
    pass


class ExtractedConstraints(BaseModel):
    """Container for all extracted constraints from a product or standard"""
    voltage_range: Optional[NumericalRangeConstraint] = None
    duty_class: Optional[CategoricalConstraint] = None
    material: Optional[CategoricalConstraint] = None
    form_factor: Optional[CategoricalConstraint] = None
    conductor_material: Optional[CategoricalConstraint] = None
    insulation_type: Optional[CategoricalConstraint] = None
    current_rating: Optional[NumericalRangeConstraint] = None
    frequency: Optional[NumericalRangeConstraint] = None
    temperature_range: Optional[NumericalRangeConstraint] = None
    protection_class: Optional[CategoricalConstraint] = None
    # Add more constraint types as needed

class ApplicabilityDecision(BaseModel):
    """
    Structured outcome of evaluating a candidate standard against a product.
    Includes explicit entity relationship type and contradictions to prevent false positives.
    """
    decision: str = Field(description="APPLICABLE, NOT_APPLICABLE, NEEDS_CLARIFICATION, RELATED, or UNVERIFIED")
    score: float = Field(description="Applicability score from 0.0 to 100.0")
    reasons: List[str] = Field(default_factory=list, description="Positive reasons supporting applicability")
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Clauses or scope text citing relevance")
    contradictions: List[str] = Field(default_factory=list, description="Contradictions / exclusions causing rejection")
    missing_information: List[str] = Field(default_factory=list, description="Missing technical details")
    clarification_questions: List[str] = Field(default_factory=list, description="Clarification questions")
    relationship_type: str = Field(default="PRIMARY_PRODUCT_STANDARD", description="PRIMARY_PRODUCT_STANDARD, REFERENCED_STANDARD, TEST_METHOD_STANDARD, MATERIAL_STANDARD, COMPONENT_STANDARD, REGULATORY_DOCUMENT")
    parent_standard: Optional[str] = Field(default=None, description="Standard number of parent standard if referenced")
    failing_constraint: Optional[str] = Field(default=None, description="Details of which constraint failed and why, for EXCLUDED decisions")


class StandardApplicabilityService:
    """
    Open-World Standard Applicability Engine.
    Evaluates whether a candidate standard truly applies to the user's specific product.
    Enforces strict scope boundaries and hard rejections for obvious mismatches.
    """

    def extract_product_constraints(self, product: ProductUnderstanding) -> ExtractedConstraints:
        """Extract structured constraints from product input"""
        constraints = ExtractedConstraints()

        # Extract from product description, name, etc.
        p_desc = (product.product_description or "").lower()
        p_name = (product.product_name or "").lower()
        p_family = (product.product_family or "").lower()
        materials = [m.lower() for m in product.materials]
        reg_chars = product.regulatory_characteristics or {}

        # Extract voltage range: check range patterns first
        range_match = re.search(r'(?:from\s+)?(\d+(?:\.\d+)?)\s*(?:kv|v)\s*(?:up\s*to\s*(?:and\s*including)?|to|-)\s*(\d+(?:\.\d+)?)\s*(?:kv|v)', p_desc + " " + p_name, re.IGNORECASE)
        if range_match:
            min_val = float(range_match.group(1))
            max_val = float(range_match.group(2))
            raw = range_match.group(0).lower()
            if "kv" in raw:
                first_part = raw[:range_match.span(2)[0] - range_match.start()]
                second_part = raw[range_match.span(2)[0] - range_match.start():]
                if "kv" in first_part or ("kv" in second_part and min_val < 100):
                    min_val *= 1000
                if "kv" in second_part or max_val < 100:
                    max_val *= 1000
            constraints.voltage_range = NumericalRangeConstraint(
                field_name="voltage_range",
                value=f"{min_val}V to {max_val}V",
                min_val=min_val,
                max_val=max_val,
                unit="v"
            )
        else:
            voltage_single_patterns = [
                r'working\s*voltages?\s*up\s*to\s*(?:and\s*including)?\s*(\d+(?:\.\d+)?)\s*(?:v|volt|voltage|kv)\b',
                r'up\s*to\s*(?:and\s*including)?\s*(\d+(?:\.\d+)?)\s*(?:v|volt|voltage|kv)\b',
                r'rated\s*(?:for|voltage)?\s*(\d+(?:\.\d+)?)\s*(?:v|volt|voltage|kv)\b',
                r'(\d+(?:\.\d+)?)\s*(?:kv)\b',
                r'(\d+(?:\.\d+)?)\s*(?:v|volt|voltage)\b'
            ]
            for pattern in voltage_single_patterns:
                match = re.search(pattern, p_desc + " " + p_name, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        unit = "kv" if "kv" in match.group(0).lower() else "v"
                        value_in_v = value * 1000 if unit == "kv" else value
                        constraints.voltage_range = NumericalRangeConstraint(
                            field_name="voltage_range",
                            value=f"up to {int(value_in_v)}V",
                            min_val=0.0,
                            max_val=value_in_v,
                            unit="v"
                        )
                        break
                    except ValueError:
                        pass

        # Extract duty class
        duty_class_keywords = {
            'light-duty': ['light duty', 'light-duty', 'light duty cables'],
            'medium-duty': ['medium duty', 'medium-duty'],
            'heavy-duty': ['heavy duty', 'heavy-duty', 'heavy duty cables', 'industrial wiring', 'power supply'],
            'extra-heavy-duty': ['extra heavy duty', 'extra-heavy-duty']
        }

        for duty_class, keywords in duty_class_keywords.items():
            if any(keyword in p_desc or keyword in p_name for keyword in keywords):
                constraints.duty_class = CategoricalConstraint(
                    field_name="duty_class",
                    value=duty_class,
                    allowed_values=[duty_class]
                )
                break

        # Extract material
        material_keywords = [
            'pvc', 'polyvinyl chloride', 'xlpe', 'cross-linked polyethylene',
            'rubber', 'eping', 'copper', 'aluminium', 'aluminum', 'steel',
            'ss', 'stainless steel', 'cs', 'carbon steel'
        ]

        found_materials = []
        for mat in material_keywords:
            if mat in p_desc or mat in p_name:
                found_materials.append(mat)

        found_materials.extend(materials)

        if found_materials:
            constraints.material = CategoricalConstraint(
                field_name="material",
                value=", ".join(found_materials),
                allowed_values=list(set(found_materials))
            )

        # Extract form factor
        if "ribbon" in p_desc or "ribbon" in p_name:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="flat ribbon cable",
                allowed_values=["flat ribbon cable", "ribbon cable", "ribbon"]
            )
        elif "switchgear" in p_desc or "circuit breaker" in p_desc:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="switchgear",
                allowed_values=["switchgear", "circuit breaker"]
            )
        elif "lamp" in p_desc or "bulb" in p_desc or "led" in p_desc:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="lamp",
                allowed_values=["lamp", "bulb", "lighting"]
            )
        elif "cooker" in p_desc:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="pressure cooker",
                allowed_values=["pressure cooker", "cooker"]
            )
        elif "flask" in p_desc or "bottle" in p_desc:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="bottle/flask",
                allowed_values=["bottle/flask", "bottle", "flask"]
            )
        else:
            form_factor_keywords = [
                'cable', 'wire', 'conductor', 'tape', 'strip', 'tube', 'pipe',
                'sheet', 'plate', 'rod', 'bar', 'profile'
            ]
            for ff in form_factor_keywords:
                if ff in p_desc or ff in p_name:
                    constraints.form_factor = CategoricalConstraint(
                        field_name="form_factor",
                        value=ff,
                        allowed_values=[ff]
                    )
                    break

        # Extract conductor material
        conductor_keywords = ['copper', 'aluminium', 'aluminum', 'acsr', 'alloy']
        for cond in conductor_keywords:
            if cond in p_desc or cond in p_name:
                constraints.conductor_material = CategoricalConstraint(
                    field_name="conductor_material",
                    value=cond,
                    allowed_values=[cond]
                )
                break

        # Extract insulation type
        insulation_keywords = ['pvc', 'xlpe', 'eping', 'rubber', 'polymer', 'thermoplastic']
        for ins in insulation_keywords:
            if ins in p_desc or ins in p_name:
                constraints.insulation_type = CategoricalConstraint(
                    field_name="insulation_type",
                    value=ins,
                    allowed_values=[ins]
                )
                break

        return constraints

    def extract_standard_constraints(self, standard: Dict[str, Any], retrieved_clauses: List[Dict[str, Any]] = None) -> ExtractedConstraints:
        """Extract structured constraints from standard's scope clause using NLP/pattern matching"""
        constraints = ExtractedConstraints()

        standard_number = standard.get("standard_number", "")
        title = standard.get("title", "")
        scope = standard.get("scope", "")
        clauses = retrieved_clauses or []

        # Combine all text from standard
        std_text = f"{standard_number} {title} {scope}".lower()
        for c in clauses[:10]:
            std_text += " " + c.get("text", "").lower() + " " + c.get("heading", "").lower()

        # Check explicit voltage range patterns FIRST
        range_match = re.search(r'(?:from\s+)?(\d+(?:\.\d+)?)\s*(?:kv|v)\s*(?:up\s*to\s*(?:and\s*including)?|to|-)\s*(\d+(?:\.\d+)?)\s*(?:kv|v)', std_text, re.IGNORECASE)
        if not range_match:
            range_match = re.search(r'voltage\s*range\s*:?\s*(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:v|volt|voltage|kv)', std_text, re.IGNORECASE)

        if range_match:
            try:
                min_v = float(range_match.group(1))
                max_v = float(range_match.group(2))
                raw = range_match.group(0).lower()
                first_part = raw[:range_match.span(2)[0] - range_match.start()]
                second_part = raw[range_match.span(2)[0] - range_match.start():]
                if "kv" in first_part or ("kv" in second_part and min_v < 100):
                    min_v *= 1000
                if "kv" in second_part or max_v < 100:
                    max_v *= 1000
                constraints.voltage_range = NumericalRangeConstraint(
                    field_name="voltage_range",
                    value=f"{min_v/1000:.1f}kV to {max_v/1000:.1f}kV" if min_v >= 1000 else f"{int(min_v)}V to {int(max_v)}V",
                    min_val=min_v,
                    max_val=max_v,
                    unit="v"
                )
            except (ValueError, IndexError):
                pass
        else:
            voltage_single_patterns = [
                r'working\s*voltages?\s*up\s*to\s*(?:and\s*including)?\s*(\d+(?:\.\d+)?)\s*(?:v|volt|voltage|kv)\b',
                r'up\s*to\s*(?:and\s*including)?\s*(\d+(?:\.\d+)?)\s*(?:v|volt|voltage|kv)\b',
                r'rated\s*(?:for|voltage)?\s*(\d+(?:\.\d+)?)\s*(?:v|volt|voltage|kv)\b',
                r'(\d+(?:\.\d+)?)\s*(?:kv)\b',
                r'(\d+(?:\.\d+)?)\s*(?:v|volt|voltage)\b'
            ]
            for pattern in voltage_single_patterns:
                match = re.search(pattern, std_text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        unit = "kv" if "kv" in match.group(0).lower() else "v"
                        value_in_v = value * 1000 if unit == "kv" else value
                        constraints.voltage_range = NumericalRangeConstraint(
                            field_name="voltage_range",
                            value=f"up to {int(value_in_v)}V",
                            min_val=0.0,
                            max_val=value_in_v,
                            unit="v"
                        )
                        break
                    except (ValueError, IndexError):
                        pass

        # Extract duty class
        duty_class_patterns = [
            r'(light[-\s]?duty|medium[-\s]?duty|heavy[-\s]?duty|extra[-\s]?heavy[-\s]?duty)',
            r'duty\s*class\s*:?\s*(light|medium|heavy|extra\s*heavy)'
        ]

        for pattern in duty_class_patterns:
            match = re.search(pattern, std_text, re.IGNORECASE)
            if match:
                duty_class_raw = match.group(1).lower().replace(" ", "-")
                if "light" in duty_class_raw:
                    duty_class = "light-duty"
                elif "medium" in duty_class_raw:
                    duty_class = "medium-duty"
                elif "heavy" in duty_class_raw:
                    duty_class = "extra-heavy-duty" if "extra" in duty_class_raw else "heavy-duty"
                else:
                    duty_class = duty_class_raw

                constraints.duty_class = CategoricalConstraint(
                    field_name="duty_class",
                    value=duty_class,
                    allowed_values=[duty_class]
                )
                break

        # Extract material
        material_patterns = [
            r'(pvc|polyvinyl\s*chloride|xlpe|cross[-\s]?linked\s*polyethylene|eping|rubber)',
            r'(copper|aluminium|aluminum)',
            r'(steel|stainless\s*steel|carbon\s*steel)'
        ]

        found_materials = []
        for pattern in material_patterns:
            matches = re.findall(pattern, std_text, re.IGNORECASE)
            for match in matches:
                mat = next((m for m in match if m), "").lower() if isinstance(match, tuple) else match.lower()
                if mat:
                    if "polyvinyl chloride" in mat or "pvc" in mat:
                        mat = "pvc"
                    elif "cross-linked" in mat or "xlpe" in mat:
                        mat = "xlpe"
                    elif "stainless" in mat:
                        mat = "stainless steel"
                    elif "carbon" in mat:
                        mat = "carbon steel"
                    found_materials.append(mat)

        if found_materials:
            constraints.material = CategoricalConstraint(
                field_name="material",
                value=", ".join(list(set(found_materials))),
                allowed_values=list(set(found_materials))
            )

        # Extract form factor
        if "ribbon cable" in std_text or "ribbon" in title.lower():
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="flat ribbon cable",
                allowed_values=["flat ribbon cable", "ribbon cable", "ribbon"]
            )
        elif "switchgear" in std_text or "circuit-breaker" in std_text:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="switchgear",
                allowed_values=["switchgear", "circuit breaker"]
            )
        elif "pressure cooker" in std_text:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="pressure cooker",
                allowed_values=["pressure cooker", "cooker"]
            )
        elif "vacuum flask" in std_text or "insulated flask" in std_text:
            constraints.form_factor = CategoricalConstraint(
                field_name="form_factor",
                value="vacuum flask",
                allowed_values=["vacuum flask", "insulated bottle", "flask", "bottle"]
            )
        else:
            form_factor_patterns = [
                r'\b(cable|wire|conductor|tape|strip|tube|pipe|sheet|plate|rod|bar|profile)\b'
            ]
            for pattern in form_factor_patterns:
                match = re.search(pattern, std_text)
                if match:
                    ff = match.group(1).lower()
                    constraints.form_factor = CategoricalConstraint(
                        field_name="form_factor",
                        value=ff,
                        allowed_values=[ff]
                    )
                    break

        # Extract conductor material
        conductor_patterns = [
            r'\b(copper|aluminium|aluminum|acsr|alloy)\b'
        ]
        for pattern in conductor_patterns:
            match = re.search(pattern, std_text, re.IGNORECASE)
            if match:
                cond = match.group(1).lower()
                constraints.conductor_material = CategoricalConstraint(
                    field_name="conductor_material",
                    value=cond,
                    allowed_values=[cond]
                )
                break

        # Extract insulation type
        insulation_patterns = [
            r'\b(pvc|xlpe|eping|rubber|polymer|thermoplastic)\b'
        ]
        for pattern in insulation_patterns:
            match = re.search(pattern, std_text, re.IGNORECASE)
            if match:
                ins = match.group(1).lower()
                constraints.insulation_type = CategoricalConstraint(
                    field_name="insulation_type",
                    value=ins,
                    allowed_values=[ins]
                )
                break

        return constraints

    def compare_constraints(self, product_constraints: ExtractedConstraints, standard_constraints: ExtractedConstraints) -> tuple[bool, Optional[str]]:
        """
        Compare constraints field-by-field.
        Returns (is_compatible, failing_constraint_reason)
        """
        # 1. Voltage Range Disjoint / Mismatch Check
        if product_constraints.voltage_range and standard_constraints.voltage_range:
            p_min = product_constraints.voltage_range.min_val if product_constraints.voltage_range.min_val is not None else 0.0
            p_max = product_constraints.voltage_range.max_val
            s_min = standard_constraints.voltage_range.min_val if standard_constraints.voltage_range.min_val is not None else 0.0
            s_max = standard_constraints.voltage_range.max_val

            # Disjoint check: standard minimum is strictly higher than product maximum
            if p_max is not None and s_min > p_max:
                return False, f"Voltage mismatch: product specifies up to {int(p_max)}V, but standard scope requires disjoint range {standard_constraints.voltage_range.value}"

            # Disjoint check: product minimum is strictly higher than standard maximum
            if s_max is not None and p_min > s_max:
                return False, f"Voltage mismatch: product requires minimum {int(p_min)}V, but standard maximum rating is {int(s_max)}V"

            # Containment check: product maximum exceeds standard maximum
            if p_max is not None and s_max is not None and p_max > s_max:
                return False, f"Voltage mismatch: product specifies {int(p_max)}V which exceeds standard maximum rating of {int(s_max)}V"

        # 2. Form Factor Mismatch Check
        if standard_constraints.form_factor:
            s_ff = standard_constraints.form_factor.value
            p_ff = product_constraints.form_factor.value if product_constraints.form_factor else ""
            if s_ff in ["flat ribbon cable", "ribbon cable", "ribbon"] and "ribbon" not in p_ff:
                return False, "Form factor mismatch: standard IS 14521 explicitly covers flat ribbon cables for electronic equipment, which does not match general electric cables"
            if s_ff == "switchgear" and "switchgear" not in p_ff and "circuit breaker" not in p_ff:
                return False, "Form factor mismatch: standard covers electrical switchgear and circuit breakers"

        # 3. Duty Class Mismatch Check
        if standard_constraints.duty_class:
            s_duty = standard_constraints.duty_class.value
            p_duty = product_constraints.duty_class.value if product_constraints.duty_class else ""
            if s_duty == "light-duty" and ("heavy" in p_duty or "power" in p_duty or "industrial" in p_duty):
                return False, "Duty class mismatch: standard is restricted to light duty cables, while product requires power supply/industrial wiring"

        # 4. Conductor Material Check
        if product_constraints.conductor_material and standard_constraints.conductor_material:
            if not self._is_categorical_subset(product_constraints.conductor_material, standard_constraints.conductor_material):
                return False, f"Conductor material mismatch: product requires {product_constraints.conductor_material.value} but standard specifies {standard_constraints.conductor_material.value}"

        # 5. Insulation Type Check
        if product_constraints.insulation_type and standard_constraints.insulation_type:
            if not self._is_categorical_subset(product_constraints.insulation_type, standard_constraints.insulation_type):
                return False, f"Insulation type mismatch: product requires {product_constraints.insulation_type.value} but standard specifies {standard_constraints.insulation_type.value}"

        return True, None

    def _is_subset_range(self, product_range: NumericalRangeConstraint, standard_range: NumericalRangeConstraint) -> bool:
        """Check if product range is subset of standard range"""
        # If either range is missing min/max, we can't do precise comparison
        # In that case, we'll be conservative and assume it might be compatible
        if product_range.min_val is None or product_range.max_val is None:
            return True  # Assume compatible if product range not fully specified

        if standard_range.min_val is None or standard_range.max_val is None:
            return False  # Assume incompatible if standard range not fully specified

        return (product_range.min_val >= standard_range.min_val and
                product_range.max_val <= standard_range.max_val)

    def _is_categorical_subset(self, product_cat: CategoricalConstraint, standard_cat: CategoricalConstraint) -> bool:
        """Check if product categorical value is allowed by standard"""
        # If standard doesn't specify allowed values, assume all values allowed
        if not standard_cat.allowed_values:
            return True

        # Check if product value is in standard's allowed values
        return product_cat.value in standard_cat.allowed_values

    def evaluate_applicability(
        self,
        product: ProductUnderstanding,
        standard: Dict[str, Any],
        retrieved_clauses: Optional[List[Dict[str, Any]]] = None
    ) -> ApplicabilityDecision:
        """
        Evaluate candidate standard against product identity, scope, application, and regulatory traits.
        Uses two-pass constraint-based applicability matching to eliminate false positives.
        """
        # First Pass - Constraint Extraction
        product_constraints = self.extract_product_constraints(product)
        standard_constraints = self.extract_standard_constraints(standard, retrieved_clauses)

        # Second Pass - Field-by-Field Comparison
        is_compatible, failing_reason = self.compare_constraints(product_constraints, standard_constraints)

        # If constraints are not compatible, return NOT_APPLICABLE with failing constraint
        if not is_compatible:
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=[failing_reason] if failing_reason else ["Constraint mismatch"],
                missing_information=[],
                failing_constraint=failing_reason
            )

        # If constraints are compatible, proceed with existing logic
        standard_number = standard.get("standard_number", "")
        title = standard.get("title", "")
        scope = standard.get("scope", "")
        clauses = retrieved_clauses or []

        reasons = []
        contradictions = []
        supporting_evidence = []
        missing_info = []

        std_text = f"{standard_number} {title} {scope}".lower()
        for c in clauses[:5]:
            std_text += " " + c.get("text", "").lower() + " " + c.get("heading", "").lower()

        # Extract product signals
        p_name = product.product_name.lower()
        p_family = (product.product_family or "").lower()
        p_desc = (product.product_description or "").lower()
        materials = [m.lower() for m in product.materials]
        reg_chars = product.regulatory_characteristics or {}
        std_title = title or ""
        std_title_lower = std_title.lower()
        std_scope = scope or ""
        std_scope_lower = std_scope.lower()

        # ---------------------------------------------------------
        # STEP 0: TITLE & ENTITY RELATIONSHIP RESOLUTION (Section 27 & 28)
        # ---------------------------------------------------------

        # 0.1 Title Verification Gate
        if not title or title.strip() == "" or "unknown" in title.lower():
            contradictions.append(
                f"Candidate standard {standard_number} does not have an official verified title extracted from retrieved source documents."
            )
            return ApplicabilityDecision(
                decision="UNVERIFIED",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=["Verified standard title"],
                relationship_type="PRIMARY_PRODUCT_STANDARD"
            )

        # 0.2 Entity Resolution: Distinguish Primary Product Standards from Material / Test / Component Standards
        is_test_method = any(k in std_title_lower for k in [
            "method of test", "methods of test", "code of practice for testing",
            "test procedures", "determination of", "guidelines for testing",
            "recommended current ratings", "current ratings for cables"
        ])
        is_material_standard = any(k in std_title_lower for k in [
            "steel plates", "sheet and strip", "plates, sheet and strip", "sheets, strips and plates",
            "sheets and strips", "sheets, strips", "low nickel austenitic", "ingot", "billet",
            "raw material", "alloy sheets", "resins", "yarn for", "grey iron casting", "pig iron",
            "copper rod", "aluminum foil for", "chemical composition"
        ])
        is_component_standard = any(k in std_title_lower for k in [
            "plug and socket", "plugs, socket", "gasket", "sealing ring", "fasteners", "screw threads", "washers"
        ]) and not any(k in p_desc for k in ["plug", "socket", "gasket", "seal", "fastener"])

        # If it's a material or test standard, check if it's referenced/supporting
        if is_material_standard:
            has_compat_material = any(m in std_title_lower or m in std_text for m in materials) or any(k in std_title_lower for k in ["stainless steel", "steel", "polymer", "plastic", "copper", "cotton"])
            if has_compat_material:
                return ApplicabilityDecision(
                    decision="RELATED",
                    score=55.0,
                    reasons=[f"Referenced Material Standard: {title}. Specifies constituent material grade/composition."],
                    supporting_evidence=clauses[:2],
                    contradictions=[],
                    missing_information=[],
                    relationship_type="MATERIAL_STANDARD"
                )
            else:
                contradictions.append(f"Standard {standard_number} is a raw material specification not matching product material.")
                return ApplicabilityDecision(
                    decision="NOT_APPLICABLE",
                    score=0.0,
                    reasons=[],
                    supporting_evidence=[],
                    contradictions=contradictions,
                    missing_information=[],
                    relationship_type="MATERIAL_STANDARD",
                    failing_constraint="Standard is a raw material specification not matching product material"
                )

        if is_test_method:
            return ApplicabilityDecision(
                decision="RELATED",
                score=50.0,
                reasons=[f"Referenced Test Method / Guideline Standard: {title}."],
                supporting_evidence=clauses[:2],
                contradictions=[],
                missing_information=[],
                relationship_type="TEST_METHOD_STANDARD",
                failing_constraint="Standard is a test method or engineering guideline (e.g. current rating recommendation), not a primary cable manufacturing specification"
            )

        if is_component_standard:
            return ApplicabilityDecision(
                decision="RELATED",
                score=45.0,
                reasons=[f"Referenced Component Standard: {title}."],
                supporting_evidence=clauses[:2],
                contradictions=[],
                missing_information=[],
                relationship_type="COMPONENT_STANDARD",
                failing_constraint="Standard is a component specification, not a primary product standard"
            )

        # 0.3 Specialized Form Factor Guard (e.g. Ribbon Cable IS 14521 vs General Electric Cables)
        if "ribbon" in std_title_lower and not any(k in p_desc for k in ["ribbon", "flat ribbon"]):
            contradictions.append(
                f"Candidate standard {standard_number} ({title}) explicitly specifies flat ribbon cables for electronic equipment, which does not match general electric cables."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[],
                relationship_type="PRIMARY_PRODUCT_STANDARD",
                failing_constraint="Form factor mismatch: standard IS 14521 explicitly covers flat ribbon cables for electronic equipment, which does not match general electric cables"
            )

        # 1.1 Food / Edible Substance vs Electrical Equipment / Industrial Hardware
        is_food_product = (
            "food" in p_family or "food" in (product.industry_context or "").lower() or
            any(k in p_name for k in ["oil", "food", "tea", "coffee", "grain", "wheat", "rice", "spice", "edible", "snack", "groundnut"]) or
            any("fssai" in d.lower() for d in (product.possible_regulatory_domains or []))
        )
        is_hardware_standard = any(k in std_title_lower or k in std_text for k in [
            "fence energizer", "electrical", "electric", "heating appliance", "cable", "wire", "battery",
            "transformer", "switchgear", "circuit breaker", "rebar", "structural steel", "cement"
        ])
        if is_food_product and is_hardware_standard:
            contradictions.append(
                f"Product '{product.product_name}' is an agricultural/food substance, whereas standard {standard_number} ({title}) strictly governs electrical equipment or industrial hardware."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[],
                failing_constraint="Domain mismatch: product is agricultural/food substance, standard covers electrical/hardware"
            )

        # 1.2 Electrical vs Non-Electrical Hard Mismatch
        is_standard_electrical = any(k in std_title_lower for k in [
            "cables", "cable", "wires", "water heater", "heating appliances", "appliances",
            "plugs", "socket", "battery", "batteries", "cells", "lamp", "luminaire", "electronic"
        ])
        is_product_electrical = reg_chars.get("electrical", False) or any(k in p_desc for k in [
            "electric", "electrical", "battery", "power", "volt", "watt", "wire", "cable", "sensor"
        ])
        is_passive_product = any(k in p_desc for k in [
            "vacuum flask", "flask", "bottle", "t-shirt", "shirt", "garment",
            "packaging film", "tray", "utensil", "cookware", "cement", "oil"
        ])

        if is_standard_electrical and is_passive_product and not is_product_electrical:
            contradictions.append(
                f"Candidate standard {standard_number} strictly covers powered electrical equipment, whereas '{product.product_name}' is a non-electrical passive article."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[],
                failing_constraint=f"Domain mismatch: product is a non-electrical article, but standard {standard_number} strictly covers electrical equipment"
            )

        # 1.2 Apparel / Garment vs Industrial Hardware / Cables / Chemicals
        is_apparel_product = any(k in p_desc for k in ["t-shirt", "shirt", "garment", "clothing", "dress", "trouser", "apparel"])
        if is_apparel_product:
            is_apparel_standard = any(k in std_title_lower or k in std_text for k in [
                "textile", "garment", "apparel", "fabric", "clothing", "shirt", "t-shirt", "knitted", "hosiery", "wear", "cotton"
            ])
            if not is_apparel_standard:
                contradictions.append(
                    f"Product '{product.product_name}' is an apparel/clothing article, but {standard_number} ({title}) governs unrelated industrial hardware / equipment."
                )
                return ApplicabilityDecision(
                    decision="NOT_APPLICABLE",
                    score=0.0,
                    reasons=[],
                    supporting_evidence=[],
                    contradictions=contradictions,
                    missing_information=[],
                    failing_constraint=f"Product '{product.product_name}' is an apparel/clothing article, but {standard_number} ({title}) governs unrelated industrial hardware / equipment."
                )

        # 1.3 Vacuum Flask vs Liquid Water Heaters (The classic false positive)
        is_flask = any(k in p_desc for k in ["vacuum flask", "flask", "insulated bottle", "thermal flask"])
        if is_flask and any(k in std_text for k in ["water heater", "geyser", "immersion", "liquid heating appliance"]):
            contradictions.append(
                f"Standard {standard_number} applies to powered liquid heating appliances (geysers/water heaters), whereas '{product.product_name}' is an unpowered thermal storage vessel."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[]
            )

        # 1.4 Water Heater vs Vacuum Flasks (Reciprocal)
        is_heater = any(k in p_desc for k in ["water heater", "geyser", "immersion heater", "liquid heater"])
        if is_heater and any(k in std_title_lower for k in ["vacuum flasks", "insulated flasks", "cookware", "utensil"]):
            contradictions.append(
                f"Standard {standard_number} ({title}) specifies unpowered storage flasks, whereas '{product.product_name}' is a powered water heating appliance."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[]
            )

        # 1.5 Packaged Drinking Water vs Physical Storage Hardware
        is_drinking_water = any(k in p_desc for k in ["drinking water", "mineral water", "potable water"]) and not any(k in p_desc for k in ["purifier", "ro system"])
        if is_drinking_water and any(k in std_title_lower for k in ["vacuum flasks", "insulated flasks", "cookware", "cable"]):
            contradictions.append(
                f"Standard {standard_number} ({title}) specifies physical storage containers/hardware, whereas '{product.product_name}' is potable water."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[]
            )

        # 1.6 Cable vs Bottles / Utensils
        if ("cable" in std_title_lower or "wire" in std_title_lower) and not any(k in p_desc for k in ["cable", "wire", "cord", "conductor", "lead"]):
            contradictions.append(
                f"Standard {standard_number} is an electrical cable/wire specification, which does not apply to '{product.product_name}'."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[]
            )

        # 1.7 Metallic vs Plastic Container Mismatch (e.g. Plastic bottle standard vs Stainless steel bottle)
        is_metal_product = any(k in m for m in materials for k in ["steel", "stainless", "copper", "aluminium", "aluminum", "brass", "metal"]) or "steel" in p_name or "stainless" in p_name
        is_plastic_product = any(k in m for m in materials for k in ["plastic", "polymer", "pet", "polyethylene", "pvc"]) or "plastic" in p_name
        is_plastic_standard = any(k in std_title_lower for k in ["plastic bottles", "plastic container", "plastics", "polymer", "polyethylene"])
        is_metal_standard = any(k in std_title_lower for k in ["stainless steel", "copper", "aluminium", "metallic"])

        if is_metal_product and is_plastic_standard and not is_plastic_product:
            contradictions.append(
                f"Candidate standard {standard_number} ({title}) strictly covers plastic containers, whereas product material is metallic ({', '.join(product.materials)})."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[]
            )

        if is_plastic_product and is_metal_standard and not is_metal_product:
            contradictions.append(
                f"Candidate standard {standard_number} ({title}) strictly covers metallic/steel articles, whereas product material is plastic ({', '.join(product.materials)})."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=0.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=[]
            )

        # 1.8 Material-Only False Match Suppression
        has_material_mention = any(m in std_text for m in materials) or any(
            any(tok in std_text for tok in re.findall(r'\w+', m) if len(tok) > 2) for m in materials
        )
        has_product_identity_mention = (
            any(w in std_text for w in re.findall(r'\w+', p_name) if len(w) > 3 and w not in ["stainless", "steel", "copper", "plastic", "domestic", "custom"]) or
            any(w in std_text for w in re.findall(r'\w+', p_family) if len(w) > 3 and w not in ["manufactured", "product", "general"])
        )

        if has_material_mention and not has_product_identity_mention:
            contradictions.append(
                f"Candidate standard mentions compatible material, but does not govern the product identity or functional scope of '{product.product_name}'."
            )
            return ApplicabilityDecision(
                decision="NOT_APPLICABLE",
                score=15.0,
                reasons=[],
                supporting_evidence=[],
                contradictions=contradictions,
                missing_information=["Product identity not in standard scope"]
            )

        # ---------------------------------------------------------
        # STEP 2: POSITIVE APPLICABILITY SCORING
        # ---------------------------------------------------------
        score = 0.0

        # A. Direct Search Term Hit (up to 35 pts)
        for term in product.search_terms:
            t_tokens = [w for w in re.findall(r'\w+', term.lower()) if len(w) > 2]
            if t_tokens:
                match_ratio = sum(1 for tok in t_tokens if tok in std_text) / len(t_tokens)
                if match_ratio >= 0.70:
                    score += 35.0
                    reasons.append(f"Standard title and scope match search phrase '{term}'")
                    break

        # B. Product Identity & Family Compatibility (30 pts)
        if (any(k in p_name or k in p_family for k in ["flask", "bottle", "drinkware", "vessel", "water bottle"]) and 
            any(k in std_text for k in ["flask", "bottle", "drinkware", "potable water bottle", "vacuum flask"])):
            score += 30.0
            reasons.append("Product identity (drinking bottle / vacuum insulated flask) matches standard scope")
        elif ("heater" in p_name or "heater" in p_family) and ("water heater" in std_text or "liquid heating" in std_text):
            score += 30.0
            reasons.append("Product identity (water heater) matches appliance scope")
        elif ("cable" in p_name or "cable" in p_family) and ("cable" in std_text or "conductor" in std_text):
            score += 30.0
            reasons.append("Product identity (insulated cable) matches cable standard scope")
        elif ("battery" in p_name or "battery" in p_family or "cell" in p_name) and ("battery" in std_text or "cell" in std_text):
            score += 30.0
            reasons.append("Product identity (secondary battery) matches CRS battery scope")
        elif ("water" in p_name and ("drinking" in p_name or "mineral" in p_name)) and ("drinking water" in std_text or "potable water" in std_text) and not any(k in std_title_lower for k in ["bottle", "container", "packaging"]):
            score += 30.0
            reasons.append("Product identity (packaged water) matches potable water standard scope")
        elif ("t-shirt" in p_name or "shirt" in p_name or "garment" in p_name or "apparel" in p_name) and ("shirt" in std_text or "t-shirt" in std_text):
            score += 30.0
            reasons.append("Product identity (T-shirt / shirt) matches Indian Standard scope")
        elif any(k in p_name or k in p_family for k in ["footwear", "shoe", "boot", "sandal"]) and any(k in std_text for k in ["footwear", "shoes", "boots"]):
            score += 30.0
            reasons.append("Product identity (footwear) matches Indian Standard scope")
        elif any(k in p_name or k in p_family for k in ["cement", "concrete"]) and "cement" in std_text:
            score += 30.0
            reasons.append("Product identity (cement) matches Indian Standard scope")
        elif any(k in p_name or k in p_family for k in ["steel bar", "rebar", "deformed steel"]) and any(k in std_text for k in ["steel bar", "concrete reinforcement", "deformed steel"]):
            score += 30.0
            reasons.append("Product identity (reinforcing steel) matches Indian Standard scope")
        elif any(k in p_name or k in p_family for k in ["toy", "play"]) and "toy" in std_text:
            score += 30.0
            reasons.append("Product identity (toy safety) matches Indian Standard scope")
        else:
            tokens = [w for w in re.findall(r'\w+', p_name) if len(w) > 3 and w not in ["stainless", "steel", "domestic", "general", "custom"]]
            if tokens:
                matches = sum(1 for t in tokens if t in std_text)
                if matches > 0:
                    score += 25.0 * (matches / len(tokens))
                    reasons.append("Functional token alignment with standard scope")

        # C. Material & Construction Compatibility (15 pts)
        if materials:
            for mat in materials:
                mat_tokens = [w for w in re.findall(r'\w+', mat.lower()) if len(w) > 2]
                if any(tok in std_text for tok in mat_tokens):
                    score += 15.0
                    reasons.append(f"Material specification ({mat}) is compatible with standard requirements")
                    break

        # D. Application / Intended Use Compatibility (15 pts)
        if product.intended_use:
            p_use_lower = product.intended_use.lower()
            if any(k in std_text for k in ["domestic", "household", "home"]) and any(k in p_use_lower for k in ["domestic", "household", "home"]):
                score += 15.0
                reasons.append("Intended domestic / household application matches standard field of application")
            elif any(k in std_text for k in ["industrial", "commercial"]) and any(k in p_use_lower for k in ["industrial", "commercial"]):
                score += 15.0
                reasons.append("Industrial / commercial use classification matches standard conditions")

        # Collect evidence clauses
        for c in clauses:
            c_text = (c.get("text", "") + " " + c.get("heading", "")).lower()
            if any(term in c_text for term in product.search_terms) or any(m in c_text for m in materials):
                supporting_evidence.append({
                    "clause_number": c.get("clause_number", ""),
                    "heading": c.get("heading", ""),
                    "text": c.get("text", "")[:280] + ("..." if len(c.get("text", "")) > 280 else ""),
                    "page": c.get("page")
                })

        # Scope Attribute Verification Gate (Requirement 5 & 20: Prevent over-eager applicability)
        # E.g. IS 4375 specifies "men's cotton knitted sports shirt/T-shirt"
        if "shirt" in std_title_lower or "t-shirt" in std_title_lower or "garment" in std_title_lower:
            # Check if standard is shirting fabric rather than ready-made garment
            if "t-shirt" in p_desc and "shirting" in std_title_lower and "t-shirt" not in std_title_lower:
                missing_info.append("Standard specifies shirting fabric piece-goods, not finished knitted T-shirts. Clarify whether inquiry covers raw shirting fabric or ready-made garments.")
                return ApplicabilityDecision(
                    decision="NEEDS_CLARIFICATION",
                    score=50.0,
                    reasons=reasons or ["Related cotton textile standard (shirting fabric)"],
                    supporting_evidence=supporting_evidence[:4],
                    contradictions=[],
                    missing_information=missing_info
                )

            missing_apparel_attrs = []
            if "men" in std_title_lower and not any(k in p_desc for k in ["men", "mens", "male", "gent"]):
                missing_apparel_attrs.append("Garment demographic category (men's vs women's / unisex)")
            if "knitted" in std_title_lower and not any(k in p_desc for k in ["knit", "knitted", "single jersey", "interlock"]):
                missing_apparel_attrs.append("Fabric construction method (knitted vs woven)")
            if "sports" in std_title_lower and not any(k in p_desc for k in ["sport", "sports", "athletic", "activewear"]):
                missing_apparel_attrs.append("Product classification (sports shirt vs general casual apparel)")

            if missing_apparel_attrs and score >= 25.0:
                missing_info.extend(missing_apparel_attrs)
                return ApplicabilityDecision(
                    decision="NEEDS_CLARIFICATION",
                    score=round(min(score, 65.0), 1),
                    reasons=reasons or ["Product type matches standard domain (cotton T-shirt)"],
                    supporting_evidence=supporting_evidence[:4],
                    contradictions=[],
                    missing_information=missing_info
                )

        # Decision threshold (45 pts minimum with zero contradictions)
        if score >= 45.0 and len(contradictions) == 0:
            decision = "APPLICABLE"
        elif score >= 25.0:
            decision = "NEEDS_CLARIFICATION"
            # Grounded missing information based on standard domain (Bug 3 fix)
            std_num = standard_number
            if any(k in std_title_lower or k in std_scope_lower for k in ["bottle", "flask", "vessel", "container", "drinkware"]):
                if "vacuum" in std_title_lower or "insulated" in std_title_lower:
                    missing_info.append(f"{std_num} scope distinction: Single-wall vs vacuum double-wall insulation")
                if "domestic" in std_title_lower or "household" in std_title_lower:
                    missing_info.append(f"{std_num} scope requirement: Domestic/household drinking use vs industrial container")
                if not missing_info:
                    missing_info.append(f"{std_num} operational specification: Nominal volume capacity and closure seal type")
            elif any(k in std_title_lower or k in std_scope_lower for k in ["cable", "wire", "conductor"]):
                missing_info.append(f"{std_num} voltage rating and conductor core configuration")
            elif any(k in std_title_lower or k in std_scope_lower for k in ["oil", "edible", "fat"]):
                missing_info.append(f"{std_num} refining grade (raw expressed vs refined grade) and packaging format")
            elif std_scope and len(std_scope) > 10:
                missing_info.append(f"{std_num} scope criteria: Specific sub-type or grade defined in scope ({std_scope[:80]}...)")
            else:
                missing_info.append(f"{std_num} applicability criteria: Intended operating parameters and grade conforming to {std_title[:60]}")
        else:
            decision = "NOT_APPLICABLE"
            contradictions.append(f"Score ({int(score)}/100) below authoritative applicability threshold")

        return ApplicabilityDecision(
            decision=decision,
            score=min(100.0, round(score, 1)),
            reasons=reasons,
            supporting_evidence=supporting_evidence[:4],
            contradictions=contradictions,
            missing_information=missing_info,
            clarification_questions=missing_info,
            failing_constraint=failing_reason if decision in ["NOT_APPLICABLE", "NEEDS_CLARIFICATION"] and 'failing_reason' in locals() else None
        )


_applicability_service: Optional[StandardApplicabilityService] = None

def get_standard_applicability_service() -> StandardApplicabilityService:
    """Get or create singleton applicability service"""
    global _applicability_service
    if _applicability_service is None:
        _applicability_service = StandardApplicabilityService()
    return _applicability_service
