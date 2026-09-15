import pytest
from app.services.products.open_world_analyzer import OpenWorldProductAnalyzer

@pytest.mark.asyncio
async def test_analyzer_specific_product():
    analyzer = OpenWorldProductAnalyzer()
    res = await analyzer.analyze_product("Stainless steel vacuum insulated flask for hot beverages")
    assert res.product_name != "Unspecified Product"
    assert "flask" in res.normalized_product_name.lower() or "vacuum" in res.normalized_product_name.lower()
    assert any("Steel" in m for m in res.materials)
    assert not res.clarification_required
    assert len(res.clarification_questions) == 0

@pytest.mark.asyncio
async def test_analyzer_vague_material_input_clarification():
    analyzer = OpenWorldProductAnalyzer()
    res = await analyzer.analyze_product("We manufacture steel products.")
    assert res.clarification_required
    assert len(res.clarification_questions) > 0
    assert any("pipes" in q or "flask" in q or "steel" in q.lower() for q in res.clarification_questions)

@pytest.mark.asyncio
async def test_analyzer_arbitrary_novel_product():
    analyzer = OpenWorldProductAnalyzer()
    res = await analyzer.analyze_product("Biodegradable seaweed-based food packaging film")
    assert not res.clarification_required
    assert "film" in res.normalized_product_name.lower() or "packaging" in res.normalized_product_name.lower()
    assert any("Seaweed" in m for m in res.materials)
