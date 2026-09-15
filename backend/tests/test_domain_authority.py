from app.services.research.web_research_engine import SourceAuthorityRanker

def test_source_authority_tier1():
    score, tier = SourceAuthorityRanker.get_authority("bis.gov.in")
    assert tier == 1
    assert score >= 95

    score, tier = SourceAuthorityRanker.get_authority("services.bis.gov.in")
    assert tier == 1

def test_source_authority_tier2():
    score, tier = SourceAuthorityRanker.get_authority("egazette.gov.in")
    assert tier == 2
    assert score >= 90

    score, tier = SourceAuthorityRanker.get_authority("dpiit.gov.in")
    assert tier == 2

def test_source_authority_tier3():
    score, tier = SourceAuthorityRanker.get_authority("iso.org")
    assert tier == 3

def test_source_authority_tier5():
    score, tier = SourceAuthorityRanker.get_authority("random-blog-post-123.com")
    assert tier == 5
    assert score <= 40
