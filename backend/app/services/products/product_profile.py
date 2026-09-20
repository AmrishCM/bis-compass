from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ClarificationQuestionItem(BaseModel):
    """Dynamic clarification question generated based on standard scope distinctions"""
    id: str = Field(..., description="Unique ID for this question, e.g. 'q1'")
    question: str = Field(..., description="Humanized plain-language question — no standard IDs or retrieval reasoning")
    type: str = Field(default="single_choice", description="Question type: single_choice, multiple_choice, yes_no, numeric, text")
    why_needed: str = Field(default="", description="Internal reasoning (not shown to user)")
    why_we_need_this: str = Field(default="This helps us identify the correct BIS requirement.", description="User-facing 1-sentence explanation")
    options: List[str] = Field(default_factory=list, description="Multiple choice options including 'I'm not sure'")
    affects: List[str] = Field(default_factory=lambda: ["standard_selection"], description="Scope or requirement affected")
    attribute_key: str = Field(default="", description="ProductProfile attribute key this question clarifies")
    decision_impact: str = Field(default="standard_selection", description="What this question determines: standard_selection, certification_requirement, testing_scope")

class ProductProfile(BaseModel):
    """
    Structured Product Profile as specified in Section 5 of the requirements.
    Maintains clean state of confirmed vs decision-critical unknown product attributes.
    """
    product_name: str = Field(..., description="Primary product name")
    product_category: Optional[str] = None
    material: Optional[str] = None
    intended_use: Optional[str] = None
    insulation: Optional[str] = None
    construction: Optional[str] = None
    capacity: Optional[str] = None
    country_of_manufacture: Optional[str] = None
    location: Optional[str] = None
    voltage_rating: Optional[str] = None
    conductor_material: Optional[str] = None
    power_rating: Optional[str] = None
    operating_environment: Optional[str] = None  # e.g., domestic, industrial, commercial
    unknown_attributes: List[str] = Field(default_factory=list)
    additional_attributes: Dict[str, Any] = Field(default_factory=dict)

    def apply_answer(self, attribute_key: str, answer_value: str):
        """Update profile attribute with user answer and remove from unknown_attributes"""
        if not attribute_key:
            return
        clean_key = attribute_key.lower().strip()
        val = answer_value.strip()

        if hasattr(self, clean_key):
            setattr(self, clean_key, val)
        else:
            self.additional_attributes[clean_key] = val

        # Remove from unknown_attributes if present
        self.unknown_attributes = [
            u for u in self.unknown_attributes if u.lower().strip() != clean_key
        ]

    def to_summary_dict(self) -> Dict[str, Any]:
        """Human-readable dictionary of confirmed attributes for Step 1 display"""
        summary = {
            "Product Name": self.product_name,
        }
        if self.material:
            summary["Material"] = self.material
        if self.intended_use:
            summary["Intended Use"] = self.intended_use
        if self.construction:
            summary["Construction"] = self.construction
        if self.insulation:
            summary["Insulation"] = self.insulation
        if self.capacity:
            summary["Capacity"] = self.capacity
        if self.operating_environment:
            summary["Operating Environment"] = self.operating_environment
        if self.voltage_rating:
            summary["Voltage Rating"] = self.voltage_rating
        if self.conductor_material:
            summary["Conductor Material"] = self.conductor_material
        if self.location:
            summary["Manufacturing Location"] = self.location

        for k, v in self.additional_attributes.items():
            if v and v != "I am not sure":
                summary[k.replace('_', ' ').capitalize()] = v
        return summary

class MultiProductDetection(BaseModel):
    """Detects multiple distinct products in single user query (Section 29)"""
    is_multi_product: bool = False
    detected_products: List[str] = Field(default_factory=list)
    message: str = ""
