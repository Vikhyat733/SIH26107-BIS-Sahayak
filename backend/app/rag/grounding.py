import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def filter_grounded_candidates(query: str, ranked_candidates: List[Dict[str, Any]], intent: str) -> List[Dict[str, Any]]:
    """
    Deterministic grounding gate.
    Returns all candidates that are sufficient to answer the query.
    """
    grounded = []
    
    for cand in ranked_candidates:
        score = cand.get("rerank_score", cand.get("retrieval_score", 0))
        signals = cand.get("signals", {})
        doc = cand["document"]
        
        # 1. Is the evidence relevant enough?
        is_standard_query = intent in ("STANDARD_LOOKUP", "standard_recommendation")
        is_standard_result = doc.source_type in ("standard", "qco")
        
        min_score = 0.30 if (is_standard_query or is_standard_result) else 0.25
        
        if score < min_score:
            continue
            
        # Extra safety for ambiguous queries
        if is_standard_query or is_standard_result:
            has_id = signals.get("identifier_match", False)
            has_alias = signals.get("alias_score", 0) >= 1.0
            has_strong_semantic = signals.get("semantic_score", 0) >= 0.75
            
            if not (has_id or has_alias or has_strong_semantic):
                continue
            
        # 2. Is the evidence authoritative?
        if doc.authority != "Bureau of Indian Standards":
            continue
            
        # 3. Is the evidence sufficient for the requested intent?
        if is_standard_query and doc.source_type not in ("standard", "qco"):
            continue
            
        grounded.append(cand)
        
    if grounded:
        logger.info(f"Grounding passed. Selected {len(grounded)} docs. Top doc: {grounded[0]['document'].document_id} with score {grounded[0].get('rerank_score')}")
    else:
        logger.warning(f"Grounding failed for query '{query}'. No evidence met thresholds.")
        
    return grounded

def check_grounding(query: str, ranked_candidates: List[Dict[str, Any]], intent: str) -> bool:
    """Legacy boolean check for tests."""
    return len(filter_grounded_candidates(query, ranked_candidates, intent)) > 0
