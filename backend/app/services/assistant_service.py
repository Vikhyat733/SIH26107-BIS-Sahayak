from typing import Any, Dict, List
from .standards_service import search_standards, qco_search, recommend_standards
from .bis_general_service import answer_general_query
from ..rag.pipeline import run_rag_pipeline
from .certification_service import get_certification_info
from .laboratory_service import find_laboratories
import re

def answer(query: str, language: str = "en") -> Dict[str, Any]:
    q = query.lower().strip()
    
    # Classify intent
    intent = "BIS_GENERAL_QUERY"
    
    # Check for STANDARD_LOOKUP (e.g. "is 1786", "is 1786:2008", "IS:1786")
    if re.match(r"^is\s*:?\s*\d+(:\d{4})?$", q):
        intent = "STANDARD_LOOKUP"
    # Check for standard_recommendation
    elif any(k in q for k in ["which standard", "which bis standard", "standard applies to"]):
        intent = "standard_recommendation"
    elif len(q.split()) <= 3 and ("phone" in q or "tmt" in q or "mobile" in q):
        intent = "standard_recommendation"
    elif q.startswith("smx"):
        intent = "standard_recommendation"
        
    # Check for CERTIFICATION_QUERY
    if any(k in q for k in ["mandatory", "certification", "qco", "require bis", "how do i get"]):
        if not ("what is bis certification" in q or "what is a qco" in q or "what is a quality control order" in q):
            intent = "CERTIFICATION_QUERY"
            
    # Check for LAB_LOOKUP
    if any(k in q for k in ["test", "lab", "laboratory", "laboratories", "testing", "where can i get my product tested"]):
        if not ("what is a lab" in q):
            intent = "LAB_LOOKUP"
        
    # If it's a standard recommendation intent, we use the recommend flow
    if intent in ("standard_recommendation", "STANDARD_LOOKUP"): 
        recs = recommend_standards(query)
        if recs:
            answers = []
            sources = []
            for r in recs:
                std = r.get("standard_number", r.get("id"))
                title = r.get("title", "")
                product = title.split("—")[0].split("-")[0].strip().lower() if title else query.lower()
                answers.append(f"{std} is identified in the available BIS evidence as covering {product}.")
                
                sources.append({
                    "name": r.get("source", "Bureau of Indian Standards"),
                    "url": r.get("source_url", "https://www.bis.gov.in/"),
                    "document": std
                })
            
            answer_text = "\n".join(answers) + "\n\nVerify current applicability and regulatory requirements before compliance action."
            evidence = recs
            confidence = 0.85
            needs_verification = False
        else:
            answer_text = "No sufficiently supported BIS standard was found for this product in the current knowledge base.\n\nTry describing the product in more detail."
            evidence = []
            confidence = 0.0
            needs_verification = True
            sources = []
        
        return {
            "answer": answer_text,
            "intent": intent,
            "sources": sources,
            "evidence": evidence,
            "confidence": confidence,
            "needs_verification": needs_verification
        }

    if intent == "CERTIFICATION_QUERY":
        return get_certification_info(query)

    if intent == "LAB_LOOKUP":
        lab_res = find_laboratories(query=query)
        return {
            "answer": lab_res["message"],
            "intent": intent,
            "sources": [],
            "evidence": lab_res["results"],
            "confidence": 0.85,
            "needs_verification": True,
            "lab_metadata": {
                "standard": lab_res.get("extracted_standard"),
                "location": lab_res.get("extracted_location")
            }
        }

    # Use the general BIS service for general queries
    return answer_general_query(query)
