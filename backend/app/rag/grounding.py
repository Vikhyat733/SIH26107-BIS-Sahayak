import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def check_grounding(query: str, ranked_candidates: List[Dict[str, Any]], intent: str) -> bool:
    """
    Deterministic grounding gate.
    Returns True if the top candidate is sufficient to answer the query.
    """
    # 1. Is there evidence?
    if not ranked_candidates:
        logger.warning("Grounding failed: No evidence candidates provided.")
        return False
        
    top_cand = ranked_candidates[0]
    score = top_cand.get("rerank_score", top_cand.get("retrieval_score", 0))
    signals = top_cand.get("signals", {})
    doc = top_cand["document"]
    
    # 2. Is the evidence relevant enough?
    # Our normalized score is bounded [0.0, 1.0].
    # We require a direct standard match, a specific alias match, or very strong lexical similarity.
    # A standard match gives +0.45. A specific alias gives +0.35.
    is_standard_query = intent in ("STANDARD_LOOKUP", "standard_recommendation")
    is_standard_result = doc.source_type in ("standard", "qco")
    
    # If the user asked for a standard OR we are about to return a standard, require high confidence
    min_score = 0.30 if (is_standard_query or is_standard_result) else 0.05
    
    if score < min_score:
        logger.warning(f"Grounding failed: Top evidence score ({score}) too low for query '{query}'. (Threshold: {min_score})")
        return False
        
    # Extra safety for ambiguous queries like "steel standard" (score might be BM25 0.10 + Title 0.10)
    # If it's a standard lookup or result, we need an identifier, specific alias, or strong semantic match.
    if is_standard_query or is_standard_result:
        has_id = signals.get("identifier_match", False)
        has_alias = signals.get("alias_score", 0) >= 1.0
        has_strong_semantic = signals.get("semantic_score", 0) >= 0.75
        
        if not (has_id or has_alias or has_strong_semantic):
            logger.warning(f"Grounding failed: Query '{query}' lacks specific entity, identifier match, or strong semantic link. Likely ambiguous.")
            return False
        
    # 3. Is the evidence authoritative?
    if doc.authority != "Bureau of Indian Standards":
        logger.warning(f"Grounding failed: Top evidence authority ({doc.authority}) is not BIS.")
        return False
        
    # 4. Is the evidence sufficient for the requested intent?
    if is_standard_query and doc.source_type not in ("standard", "qco"):
        logger.warning(f"Grounding failed: Intent {intent} requires standard/qco, but got {doc.source_type}.")
        return False
        
    logger.info(f"Grounding passed. Selected doc: {doc.document_id} with score {score}. Reasons: {top_cand.get('reasons')}")
    return True
