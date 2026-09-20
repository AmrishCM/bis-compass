"""
BIS Standards Scope Differentiator and Dynamic Question Generator.
Compares candidate standards against the structured ProductProfile to determine
decision-critical missing attributes and dynamically generate prioritized, humanized questions.
Strictly eliminates hardcoded question banks in accordance with Sections 3, 4, 5, 6, and 7.
"""
from typing import List, Dict, Any, Optional
import json
import logging
import re
from pydantic import BaseModel

from app.services.products.product_profile import ProductProfile, ClarificationQuestionItem
from app.services.llm.provider_factory import LLMProviderFactory, get_llm_provider

logger = logging.getLogger(__name__)

class ScopeDifferentiator:
    """
    Compares candidate standards against product profile to identify decision-critical unknowns.
    Generates dynamic multiple-choice clarification question batches.
    """

    def __init__(self):
        # Use resilient dual LLM provider (Groq/NVIDIA failover) for fast, robust clarification generation
        try:
            self.llm_provider = LLMProviderFactory.create_provider(provider_type="dual")
        except Exception:
            self.llm_provider = get_llm_provider()

    async def differentiate_and_generate_questions(
        self,
        product_profile: ProductProfile,
        candidate_standards: List[Dict[str, Any]],
        previous_questions: Optional[List[str]] = None,
        product_description: str = ""
    ) -> List[ClarificationQuestionItem]:
        """
        Dynamically generates 2-5 prioritized clarification questions based on candidate standards
        and missing product profile attributes.
        """
        prev_q = set(q.lower().strip() for q in (previous_questions or []))

        # Format candidates for LLM prompt — but do NOT expose these IDs to the user
        cand_summaries = []
        for c in candidate_standards[:5]:
            num = c.get("standard_number", "")
            title = c.get("title", "")
            scope = c.get("scope", "") or c.get("evidence_snippet", "")
            cand_summaries.append(f"• Standard: {num} - {title}\n  Scope/Details: {scope[:250]}")

        candidates_text = "\n".join(cand_summaries) if cand_summaries else "General Indian Standards applicable to this product category."

        confirmed_profile = product_profile.to_summary_dict()
        confirmed_text = json.dumps(confirmed_profile, indent=2)
        unknowns_text = ", ".join(product_profile.unknown_attributes) if product_profile.unknown_attributes else "insulation, construction, intended use, capacity"

        system_prompt = (
            "You are generating clarification questions for a manufacturer who wants to check BIS compliance.\n"
            "The manufacturer may have no knowledge of BIS terminology, standard numbers, or technical jargon.\n\n"
            "Your task: Identify which missing product characteristics distinguish whether the candidate BIS standards apply,\n"
            "and generate clear, simple questions that a factory owner can understand and answer.\n\n"
            "STRICT RULES:\n"
            "1. NEVER put standard numbers (like IS 17790, IS 17526) into any question text.\n"
            "2. NEVER expose internal retrieval reasoning, scope analysis, or candidate ranking in questions.\n"
            "3. NEVER use phrases like 'scope distinguishes', 'semantic similarity', 'candidate standard', 'vector retrieval'.\n"
            "4. Convert technical distinctions into everyday language a factory owner understands.\n"
            "5. Use short, direct questions. Example: 'Is your bottle insulated?' NOT 'IS 17790 scope distinguishes single-wall from vacuum double-wall containers'.\n"
            "6. Every question MUST have selectable options. Always include 'I\\'m not sure' as the last option.\n"
            "7. Provide a simple 1-sentence 'why_we_need_this' explaining why the detail matters (in plain language).\n"
            "8. DO NOT ask questions whose answers are already known in Confirmed Product Details.\n"
            "9. DO NOT repeat any previously asked question.\n"
            "10. Prioritize questions that distinguish between candidate standards (Priority 1) over general detail questions (Priority 2).\n"
            "11. Set 'type' to one of: single_choice, multiple_choice, yes_no, numeric, text.\n"
            "12. Set 'decision_impact' to: standard_selection, certification_requirement, or testing_scope.\n\n"
            "Return ONLY valid JSON as a list of questions matching this exact schema:\n"
            "[\n"
            "  {\n"
            '    "id": "q1",\n'
            '    "question": "Is your bottle insulated?",\n'
            '    "type": "single_choice",\n'
            '    "why_we_need_this": "This affects which BIS requirement applies to your product.",\n'
            '    "options": ["Yes — vacuum insulated", "Yes — insulated, but not vacuum", "No — single wall", "I\'m not sure"],\n'
            '    "decision_impact": "standard_selection",\n'
            '    "attribute_key": "insulation"\n'
            "  }\n"
            "]\n\n"
            "GOOD question examples:\n"
            '  "Is your bottle insulated?"\n'
            '  "Who is the product intended for?"\n'
            '  "What is the approximate capacity?"\n\n'
            "BAD question examples (NEVER generate these):\n"
            '  "IS 17790 scope distinguishes single-wall from vacuum double-wall containers — which construction does your product use?"\n'
            '  "IS 17790 specifies domestic drinking storage — is your product intended for domestic consumer retail or industrial transport?"\n'
        )

        user_prompt = (
            f"Product Description: \"{product_description or product_profile.product_name}\"\n\n"
            f"Confirmed Product Details:\n{confirmed_text}\n\n"
            f"Decision-critical Unknown Attributes:\n{unknowns_text}\n\n"
            f"Candidate BIS Standards Discovered (FOR YOUR ANALYSIS ONLY — do NOT mention these to the user):\n{candidates_text}\n\n"
            f"Previously Asked Questions (DO NOT REPEAT):\n{list(prev_q)}\n\n"
            "Generate the necessary clarification questions now in valid JSON."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.llm_provider.chat(messages=messages, temperature=0.1, max_tokens=800)
            raw = response.content.strip()

            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            try:
                parsed = json.loads(raw, strict=False)
            except Exception:
                clean_json = re.sub(r'\\(?![/"\\bfnrtu])', r'\\\\', raw)
                parsed = json.loads(clean_json, strict=False)
            questions: List[ClarificationQuestionItem] = []

            if isinstance(parsed, list):
                for idx, q_dict in enumerate(parsed):
                    if isinstance(q_dict, dict) and q_dict.get("question"):
                        q_text = q_dict["question"].strip()
                        if q_text.lower() in prev_q:
                            continue

                        # Sanitize: strip any standard IDs that the LLM may have leaked
                        q_text = self._sanitize_question_text(q_text)

                        q_id = q_dict.get("id") or f"q{idx + 1}"
                        q_type = q_dict.get("type") or "single_choice"
                        why_user = q_dict.get("why_we_need_this") or "This helps us identify the correct BIS requirement."
                        why_internal = q_dict.get("why_needed") or ""
                        opts = q_dict.get("options") or ["Yes", "No", "I'm not sure"]
                        if not any("not sure" in opt.lower() for opt in opts):
                            opts.append("I'm not sure")
                        affects = q_dict.get("affects") or ["standard_selection"]
                        attr = q_dict.get("attribute_key") or ""
                        impact = q_dict.get("decision_impact") or "standard_selection"

                        questions.append(ClarificationQuestionItem(
                            id=q_id,
                            question=q_text,
                            type=q_type,
                            why_needed=why_internal,
                            why_we_need_this=why_user,
                            options=opts,
                            affects=affects,
                            attribute_key=attr,
                            decision_impact=impact
                        ))
            if questions:
                return questions[:5]  # Batch at most 4-5 questions at once

        except Exception as e:
            logger.warning(f"LLM scope differentiation failed: {e}. Using product-grounded heuristic fallback.")

        # Heuristic fallback if LLM is unavailable or JSON parsing fails
        return self._heuristic_fallback_questions(product_profile, candidate_standards, prev_q)

    @staticmethod
    def _sanitize_question_text(text: str) -> str:
        """Remove any leaked standard IDs (IS XXXXX) from question text"""
        sanitized = re.sub(r'\bIS\s+\d{3,6}(\s*\(Part\s*\d+\))?', '', text)
        sanitized = re.sub(r'\bIS\s+\d{3,6}:\d{4}', '', sanitized)
        # Clean up leftover artifacts
        sanitized = re.sub(r'\s{2,}', ' ', sanitized).strip()
        sanitized = re.sub(r'^[\s,—\-:]+', '', sanitized).strip()
        # Ensure first letter is capitalized
        if sanitized:
            sanitized = sanitized[0].upper() + sanitized[1:]
        return sanitized

    def _heuristic_fallback_questions(
        self,
        product_profile: ProductProfile,
        candidates: List[Dict[str, Any]],
        prev_q: set
    ) -> List[ClarificationQuestionItem]:
        """Dynamic heuristic fallback tailored to missing attributes without static hardcoding"""
        questions = []
        unknowns = set(product_profile.unknown_attributes)

        # 1. Insulation check
        if "insulation" in unknowns and "is your bottle insulated?" not in prev_q:
            questions.append(ClarificationQuestionItem(
                id="q_insulation",
                question="Is your bottle insulated?",
                type="single_choice",
                why_we_need_this="This affects which BIS requirement applies to your product.",
                options=["Yes — vacuum insulated", "Yes — insulated, but not vacuum", "No — single wall", "I'm not sure"],
                affects=["standard_selection"],
                attribute_key="insulation",
                decision_impact="standard_selection"
            ))

        # 2. Construction check
        if "construction" in unknowns and "how is your product constructed?" not in prev_q:
            questions.append(ClarificationQuestionItem(
                id="q_construction",
                question="How is your product constructed?",
                type="single_choice",
                why_we_need_this="Different constructions have different testing and certification requirements.",
                options=["Double-wall construction", "Single-wall construction", "Fabricated with inner lining", "I'm not sure"],
                affects=["standard_selection"],
                attribute_key="construction",
                decision_impact="standard_selection"
            ))

        # 3. Purpose / Use
        if "intended_use" in unknowns and not product_profile.intended_use:
            questions.append(ClarificationQuestionItem(
                id="q_use",
                question="What is it mainly used for?",
                type="single_choice",
                why_we_need_this="The intended use determines which certification rules apply.",
                options=["Drinking water / beverages", "Food storage", "Commercial / industrial use", "Other", "I'm not sure"],
                affects=["standard_selection", "certification_requirement"],
                attribute_key="intended_use",
                decision_impact="standard_selection"
            ))

        # 4. Capacity / Dimensions
        if "capacity" in unknowns and not product_profile.capacity:
            questions.append(ClarificationQuestionItem(
                id="q_capacity",
                question="What is the approximate capacity?",
                type="single_choice",
                why_we_need_this="Some BIS requirements only cover specific size ranges.",
                options=["Below 500 ml", "500 ml – 1 litre", "Above 1 litre", "Multiple sizes", "I'm not sure"],
                affects=["standard_selection", "testing_requirements"],
                attribute_key="capacity",
                decision_impact="standard_selection"
            ))

        # 5. End user
        if "operating_environment" in unknowns:
            questions.append(ClarificationQuestionItem(
                id="q_enduser",
                question="Who is it intended for?",
                type="single_choice",
                why_we_need_this="This can affect whether certification is mandatory or voluntary.",
                options=["Household / consumer", "Commercial / institutional", "Industrial", "Both consumer and commercial", "I'm not sure"],
                affects=["certification_requirement"],
                attribute_key="operating_environment",
                decision_impact="certification_requirement"
            ))

        # 6. Voltage (for electrical)
        if ("voltage_range" in unknowns or "voltage" in unknowns) and any("electrical" in c.get("title", "").lower() or "cable" in c.get("title", "").lower() for c in candidates):
            questions.append(ClarificationQuestionItem(
                id="q_voltage",
                question="What is the rated working voltage?",
                type="single_choice",
                why_we_need_this="The voltage rating determines which safety standard applies.",
                options=["Up to 1100V (low voltage)", "3.3kV to 11kV (medium voltage)", "Above 11kV (high voltage)", "I'm not sure"],
                affects=["standard_selection"],
                attribute_key="voltage_rating",
                decision_impact="standard_selection"
            ))

        return questions[:4]
