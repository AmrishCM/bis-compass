"""
Automated Test Suite for Open-World Product Intelligence & BIS Applicability Engine.
Verifies arbitrary novel products, separation of product identity from material,
suppression of false positives, clarification requests on vague queries, and safe abstention.
"""
import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.products.product_understanding import get_product_understanding_engine
from app.services.standards.matching_engine import get_standards_matching_engine
from app.agents.orchestrator_agent import OrchestratorAgent, OrchestrationInput

async def run_tests():
    print("==================================================================")
    print("  BIS-Compass: Open-World Product Intelligence & Applicability Test")
    print("==================================================================\n")

    orchestrator = OrchestratorAgent()
    passed = 0
    total = 0

    test_cases = [
        {
            "name": "1. Stainless Steel Vacuum Flask (False Positive Suppression)",
            "query": "I want to sell stainless steel vacuum flasks for domestic use",
            "expected_applicable": "IS 17526",
            "must_reject": ["IS 302-2-15", "IS 694"],
            "must_clarify": False
        },
        {
            "name": "2. Cotton T-Shirt (Apparel - Not In Seed DB)",
            "query": "I manufacture cotton T-shirts.",
            "expected_applicable": None,  # Must NOT match cables, water heaters, flasks
            "must_reject": ["IS 694", "IS 302-2-15", "IS 17526"],
            "must_clarify": False
        },
        {
            "name": "3. Electric Water Heater (Heater Standard Match)",
            "query": "Domestic electric storage water heater 25L with thermostat",
            "expected_applicable": "IS 302-2-15",
            "must_reject": ["IS 17526", "IS 694"],
            "must_clarify": False
        },
        {
            "name": "4. PVC Insulated Electric Cables",
            "query": "PVC insulated electric cables for working voltages up to 1100V",
            "expected_applicable": "IS 694",
            "must_reject": ["IS 17526", "IS 14543"],
            "must_clarify": False
        },
        {
            "name": "5. Secondary Lithium Cells and Batteries (CRS)",
            "query": "Secondary lithium cells and batteries for portable applications",
            "expected_applicable": "IS 16046",
            "must_reject": ["IS 694", "IS 302-2-15"],
            "must_clarify": False
        },
        {
            "name": "6. Packaged Drinking Water in Sealed Bottles",
            "query": "Packaged natural mineral drinking water in sealed PET bottles",
            "expected_applicable": "IS 14543",
            "must_reject": ["IS 694"],
            "must_clarify": False
        },
        {
            "name": "7. Biodegradable Seaweed Packaging Film (Novel Product)",
            "query": "We make a biodegradable seaweed-based food packaging film.",
            "expected_applicable": None,  # Must understand as bio-packaging, abstain gracefully
            "must_reject": ["IS 694", "IS 302-2-15", "IS 17526"],
            "must_clarify": False
        },
        {
            "name": "8. Smart Textile Sensor Patch (Novel Wearable)",
            "query": "We make a smart textile sensor patch for sports monitoring.",
            "expected_applicable": None,  # Understand as wearable electronic, abstain gracefully
            "must_reject": ["IS 17526", "IS 302-2-15"],
            "must_clarify": False
        },
        {
            "name": "9. Vague Material-Only Input (Trigger Clarification)",
            "query": "We manufacture steel products.",
            "expected_applicable": None,
            "must_reject": [],
            "must_clarify": True
        },
        {
            "name": "10. Anti-Gravity Quantum Hoverboard (Negative Test)",
            "query": "Anti-gravity quantum hoverboard for interstellar travel",
            "expected_applicable": None,
            "must_reject": [],
            "must_clarify": False
        }
    ]

    for tc in test_cases:
        total += 1
        print(f"Running Test [{total}]: {tc['name']}")
        print(f"Query: \"{tc['query']}\"")

        input_data = OrchestrationInput(
            product_description=tc["query"],
            include_web_search=False
        )

        result = await orchestrator.run_full_certification_analysis(input_data)
        pu = result.product_understanding
        applicable_numbers = [s.standard_number for s in result.applicable_standards]
        rejected_numbers = [r["standard_number"] for r in result.rejected_candidates]

        print(f"  -> Product Identity: {pu.product_name if pu else 'None'}")
        print(f"  -> Product Family:   {pu.product_family if pu else 'None'}")
        print(f"  -> Materials:        {pu.materials if pu else []}")
        print(f"  -> Clarification:    {result.clarification_required}")
        print(f"  -> Applicable:       {applicable_numbers}")
        print(f"  -> Rejected:         {len(rejected_numbers)} candidates")

        test_passed = True

        # Check clarification requirement
        if tc["must_clarify"]:
            if not result.clarification_required:
                print("  [FAIL] Expected clarification_required=True, got False")
                test_passed = False
            else:
                print(f"  [OK] Clarification requested with {len(result.clarification_questions)} targeted questions")

        else:
            # Check expected applicable standard
            if tc["expected_applicable"]:
                matched = any(tc["expected_applicable"] in num for num in applicable_numbers)
                if not matched:
                    print(f"  [FAIL] Expected {tc['expected_applicable']} in applicable standards, got {applicable_numbers}")
                    test_passed = False
                else:
                    print(f"  [OK] Correctly identified applicable standard {applicable_numbers[0]}")
            else:
                # Should not have false positives
                if applicable_numbers:
                    print(f"  [FAIL] Expected safe abstention, but got false positive: {applicable_numbers}")
                    test_passed = False
                else:
                    print(f"  [OK] Safely abstained without false positives: \"{result.overall_assessment[:80]}...\"")

            # Check must_reject standards
            for rejected_expected in tc["must_reject"]:
                if any(rejected_expected in num for num in applicable_numbers):
                    print(f"  [FAIL] Standard {rejected_expected} was falsely recommended!")
                    test_passed = False

        if test_passed:
            passed += 1
            print("  ==> TEST RESULT: PASS\n")
        else:
            print("  ==> TEST RESULT: FAIL\n")

    print("==================================================================")
    print(f"  Test Suite Completed: {passed} / {total} tests passed ({int(passed/total*100)}%)")
    print("==================================================================")

    if passed == total:
        print("ALL TESTS PASSED! False positive rate: 0.0%, Open-World Accuracy: 100%")
        return 0
    else:
        print("SOME TESTS FAILED.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
