import json
from app.rag.schema import KnowledgeItem
from app.rag.pipeline import run_rag_pipeline
from app.rag.grounding import check_grounding
from app.rag.semantic_retrieval import init_semantic_store

# Initialize semantic index for testing
init_semantic_store()

def test_knowledge_item_schema():
    item = KnowledgeItem(
        id="IS-1786",
        title="TMT Bars",
        document_type="standard",
        source="BIS",
        content="Some content"
    )
    assert item.id == "IS-1786"
    assert item.language == "en"

def test_rag_pipeline_no_results():
    result = run_rag_pipeline("xzxzxzxzxzyyyyyy qwqeqweqwe 1234567890", intent="BIS_GENERAL_QUERY")
    assert result["needs_verification"] is True
    assert "reliably" in result["answer"] or "supported" in result["answer"]
    assert len(result["evidence"]) == 0

def test_rag_pipeline_with_results():
    result = run_rag_pipeline("TMT bars", intent="STANDARD_LOOKUP")
    assert "evidence" in result
    assert isinstance(result["evidence"], list)
    assert len(result["evidence"]) > 0

def test_grounding_checker():
    # If no evidence, not grounded
    assert check_grounding("Some answer", [], "BIS_GENERAL_QUERY") is False
    # If evidence but score too low, not grounded
    assert check_grounding("Some answer", [{"document": type("obj", (object,), {"authority": "Bureau of Indian Standards", "source_type": "standard", "document_id": "test"})(), "rerank_score": 0.01}], "BIS_GENERAL_QUERY") is False
    # If evidence and score high, grounded
    assert check_grounding("Some answer", [{"document": type("obj", (object,), {"authority": "Bureau of Indian Standards", "source_type": "standard", "document_id": "test"})(), "rerank_score": 0.5, "signals": {"identifier_match": True}}], "BIS_GENERAL_QUERY") is True

from app.rag.embeddings import NoOpEmbeddingProvider
from app.rag.semantic_retrieval import SemanticStore, _semantic_store
from app.rag.retrieval import Document

def test_noop_provider():
    provider = NoOpEmbeddingProvider()
    docs = provider.embed_documents(["hello", "world"])
    assert len(docs) == 2
    assert len(docs[0]) == 768
    assert all(x == 0.0 for x in docs[0])

def test_semantic_fallback():
    # If no provider is available (simulated by NoOp or disabled store), it should return empty safely
    store = SemanticStore()
    store.provider = NoOpEmbeddingProvider()
    store.initialize()
    assert store.is_ready is False
    assert len(store.search("query")) == 0

def test_semantic_ambiguity_guardrails():
    # Ambiguous queries should fail grounding (safe refusal)
    res_ambig1 = run_rag_pipeline("steel standard", intent="STANDARD_LOOKUP")
    assert res_ambig1["needs_verification"] is True
    
    res_ambig2 = run_rag_pipeline("BIS for steel", intent="STANDARD_LOOKUP")
    assert res_ambig2["needs_verification"] is True
    
    res_ambig3 = run_rag_pipeline("steel products", intent="STANDARD_LOOKUP")
    assert res_ambig3["needs_verification"] is True
    
    res_ambig4 = run_rag_pipeline("What BIS standard applies to XYZ imaginary product 123?", intent="standard_recommendation")
    assert res_ambig4["needs_verification"] is True
    
    # Specific standard queries should pass
    res_spec1 = run_rag_pipeline("What is IS 1786?", intent="STANDARD_LOOKUP")
    assert res_spec1["needs_verification"] is False
    assert "1786" in str(res_spec1["evidence"])
    
    res_spec2 = run_rag_pipeline("IS 1786", intent="STANDARD_LOOKUP")
    assert res_spec2["needs_verification"] is False
    assert "1786" in str(res_spec2["evidence"])
    
    res_spec3 = run_rag_pipeline("TMT bars", intent="STANDARD_LOOKUP")
    assert res_spec3["needs_verification"] is False
    
    # Phase 3C Targeted Tests
    # Colloquial TMT/rebar questions
    res_rebar1 = run_rag_pipeline("rebar BIS standard", intent="STANDARD_LOOKUP")
    assert res_rebar1["needs_verification"] is False
    assert "1786" in str(res_rebar1["evidence"])
    
    res_rebar2 = run_rag_pipeline("TMT bar standard", intent="STANDARD_LOOKUP")
    assert res_rebar2["needs_verification"] is False
    assert "1786" in str(res_rebar2["evidence"])

    # Drinking-water questions
    res_water = run_rag_pipeline("drinking water standard", intent="STANDARD_LOOKUP")
    assert res_water["needs_verification"] is False
    assert "10500" in str(res_water["evidence"])

    # Safe Refusals (Generic queries)
    assert run_rag_pipeline("standard for metal", intent="STANDARD_LOOKUP")["needs_verification"] is True
    
    # Unsupported fictional products
    assert run_rag_pipeline("Give me the BIS standard for an unsupported fictional product.", intent="standard_recommendation")["needs_verification"] is True

    # Highly specific descriptive queries should pass via strong semantic linkage
    res_sem1 = run_rag_pipeline("Which Indian Standard covers reinforcement steel used in concrete?", intent="standard_recommendation")
    assert res_sem1["needs_verification"] is False
    assert "1786" in str(res_sem1["evidence"])

    # Phase 4 Targeted Tests: Multi-document retrieval
    res_multi = run_rag_pipeline("What is the standard and QCO for TMT bars?", intent="STANDARD_LOOKUP")
    # Should retrieve both IS 1786 and the corresponding QCO (if any)
    # The pipeline should deduplicate and return multiple evidence pieces
    assert res_multi["needs_verification"] is False
    assert len(res_multi["evidence"]) >= 1
    # Check deduplication
    doc_ids = [e["document_title"] for e in res_multi["evidence"]]
    assert len(doc_ids) == len(set(doc_ids))
    
    # Generic standard search should still fail grounding safely
    res_generic = run_rag_pipeline("standard for metal", intent="STANDARD_LOOKUP")
    assert res_generic["needs_verification"] is True
    assert len(res_generic["evidence"]) == 0

    # Phase 4B Targeted Tests
    # Conflicting or incomplete evidence test: A prompt with conflicting info
    # We will simulate a query that hits a QCO and verify the answer mentions applicability verification
    res_qco = run_rag_pipeline("Does QCO-STEEL-2020 apply to rebar?", intent="STANDARD_LOOKUP")
    # Even if deterministic fallback is used, it should mention QCO
    assert "QCO" in res_qco["answer"] or "Quality Control Order" in res_qco["answer"]
    
    # Missing provenance fields / Unknown status
    # We verify that QCOs with 'Unknown' source_url or 'Unverified' are processed
    # QCO_FILE was updated to have 'Unknown' source_url. Let's verify the retrieval correctly parses it as Unverified.
    from app.rag.retrieval import _store
    qco_doc = next((d for d in _store.documents if d.source_type == "qco" and "STEEL" in d.title), None)
    if qco_doc:
        assert qco_doc.source_url == "Unverified" or "Unknown" in qco_doc.source_url
        
    # Check that 'applicable_qco' is preserved in the standard doc
    std_doc = next((d for d in _store.documents if d.document_id == "IS_1786_2008"), None)
    if std_doc:
        doc_json = json.loads(std_doc.content)
        assert "applicable_qco" in doc_json
        assert doc_json["applicable_qco"] == "QCO-STEEL-2020"

def test_source_verification_semantics():
    """Verify that source identity and applicability are not hallucinated."""
    res = run_rag_pipeline("TMT bars", intent="STANDARD_LOOKUP")
    assert len(res["evidence"]) > 0
    for ev in res["evidence"]:
        assert ev["verification_status"] == "Source Identity Unverified"
        assert ev["applicability"] == "Applicability not verified"

