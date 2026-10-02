from typing import List, Dict, Any
from ..services.standards_service import search_standards, qco_search

def retrieve_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    # Hybrid retrieval dummy for now (uses keyword search)
    standards = search_standards(query)
    qcos = qco_search(query)
    
    results = []
    for s in standards:
        results.append({
            "id": s["id"],
            "title": s.get("title", ""),
            "content": s.get("title", "") + " " + s.get("standard", ""),
            "type": "standard",
            "source": s.get("source", "BIS knowledge seed")
        })
    
    for q in qcos:
        results.append({
            "id": q.get("id", "qco"),
            "title": q.get("product_name", ""),
            "content": str(q),
            "type": "qco",
            "source": "BIS QCO registry"
        })
        
    return results[:top_k]
