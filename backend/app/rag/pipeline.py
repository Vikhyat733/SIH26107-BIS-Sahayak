import logging
from typing import Dict, Any, List
from .retrieval import retrieve_documents
from .reranking import rerank
from .grounding import check_grounding

logger = logging.getLogger("rag_pipeline")
logging.basicConfig(level=logging.INFO)

def run_rag_pipeline(query: str) -> Dict[str, Any]:
    logger.info(f"Retrieval started for query: '{query}'")
    
    # 1. Retrieve
    docs = retrieve_documents(query)
    logger.info(f"Documents retrieved: {len(docs)}")
    
    # 2. Rerank
    ranked_docs = rerank(query, docs)
    
    # 3. Formulate Answer
    logger.info("LLM/explanation stage started")
    if not ranked_docs:
        answer = "I couldn't find sufficient authoritative evidence in the current knowledge base to answer this reliably."
        is_grounded = False
        confidence = 0.0
    else:
        # Generate an answer grounded ONLY in retrieved evidence
        top_doc = ranked_docs[0]
        logger.info(f"Evidence selected: {top_doc.get('id')}")
        if top_doc.get("type") == "standard":
            answer = f"According to the BIS knowledge base, the applicable standard is {top_doc.get('id')} ({top_doc.get('title')})."
        elif top_doc.get("type") == "qco":
            answer = f"Found a relevant Quality Control Order (QCO) for {top_doc.get('title')}."
        else:
            answer = f"Found relevant information in the authoritative sources."
            
        is_grounded = check_grounding(answer, ranked_docs)
        confidence = 0.85 if is_grounded else 0.3

    sources = list(set([doc.get("source", "Unknown") for doc in ranked_docs]))

    logger.info(f"Response generated. Grounded: {is_grounded}")
    
    return {
        "answer": answer,
        "documents": ranked_docs,
        "sources": sources,
        "confidence": confidence,
        "grounded": is_grounded,
        "needs_verification": not is_grounded
    }
