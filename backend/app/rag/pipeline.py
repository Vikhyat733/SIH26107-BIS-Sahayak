import logging
from typing import Dict, Any, List
import json
from .retrieval import retrieve_documents
from .reranking import rerank
from .grounding import check_grounding

logger = logging.getLogger("rag_pipeline")
logging.basicConfig(level=logging.INFO)

def run_rag_pipeline(query: str, intent: str = "BIS_GENERAL_QUERY") -> Dict[str, Any]:
    logger.info(f"Retrieval started for query: '{query}', intent: {intent}")
    
    # 1. Retrieve candidates
    from .semantic_retrieval import retrieve_semantic_documents
    bm25_cands = retrieve_documents(query, top_k=5)
    sem_cands = retrieve_semantic_documents(query, top_k=5)
    
    # Candidate Fusion
    fused: Dict[str, Dict[str, Any]] = {}
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
    logger.info(f"Fused Candidates retrieved: {len(candidates)} (BM25: {len(bm25_cands)}, Semantic: {len(sem_cands)})")
    
    # 2. Rerank
    ranked_docs = rerank(query, candidates)
    
    # 3. Grounding Gate
    is_grounded = check_grounding(query, ranked_docs, intent)
    
    # 4. Formulate Answer (Deterministic generation for Phase 1)
    if not is_grounded:
        logger.info("Grounding failed. Returning safe refusal.")
        if intent in ("STANDARD_LOOKUP", "standard_recommendation"):
            answer = "No sufficiently supported BIS standard was found for this product in the current knowledge base.\n\nTry describing the product in more detail."
        else:
            answer = "This question could not be answered reliably from the current knowledge base."
            
        return {
            "intent": intent,
            "answer": answer,
            "evidence": [],
            "sources": [],
            "confidence": 0.0,
            "needs_verification": True
        }
        
    top_cand = ranked_docs[0]
    doc = top_cand["document"]
    
    logger.info(f"Evidence selected: {doc.document_id}")
    
    # Deterministic Answer Generation (Mocking LLM output for Phase 1) fallback
    def generate_deterministic_fallback():
        if intent in ("STANDARD_LOOKUP", "standard_recommendation") or doc.source_type == "standard":
            std = doc.standard_number or doc.document_id
            title = doc.title
            product = title.split("—")[0].split("-")[0].strip().lower() if title else query.lower()
            return f"{std} is identified in the available BIS evidence as covering {product}.\n\nVerify current applicability and regulatory requirements before compliance action."
        elif doc.source_type == "qco":
            qco_title = doc.title
            return f"Found a relevant Quality Control Order (QCO): {qco_title}."
        else:
            content = doc.content
            if content.startswith(doc.title):
                content = content[len(doc.title):].strip()
            return content

    # Build EvidencePacket
    from ..llm import EvidencePacket, EvidenceItem, get_provider
    ev_item = EvidenceItem(
        document_id=doc.document_id,
        title=doc.title,
        source_authority=doc.authority,
        excerpt=doc.content[:1500],  # Keep excerpt reasonable
        relevance_score=top_cand.get("final_score", 0.0),
        url=doc.source_url or ""
    )
    packet = EvidencePacket(
        query=query,
        intent=intent,
        evidence=[ev_item]
    )

    provider = get_provider()
    generated = None
    if provider:
        generated = provider.generate(packet)

    if generated:
        answer = generated.answer
        if generated.caveats:
            answer += "\n\nCaveats:\n- " + "\n- ".join(generated.caveats)
        if generated.next_steps:
            answer += "\n\nNext Steps:\n- " + "\n- ".join(generated.next_steps)
    else:
        answer = "Evidence was found, but the language-generation service is currently unavailable. Please review the cited BIS evidence below.\n\n"
        answer += generate_deterministic_fallback()

    # Shared evidence block
    evidence = [{
        "text": doc.content[:500] + "...",
        "document_title": doc.title,
        "source": doc.authority,
        "source_url": doc.source_url,
        "verification_status": "authoritative",
        "document_type": doc.source_type
    }]

    sources = [{
        "name": doc.authority,
        "url": doc.source_url,
        "document": doc.standard_number or doc.title or doc.document_id
    }]

    return {
        "intent": intent,
        "answer": answer,
        "evidence": evidence,
        "sources": sources,
        "confidence": 0.85 if is_grounded else 0.3,
        "needs_verification": not is_grounded
    }
