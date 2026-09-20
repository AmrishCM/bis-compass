import asyncio
import pytest
from app.services.products.product_understanding import ProductUnderstanding
from app.services.standards.applicability_service import StandardApplicabilityService
from app.agents.laboratory_agent import LaboratoryAgent
from app.agents.orchestrator_agent import OrchestratorAgent, OrchestrationInput
from app.db.session import SessionLocal, init_db
from app.models.standard import ProductSession, LaboratoryRecord

def test_regression_issue1_pvc_cables():
    """
    Issue 1 Regression Test:
    For 'PVC insulated electric cables... up to 1100V':
    - IS 694 (up to 1100V) -> APPLICABLE
    - IS 1554 Pt 2 (3.3kV to 11kV) -> NOT_APPLICABLE with failing_constraint
    - IS 3961 Pt 5 (current rating guideline) -> RELATED with guideline reason
    - IS 14521 (flat ribbon cable) -> NOT_APPLICABLE with form factor mismatch
    """
    svc = StandardApplicabilityService()
    cable_prod = ProductUnderstanding(
        product_name="PVC insulated electric cables",
        product_description="PVC insulated electric cables with copper conductor for working voltages up to 1100V",
        category="Electrical Cables & Wires",
        materials=["copper", "PVC"],
        intended_use="Electric power transmission and domestic wiring"
    )

    # 1. IS 694:2010
    d_694 = svc.evaluate_applicability(cable_prod, {
        "standard_number": "IS 694:2010",
        "title": "PVC Insulated Cables for Working Voltages Up to and Including 1100 V",
        "scope": "Covers requirements for PVC insulated cables for working voltages up to and including 1100 V."
    })
    assert d_694.decision == "APPLICABLE", f"IS 694 should be APPLICABLE, got {d_694.decision}"

    # 2. IS 1554 (Part 2):1988
    d_1554 = svc.evaluate_applicability(cable_prod, {
        "standard_number": "IS 1554 (Part 2):1988",
        "title": "PVC insulated (heavy duty) electric cables: Part 2 For working voltages from 3.3 kV up to and including 11 kV",
        "scope": "Requirements for PVC insulated cables for working voltages from 3.3 kV up to and including 11 kV."
    })
    assert d_1554.decision == "NOT_APPLICABLE", f"IS 1554 Pt 2 should be NOT_APPLICABLE, got {d_1554.decision}"
    assert d_1554.failing_constraint is not None
    assert "voltage" in d_1554.failing_constraint.lower() or "disjoint" in d_1554.failing_constraint.lower()

    # 3. IS 3961 (Part 5):1968
    d_3961 = svc.evaluate_applicability(cable_prod, {
        "standard_number": "IS 3961 (Part 5):1968",
        "title": "Recommended current ratings for cables: Part 5 PVC insulated light duty cables",
        "scope": "Recommended current ratings for PVC insulated light duty cables."
    })
    assert d_3961.decision == "RELATED", f"IS 3961 Pt 5 should be RELATED, got {d_3961.decision}"

    # 4. IS 14521:1998
    d_14521 = svc.evaluate_applicability(cable_prod, {
        "standard_number": "IS 14521:1998",
        "title": "Cables and Wires for Internal Wiring of Electronic and Telecommunication Equipment - Flat Ribbon Cable",
        "scope": "Requirements for flat ribbon cables for internal wiring of electronic equipment."
    })
    assert d_14521.decision == "NOT_APPLICABLE", f"IS 14521 should be NOT_APPLICABLE, got {d_14521.decision}"
    assert d_14521.failing_constraint is not None
    assert "ribbon" in d_14521.failing_constraint.lower() or "form factor" in d_14521.failing_constraint.lower()

def test_regression_major_bug_stainless_steel_vs_electrical():
    """
    Section 58 Regression Test:
    Stainless steel drinking bottle must NEVER match electrical standards
    merely because it contains 'steel'.
    """
    svc = StandardApplicabilityService()
    bottle_prod = ProductUnderstanding(
        product_name="Stainless Steel Drinking Bottle",
        product_description="Stainless steel vacuum bottle for hot and cold drinking water",
        category="Domestic insulated container",
        materials=["stainless steel"],
        intended_use="storage of hot and cold drinking liquids"
    )

    # Evaluate against electrical standard IS 694
    d_elec = svc.evaluate_applicability(bottle_prod, {
        "standard_number": "IS 694:2010",
        "title": "PVC Insulated Cables for Working Voltages Up to and Including 1100 V",
        "scope": "Covers requirements for PVC insulated cables for working voltages up to and including 1100 V."
    })
    assert d_elec.decision == "NOT_APPLICABLE", f"Electrical standard must be rejected for bottle, got {d_elec.decision}"
    assert d_elec.failing_constraint is not None
    assert "domain" in d_elec.failing_constraint.lower() or "non-electrical" in d_elec.failing_constraint.lower()

@pytest.mark.asyncio
async def test_regression_issue3_delhi_laboratory_lookup():
    """
    Issue 3 Regression Test:
    Laboratory search for 'Delhi' must return recognized testing laboratories
    from local database and verified directories without timing out or returning 0.
    """
    init_db()
    lab_agent = LaboratoryAgent()
    pu = ProductUnderstanding(
        product_name="Stainless Steel Vacuum Bottle",
        category="Domestic insulated container",
        materials=["stainless steel"],
        intended_use="Domestic drinking container"
    )

    labs = await lab_agent.find_labs_for_product(
        product_understanding=pu,
        standard_id=1,
        location="Delhi",
        max_results=5,
        standard_number="IS 17526:2021"
    )

    assert len(labs) > 0, "Expected at least 1 laboratory found for Delhi, got 0"
    lab_names = [l.lab_name for l in labs]
    # Check that known recognized labs in Delhi/NCR are returned
    has_delhi_lab = any("delhi" in l.location.lower() or "delhi" in l.address.lower() or "ghaziabad" in l.address.lower() for l in labs)
    assert has_delhi_lab, f"Expected Delhi laboratory in results: {lab_names}"

def test_regression_clarification_session_flow():
    """
    Clarification & Session State Regression Test (Rules 15-17, 32, 37):
    - Initial vague product triggers clarification_required
    - Session ID is generated and persisted in ProductSession table
    - Clarification endpoint updates session and continues analysis under same session_id
    """
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # 1. Post vague product
    resp = client.post("/api/analyze", json={
        "product_description": "We manufacture steel products",
        "location": "Coimbatore"
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["clarification_required"] is True, "Expected clarification_required=True for vague product"
    assert "session_id" in data and data["session_id"].startswith("BC-2026-"), "Expected session_id formatted BC-2026-*"
    sid = data["session_id"]

    # 2. Get session by ID
    get_resp = client.get(f"/api/analyze/session/{sid}")
    assert get_resp.status_code == 200, f"Expected session retrieval 200, got {get_resp.status_code}"
    sess_data = get_resp.json()
    assert sess_data["session_id"] == sid
    assert sess_data["status"] == "NEEDS_CLARIFICATION"

    # 3. Submit clarification to /api/analyze/clarify
    clarif_resp = client.post("/api/analyze/clarify", json={
        "session_id": sid,
        "clarification_answer": "Vacuum insulated stainless steel drinking bottle 750ml for hot and cold water",
        "question": data["clarification_questions"][0] if data.get("clarification_questions") else "Product details",
        "location": "Coimbatore"
    })
    assert clarif_resp.status_code == 200, f"Expected 200 on clarify, got {clarif_resp.status_code}: {clarif_resp.text}"
    clarif_data = clarif_resp.json()
    assert clarif_data["session_id"] == sid, "Session ID must be preserved across clarification turns"
    assert clarif_data["product_understanding"]["product_name"] is not None

if __name__ == "__main__":
    print("Running Master Regression Tests...")
    test_regression_issue1_pvc_cables()
    print("✓ Issue 1 (PVC Cable Voltage Ranges & Disjoint Constraints) PASSED")

    test_regression_major_bug_stainless_steel_vs_electrical()
    print("✓ Section 58 (Stainless Steel Bottle vs Electrical Regression) PASSED")

    asyncio.run(test_regression_issue3_delhi_laboratory_lookup())
    print("✓ Issue 3 (Delhi Laboratory Lookup & Database Routing) PASSED")

    test_regression_clarification_session_flow()
    print("✓ Section 15-17 & 32 (Clarification & ProductSession Flow) PASSED")

    print("\nALL MASTER REGRESSION TESTS PASSED SUCCESSFULLY!")
