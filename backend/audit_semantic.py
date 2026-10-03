import json
import logging
from app.rag.pipeline import run_rag_pipeline
from app.rag.retrieval import retrieve_documents
from app.rag.semantic_retrieval import retrieve_semantic_documents, init_semantic_store
from app.rag.reranking import rerank
from app.rag.grounding import check_grounding

logging.basicConfig(level=logging.CRITICAL)

queries = [
    "steel standard",
    "BIS for steel",
    "steel products",
    "reinforcement steel",
    "steel bars",
    "TMT",
    "TMT bars",
    "Which standard applies to steel?",
    "Which Indian Standard covers reinforcement steel used in concrete?",
    "What standard should I use for steel bars used to reinforce concrete?",
    "What is IS 1786?",
    "IS 1786",
    "What BIS standard applies to XYZ imaginary product 123?"
]

init_semantic_store()

print("="*80)
for q in queries:
    print(f"QUERY: {q}")
    
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
            fused[doc_id]["retrieval_method"] = "fused_lexical_semantic"
        else:
            fused[doc_id] = {
                "document": c["document"],
                "bm25_score": 0.0,
                "semantic_score": c["retrieval_score"],
                "retrieval_method": c["retrieval_method"]
            }
            
    candidates = list(fused.values())
    ranked = rerank(q, candidates)
    
    if not ranked:
        print("No candidates found.")
        print("-" * 40)
        continue
        
    top = ranked[0]
    doc = top["document"]
    score = top["rerank_score"]
    signals = top.get("signals", {})
    
    bm25_norm = signals.get('bm25_norm', 0.0)
    sem_score = signals.get('semantic_score', 0.0)
    bm25_contrib = bm25_norm * 0.05
    sem_contrib = sem_score * 0.30
    agreement = 0.05 if (bm25_norm > 0 and sem_score > 0) else 0.0
    
    import re
    q_low = q.lower().strip()
    intent = "BIS_GENERAL_QUERY"
    if re.match(r"^is\s*:?\s*\d+(:\d{4})?$", q_low):
        intent = "STANDARD_LOOKUP"
    elif any(k in q_low for k in ["which standard", "which bis standard", "standard applies to"]):
        intent = "standard_recommendation"
    elif len(q_low.split()) <= 3 and ("phone" in q_low or "tmt" in q_low or "mobile" in q_low):
        intent = "standard_recommendation"
    elif q_low.startswith("smx"):
        intent = "standard_recommendation"
    if any(k in q_low for k in ["mandatory", "certification", "qco", "require bis", "how do i get"]):
        if not ("what is bis certification" in q_low or "what is a qco" in q_low or "what is a quality control order" in q_low):
            intent = "CERTIFICATION_QUERY"
    if any(k in q_low for k in ["test", "lab", "laboratory", "laboratories", "testing", "where can i get my product tested"]):
        if not ("what is a lab" in q_low):
            intent = "LAB_LOOKUP"
    is_grounded = check_grounding(q, ranked, intent)
    
    is_standard_query = intent in ("STANDARD_LOOKUP", "standard_recommendation")
    is_standard_result = doc.source_type in ("standard", "qco")
    threshold = 0.30 if (is_standard_query or is_standard_result) else 0.05
    
    has_id = signals.get("identifier_match", False)
    has_alias = signals.get("alias_score", 0) >= 1.0
    has_strong_semantic = signals.get("semantic_score", 0) >= 0.70
    
    reason = "Passed" if is_grounded else "Failed"
    if not is_grounded:
        if score < threshold:
            reason = f"Score ({score}) below threshold ({threshold})"
        elif (is_standard_query or is_standard_result) and not (has_id or has_alias or has_strong_semantic):
            reason = "Ambiguous: lacks ID, specific alias, or strong semantic link"
            
    # Find raw top BM25 and Semantic
    top_bm25 = sorted(bm25_cands, key=lambda x: x['retrieval_score'], reverse=True)
    top_sem = sorted(sem_cands, key=lambda x: x['retrieval_score'], reverse=True)
    
    tb = top_bm25[0] if top_bm25 else None
    ts = top_sem[0] if top_sem else None
            
    print(f"Top BM25 Candidate: {tb['document'].document_id if tb else 'None'} | raw={tb['retrieval_score'] if tb else 0}")
    print(f"Top Sem Candidate:  {ts['document'].document_id if ts else 'None'} | cosine={ts['retrieval_score'] if ts else 0}")
    print(f"Both channels retrieved top doc ({doc.document_id})? {'Yes' if (bm25_norm > 0 and sem_score > 0) else 'No'}")
    print(f"Identifier signal:  {signals.get('identifier_match', False)}")
    print(f"Alias/Entity signal: {signals.get('alias_score', 0)}")
    print(f"Title signal:       {signals.get('title_score', 0)}")
    print(f"BM25 contrib:       {bm25_contrib:.4f} (norm {bm25_norm:.4f} * 0.05)")
    print(f"Semantic contrib:   {sem_contrib:.4f} (cosine {sem_score:.4f} * 0.30)")
    print(f"Agreement bonus:    {agreement:.4f}")
    print(f"Final rerank score: {score:.4f}")
    print(f"Threshold:          {threshold}")
    print(f"Grounded?           {is_grounded}")
    print(f"Selected Document:  {doc.document_id}")
    print(f"Decision Reason:    {reason}")
    print("-" * 80)
