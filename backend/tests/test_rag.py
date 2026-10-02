from app.rag.schema import KnowledgeItem
from app.rag.pipeline import run_rag_pipeline
from app.rag.grounding import check_grounding

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
    result = run_rag_pipeline("some random string that won't match anything 1234567890")
    assert result["grounded"] is False
    assert result["needs_verification"] is True
    assert "authoritative evidence" in result["answer"] or "insufficient" in result["answer"]

def test_rag_pipeline_with_results():
    result = run_rag_pipeline("TMT bars")
    assert "documents" in result
    assert isinstance(result["documents"], list)

def test_grounding_checker():
    # If no evidence, not grounded
    assert check_grounding("Some answer", []) is False
    # If evidence, grounded
    assert check_grounding("Some answer", [{"id": "1"}]) is True
