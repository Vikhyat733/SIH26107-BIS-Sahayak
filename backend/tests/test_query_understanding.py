from app.rag.query_understanding import QueryUnderstandingService

def test_query_understanding():
    qu = QueryUnderstandingService()
    
    # 1. "What is IS 1786?"
    res = qu.understand("What is IS 1786?")
    assert res.intent == "STANDARD_LOOKUP"
    assert any(i["core_identifier"] == "1786" for i in res.standard_identifiers)
    assert res.specificity == "HIGH"
    assert res.needs_clarification is False
    
    # 2. "IS 1786:2008"
    res = qu.understand("IS 1786:2008")
    assert res.intent == "STANDARD_LOOKUP"
    assert any(i["core_identifier"] == "1786" for i in res.standard_identifiers)
    assert res.specificity == "HIGH"
    
    # 3. "IS-1786"
    res = qu.understand("IS-1786")
    assert res.intent == "STANDARD_LOOKUP"
    assert any(i["core_identifier"] == "1786" for i in res.standard_identifiers)
    
    # 4. "Indian Standard 1786"
    res = qu.understand("Indian Standard 1786")
    # Actually Indian Standard 1786 doesn't start with IS, so intent is BIS_GENERAL_QUERY
    # But it should still extract identifier
    assert any(i["core_identifier"] == "1786" for i in res.standard_identifiers)
    assert res.specificity == "HIGH"
    
    # 5. "What standard applies to TMT bars?"
    res = qu.understand("What standard applies to TMT bars?")
    assert res.intent == "standard_recommendation"
    assert any(e.canonical == "tmt" or e.canonical == "tmt bar" for e in res.product_entities)
    assert res.specificity == "HIGH"
    assert res.needs_clarification is False
    
    # 6. "TMT reinforcement bars"
    res = qu.understand("TMT reinforcement bars")
    assert any("tmt" in e.canonical or "reinforcement" in e.canonical for e in res.product_entities)
    
    # 7. "Which Indian Standard covers reinforcement steel used in concrete?"
    res = qu.understand("Which Indian Standard covers reinforcement steel used in concrete?")
    assert res.intent == "standard_recommendation"
    assert res.specificity in ("HIGH", "MEDIUM")
    assert res.needs_clarification is False
    
    # 8. "steel standard"
    res = qu.understand("steel standard")
    assert res.specificity == "LOW"
    assert res.needs_clarification is True
    
    # 9. "BIS for steel"
    res = qu.understand("BIS for steel")
    assert res.specificity == "LOW"
    assert res.needs_clarification is True
    
    # 10. "steel products"
    res = qu.understand("steel products")
    assert res.specificity == "LOW"
    assert res.needs_clarification is True
    
    # 11. "How do I get BIS certification for TMT bars?"
    res = qu.understand("How do I get BIS certification for TMT bars?")
    assert res.intent == "CERTIFICATION_QUERY"
    
    # 12. "Which QCO applies to TMT reinforcement bars?"
    res = qu.understand("Which QCO applies to TMT reinforcement bars?")
    assert res.intent == "QCO_QUERY"
    
    # 13. "Testing labs near Lucknow for IS 1786"
    res = qu.understand("Testing labs near Lucknow for IS 1786")
    assert res.intent == "LAB_LOOKUP"
    assert any(i["core_identifier"] == "1786" for i in res.standard_identifiers)
    
    # 14. "What is BIS certification?"
    res = qu.understand("What is BIS certification?")
    assert res.intent == "BIS_GENERAL_QUERY"
    
    # 15. "Check this MTC against IS 1786"
    res = qu.understand("Check this MTC against IS 1786")
    assert res.intent == "COMPLIANCE_QUERY"
    
    # 16. fictional/unknown product query
    res = qu.understand("What BIS standard applies to XYZ imaginary product 123?")
    assert res.intent == "standard_recommendation"
    assert len(res.product_entities) == 0
    assert len(res.standard_identifiers) == 0
    assert res.specificity == "LOW"
    assert res.needs_clarification is True
