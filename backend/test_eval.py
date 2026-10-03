import json
from app.services.assistant_service import answer
from app.rag.retrieval import retrieve_documents
from app.rag.reranking import rerank
from app.rag.grounding import check_grounding
from app.rag.semantic_retrieval import init_semantic_store

init_semantic_store()

QUERIES = [
    # Standard lookup
    "Which BIS standard applies to TMT reinforcement bars?",
    "What standard is used for high strength deformed steel bars?",
    "Which IS standard covers reinforcement bars?",
    "What is IS 1786?",
    "Tell me about IS 1786:2008.",
    
    # Alias/synonym tests
    "TMT bar standard",
    "TMT reinforcement steel standard",
    "rebar BIS standard",
    "deformed steel reinforcement standard",
    "high strength reinforcement bar specification",
    
    # General BIS queries
    "What is BIS certification?",
    "What is a QCO?",
    "What is a Quality Control Order?",
    "Is BIS certification mandatory for every product?",
    
    # Negative / unsupported queries
    "What BIS standard applies to XYZ imaginary product 123?",
    "Which BIS standard applies to a product that does not exist in the current corpus?",
    "Give me the BIS standard for an unsupported fictional product.",
    
    # Ambiguous queries
    "steel standard",
    "BIS for steel",
    "certification for my product",
    
    # Explicit standard queries
    "Explain IS 10500.",
    "What does IS 1786 cover?",
    "IS 1786 reinforcement.",
    "IS 10500 drinking water.",
    
    # LIMS regression
    "Testing labs for IS 1786",
    "Testing labs near Lucknow for IS 1786",
    
    # Certification regression
    "Which QCO applies to TMT reinforcement bars?",
    "Does TMT reinforcement bar require mandatory BIS certification?",
    
    # Semantic Phase 2 Queries (Should Improve)
    "What standard should I use for steel bars used to reinforce concrete?",
    "Which Indian Standard covers reinforcement steel used in concrete?",
    "Specification for high strength deformed steel used as concrete reinforcement",
    "standard for TMT construction reinforcement",
    
    # Semantic Phase 2 Queries (Must Remain Safe)
    "standard for metal",
]

results = []

for q in QUERIES:
    # 1. Full E2E answer to get intent and final response
    e2e = answer(q)
    intent = e2e.get("intent", "UNKNOWN")
    
    # 2. Get internal RAG state if applicable
    from app.rag.semantic_retrieval import retrieve_semantic_documents
    bm25_cands = retrieve_documents(q, top_k=5)
    sem_cands = retrieve_semantic_documents(q, top_k=5)
    
    fused = {}
    for c in bm25_cands:
        doc_id = c["document"].document_id
        fused[doc_id] = {
            "document": c["document"],
            "bm25_score": c["retrieval_score"],
            "semantic_score": 0.0,
            "retrieval_method": c["retrieval_method"]
        }
    for c in sem_cands:
        doc_id = c["document"].document_id
        if doc_id in fused:
            fused[doc_id]["semantic_score"] = c["retrieval_score"]
            fused[doc_id]["retrieval_method"] = "fused"
        else:
            fused[doc_id] = {
                "document": c["document"],
                "bm25_score": 0.0,
                "semantic_score": c["retrieval_score"],
                "retrieval_method": c["retrieval_method"]
            }
    candidates = list(fused.values())
    
    # We need to manually rerank to see scores
    bm25_scores = [c.get("bm25_score", 0) for c in candidates]
    bm25_docs = [c["document"].document_id for c in candidates]
    
    # Ensure candidates list isn't modified in-place maliciously
    reranked = rerank(q, list(candidates))
    rerank_scores = [c.get("rerank_score", c.get("retrieval_score")) for c in reranked]
    rerank_docs = [c["document"].document_id for c in reranked]
    
    grounding = check_grounding(q, reranked, intent)
    
    results.append({
        "query": q,
        "intent": intent,
        "e2e_answer": e2e.get("answer"),
        "confidence": e2e.get("confidence"),
        "needs_verification": e2e.get("needs_verification"),
        "bm25_candidates": bm25_docs,
        "bm25_scores": bm25_scores,
        "reranked_candidates": rerank_docs,
        "rerank_scores": rerank_scores,
        "grounding_passed": grounding,
        "evidence": e2e.get("evidence"),
        "sources": e2e.get("sources")
    })
    
with open("eval_results.json", "w") as f:
    json.dump(results, f, indent=2)
