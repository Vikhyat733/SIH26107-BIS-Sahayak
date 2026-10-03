import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Structured Entity Mappings differentiating specific vs broad aliases
ENTITY_MAPPINGS = {
    "IS_1786_2008": [
        {"alias": "tmt", "type": "specific"},
        {"alias": "tmt bar", "type": "specific"},
        {"alias": "tmt bars", "type": "specific"},
        {"alias": "tmt reinforcement", "type": "specific"},
        {"alias": "deformed steel bar", "type": "specific"},
        {"alias": "high strength deformed steel", "type": "specific"},
        {"alias": "high strength reinforcement bar", "type": "specific"},
        {"alias": "reinforcement bar", "type": "broad"},
        {"alias": "reinforcement bars", "type": "broad"},
        {"alias": "steel reinforcement", "type": "broad"}
    ],
    "IS_10500_2012": [
        {"alias": "drinking water", "type": "specific"},
        {"alias": "potable water", "type": "specific"},
        {"alias": "water", "type": "broad"}
    ]
}

def extract_standard_identifiers(text: str) -> List[str]:
    """
    Extracts canonical standard numbers from text.
    Matches: IS 1786, IS 1786:2008, is 1786, IS-1786, Indian Standard 1786
    Returns core numbers like '1786' to allow version-agnostic matching.
    """
    if not text:
        return []
    # Match IS or Indian Standard followed by optional separators and digits
    pattern = r'\b(?:IS|Indian\s+Standard)[\s:-]*(\d+)'
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    return list(set(matches))

def calculate_title_similarity(query: str, title: str) -> float:
    if not title:
        return 0.0
    q_words = set(re.findall(r'\w+', query.lower()))
    t_words = set(re.findall(r'\w+', title.lower()))
    if not q_words or not t_words:
        return 0.0
    # simple overlap ratio
    overlap = len(q_words.intersection(t_words))
    return min(1.0, overlap / max(1, min(len(q_words), 5)))

def check_alias_match(query_lower: str, doc_id: str, doc_aliases: List[str] = None) -> float:
    """
    Returns 1.0 for specific alias match, 0.4 for broad match, 0.0 otherwise.
    """
    aliases = ENTITY_MAPPINGS.get(doc_id, [])
    
    # Also add inline document aliases (like search_queries from general KB)
    if doc_aliases:
        for a in doc_aliases:
            aliases.append({"alias": a, "type": "specific"})
            
    q_clean = re.sub(r'[^\w\s]', '', query_lower)
    best_match = 0.0
    for a in aliases:
        pattern = r'\b' + re.escape(a["alias"]) + r'\b'
        if re.search(pattern, q_clean):
            score = 1.0 if a["type"] == "specific" else 0.4
            best_match = max(best_match, score)
    return best_match

def normalize_bm25(score: float) -> float:
    """Normalize unbounded BM25 score to [0, 1.0] using a soft curve."""
    return score / (score + 5.0)

def rerank(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Bounded scoring model combining multiple signals.
    """
    q_lower = query.lower().strip()
    query_identifiers = extract_standard_identifiers(query)
    
    reranked = []
    for cand in candidates:
        doc = cand["document"]
        raw_bm25 = cand.get("bm25_score", cand.get("retrieval_score", 0.0))
        semantic_score = cand.get("semantic_score", 0.0)
        
        # 1. Normalize BM25
        bm25_norm = normalize_bm25(raw_bm25)
        
        # 2. Extract Identifier Match
        doc_identifiers = extract_standard_identifiers(doc.standard_number)
        if not doc_identifiers:
            doc_identifiers = extract_standard_identifiers(doc.document_id)
            
        has_identifier_match = False
        for qi in query_identifiers:
            if qi in doc_identifiers:
                has_identifier_match = True
                break
                
        identifier_score = 1.0 if has_identifier_match else 0.0
        
        # 3. Title Match
        title_score = calculate_title_similarity(query, doc.title)
        
        # 4. Alias/Entity Match
        alias_score = check_alias_match(q_lower, doc.document_id, doc.aliases)
        
        # 5. Semantic/Lexical Fusion
        # We give a small bonus if both methods retrieved it
        retrieval_agreement = 0.05 if (bm25_norm > 0 and semantic_score > 0) else 0.0
        
        # Calculate Bounded Final Score (Max 1.0)
        # Weights: ID=0.45, Alias=0.10, Title=0.05, BM25=0.05, Semantic=0.30, Agreement=0.05
        final_score = (
            (identifier_score * 0.45) +
            (alias_score * 0.10) +
            (title_score * 0.05) +
            (bm25_norm * 0.05) +
            (semantic_score * 0.30) +
            retrieval_agreement
        )
        final_score = min(1.0, final_score) # Ensure bounded
        
        # Explanation
        reasons = []
        if identifier_score > 0: reasons.append(f"exact identifier match ({doc_identifiers[0] if doc_identifiers else 'N/A'})")
        if alias_score == 1.0: reasons.append("specific entity match")
        if alias_score == 0.4: reasons.append("broad entity match")
        if title_score > 0.5: reasons.append("strong title relevance")
        if bm25_norm > 0.4: reasons.append("strong lexical relevance")
        if semantic_score > 0.7: reasons.append("strong semantic relevance")
        if retrieval_agreement > 0: reasons.append("retrieval agreement (lexical + semantic)")
        
        # Create new candidate with rich signals
        cand_copy = dict(cand)
        cand_copy["rerank_score"] = round(final_score, 4)
        cand_copy["signals"] = {
            "bm25_norm": round(bm25_norm, 3),
            "semantic_score": round(semantic_score, 3),
            "identifier_match": has_identifier_match,
            "title_score": round(title_score, 3),
            "alias_score": alias_score
        }
        cand_copy["reasons"] = reasons
        
        reranked.append(cand_copy)
        
    reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
    
    if reranked:
        top = reranked[0]
        logger.info(f"Reranked Top Doc: {top['document'].document_id} | Score: {top['rerank_score']} | Signals: {top['signals']}")
        
    return reranked
