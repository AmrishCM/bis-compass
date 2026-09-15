from app.services.research.research_planner import ComplianceResearchPlanner
from app.services.products.product_understanding import ProductUnderstanding

def test_research_planner_multi_dimensional():
    planner = ComplianceResearchPlanner()
    pu = ProductUnderstanding(
        product_name="Solar Inverter",
        normalized_product_name="solar inverter",
        materials=["Silicon", "Aluminum"],
        intended_use="Photovoltaic grid connection"
    )
    plan = planner.generate_research_plan(pu)
    assert len(plan.dimensions) >= 4
    dim_names = [d.dimension_name for d in plan.dimensions]
    assert "standards_discovery" in dim_names
    assert "qco_mandate" in dim_names
    assert "certification_scheme" in dim_names

    # Check that Tier 1 domain targeting is present
    t1_dim = next(d for d in plan.dimensions if d.dimension_name == "standards_discovery")
    assert any("bis.gov.in" in dom for dom in t1_dim.target_domains)
