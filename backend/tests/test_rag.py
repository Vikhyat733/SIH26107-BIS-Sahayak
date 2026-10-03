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
    
    # Highly specific descriptive queries should pass via strong semantic linkage
    res_sem1 = run_rag_pipeline("Which Indian Standard covers reinforcement steel used in concrete?", intent="standard_recommendation")
    assert res_sem1["needs_verification"] is False


