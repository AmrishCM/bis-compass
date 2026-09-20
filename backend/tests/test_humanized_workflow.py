import asyncio
import logging
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.agents.orchestrator_agent import OrchestratorAgent, OrchestrationInput
from app.services.products.product_profile import ProductProfile
from app.services.research.scope_differentiator import ScopeDifferentiator
from app.services.compliance.humanized_roadmap import HumanizedRoadmapBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_vague_bottle_triggers_clarification():
    """Verify that 'I manufacture stainless steel water bottles' does NOT immediately assume IS 17526"""
    orchestrator = OrchestratorAgent()
    input_data = OrchestrationInput(
        product_description="I manufacture stainless steel water bottles.",
        location="Tiruppur, Tamil Nadu",
        include_web_search=True
    )
    result = await orchestrator.run_full_certification_analysis(input_data)
    
    assert result.clarification_required is True, "Clarification should be required for unspecified stainless steel water bottle"
    assert result.final_status == "NEEDS_CLARIFICATION", f"Expected NEEDS_CLARIFICATION, got {result.final_status}"
    assert len(result.clarification_questions) > 0, "Expected dynamic clarification questions"
    assert len(result.clarification_question_items) > 0, "Expected structured clarification question items with options"
    assert len(result.applicable_standards) == 0, "No standard should be marked APPLICABLE before clarification"

    first_q = result.clarification_question_items[0]
    assert "options" in first_q, "Question item must include multiple-choice options"
    assert len(first_q["options"]) >= 2, "Question item must have at least 2 options"
    logger.info("Test 1 passed: Vague bottle triggers dynamic multi-question clarification step successfully")

@pytest.mark.asyncio
async def test_clarification_answers_confirm_standard():
    """Verify that providing clarification answers confirms IS 17526 and produces humanized roadmap"""
    orchestrator = OrchestratorAgent()
    
    # User provides confirmed profile
    profile = ProductProfile(
        product_name="Stainless Steel Vacuum Drinking Bottle",
        material="Stainless steel",
        intended_use="Drinking water",
        insulation="vacuum insulated",
        construction="double-wall",
        capacity="750 ml",
        location="Tiruppur, Tamil Nadu",
        unknown_attributes=[]
    )
    
    input_data = OrchestrationInput(
        product_description="Stainless steel double-walled vacuum insulated drinking bottle 750ml for domestic use. Tiruppur, Tamil Nadu.",
        product_profile=profile.dict(),
        location="Tiruppur, Tamil Nadu",
        include_web_search=True
    )
    
    result = await orchestrator.run_full_certification_analysis(input_data)
    
    assert result.clarification_required is False, "Clarification should not be required when attributes are confirmed"
    assert len(result.applicable_standards) > 0, "Expected at least one verified standard"
    
    std_nums = [s.standard_number for s in result.applicable_standards]
    assert any("17526" in s for s in std_nums), f"Expected IS 17526 in applicable standards, found: {std_nums}"
    
    assert result.step_by_step_roadmap, "Step-by-step roadmap must be generated"
    roadmap = result.step_by_step_roadmap
    assert "step_1_product" in roadmap
    assert "step_2_standard" in roadmap
    assert "step_3_certification" in roadmap
    assert "step_4_tests" in roadmap
    assert "step_5_laboratories" in roadmap
    assert "step_6_how_to_apply" in roadmap
    assert "step_7_next_steps" in roadmap
    
    logger.info("Test 2 passed: Confirmed profile successfully verifies standard and produces full 8-step roadmap")

@pytest.mark.asyncio
async def test_multi_product_detection():
    """Verify that multiple products in input are detected and split (Section 29)"""
    orchestrator = OrchestratorAgent()
    input_data = OrchestrationInput(
        product_description="I manufacture stainless steel bottles, electrical switches and PVC pipes.",
        location="Chennai, Tamil Nadu",
        include_web_search=False
    )
    result = await orchestrator.run_full_certification_analysis(input_data)
    
    assert result.clarification_required is True
    assert result.multi_product_detected is not None
    assert result.multi_product_detected.get("is_multi_product") is True
    prods = result.multi_product_detected.get("detected_products", [])
    assert len(prods) >= 2, f"Expected multiple detected products, got {prods}"
    logger.info(f"Test 3 passed: Multi-product detected successfully: {prods}")

if __name__ == "__main__":
    asyncio.run(test_vague_bottle_triggers_clarification())
    asyncio.run(test_clarification_answers_confirm_standard())
    asyncio.run(test_multi_product_detection())
    print("ALL TESTS PASSED SUCCESSFULLY!")
