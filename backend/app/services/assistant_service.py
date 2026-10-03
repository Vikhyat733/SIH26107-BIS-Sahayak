from typing import Any, Dict, List
from .standards_service import search_standards, qco_search, recommend_standards
from .bis_general_service import answer_general_query
from ..rag.pipeline import run_rag_pipeline
from .certification_service import get_certification_info
from .laboratory_service import find_laboratories
from ..rag.query_understanding import QueryUnderstandingService

qu_service = QueryUnderstandingService()

def answer(query: str, language: str = "en") -> Dict[str, Any]:
    # Phase 3A: Query Understanding
    understanding = qu_service.understand(query)
    intent = understanding.intent
    
    # 1. Check for immediate clarification needs
    if understanding.needs_clarification:
        return {
            "intent": intent,
            "answer": understanding.clarification_reason,
            "evidence": [],
            "sources": [],
            "confidence": 0.0,
            "needs_verification": True,
            "query_understanding": {
                "specificity": understanding.specificity,
                "entities": [e.canonical for e in understanding.product_entities]
            }
        }
        
    # 2. Routing based on detected intent
    if intent in ("standard_recommendation", "STANDARD_LOOKUP"): 
        # Pass the pre-processed plan to the pipeline or just the original query as baseline
        return run_rag_pipeline(query, intent=intent)

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

    if intent == "HALLMARKING_QUERY":
        from .hallmarking_service import get_hallmarking_guidance
        hm_res = get_hallmarking_guidance(query)
        return {
            "answer": hm_res["message"],
            "intent": intent,
            "sources": [],
            "evidence": [],
            "confidence": 0.85,
            "needs_verification": True
        }

    if intent == "COMPLIANCE_QUERY":
        return {
            "answer": "To check compliance, please upload your Material Test Certificate (MTC) through the Compliance Check feature.",
            "intent": intent,
            "sources": [],
            "evidence": [],
            "confidence": 1.0,
            "needs_verification": False
        }

    # 3. Default routing (General queries, QCO, etc.)
    # QCO_QUERY and BIS_GENERAL_QUERY route to RAG
    return run_rag_pipeline(query, intent=intent)
