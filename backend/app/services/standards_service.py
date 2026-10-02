import json
from typing import Any, Dict, List
from ..core.config import STANDARDS_DIR, QCO_FILE


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def list_standards() -> List[Dict[str, Any]]:
    items = []
    for path in sorted(STANDARDS_DIR.glob("*.json")):
        data = _load_json(path)
        items.append({
            "id": path.stem,
            "title": data.get("title", path.stem),
            "standard": data.get("standard", path.stem.replace("_", ":", 1)),
            "source": "BIS knowledge seed / supplied project",
        })
    return items


def search_standards(query: str) -> List[Dict[str, Any]]:
    q = query.lower().strip()
    if not q:
        return []
        
    # 1. Product Entity Normalization
    entity_mappings = {
        "IS_1786_2008": [
            "tmt", "tmt bar", "tmt bars", "tmt reinforcement bar", "tmt reinforcement bars",
            "reinforcement bar", "reinforcement bars", "deformed steel bar",
            "high strength deformed steel bars", "steel reinforcement bar", "steel bars for concrete reinforcement"
        ],
        "IS_10500_2012": [
            "drinking water", "potable water"
        ]
    }
    
    # 2. Stopwords and generic words to exclude from keyword search
    # Extended to include words like product, standard, certification, mandatory, bar
    stopwords = {
        "which", "standard", "standards", "applies", "to", "for", "the", "a", "an", "is", "what", "are", 
        "bis", "does", "do", "require", "mandatory", "certification", "get", "how", "need", 
        "product", "products", "bar", "bars"
    }
    keywords = [kw.strip("?.,!") for kw in q.split() if kw.strip("?.,!") not in stopwords and len(kw.strip("?.,!")) > 2]
    
    import re
    results = []
    
    for path in sorted(STANDARDS_DIR.glob("*.json")):
        data = _load_json(path)
        blob = json.dumps(data, ensure_ascii=False).lower()
        title = data.get("title", "").lower()
        std_code = data.get("standard_code", path.stem).lower()
        
        score = 0
        
        # A & B. Exact product/entity match and Product synonym/alias match
        aliases = entity_mappings.get(path.stem, [])
        matched_entity = False
        
        # Check exact title match
        if title in q and len(title) > 5:
            score += 200
            matched_entity = True
            
        for alias in aliases:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, q):
                score += 100
                matched_entity = True
                break
                
        # C. Standard/product metadata match
        if any(kw in std_code for kw in keywords) and keywords:
            score += 50
        if any(kw in title for kw in keywords) and keywords:
            score += 30
            
        # D & E. Generic keyword match in blob (Semantic/vector fallback)
        # We only apply generic fallback if we haven't already strongly matched this entity, 
        # or we add it as a weak score that cannot override a strong entity match (score 100+).
        blob_matches = sum(1 for kw in keywords if kw in blob)
        if blob_matches > 0:
            score += (blob_matches * 5)
            
        if score > 0:
            results.append({
                "score": score,
                "id": path.stem,
                "standard": data.get("standard", path.stem.replace("_", ":", 1)),
                "title": data.get("title", path.stem),
                "source": "BIS knowledge seed / supplied project",
            })
            
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Do not remove score so callers can check confidence

        
    return results


def qco_search(query: str) -> List[Dict[str, Any]]:
    q = query.lower().strip()
    if not q:
        return []
    stopwords = {"which", "standard", "applies", "to", "for", "the", "a", "an", "is", "what", "are", "qco"}
    keywords = [kw for kw in q.split() if kw not in stopwords]
    registry = _load_json(QCO_FILE) if QCO_FILE.exists() else []
    out = []
    for item in registry:
        blob = json.dumps(item, ensure_ascii=False).lower()
        if any(kw in blob for kw in keywords):
            out.append(item)
    return out


def recommend_standards(product_description: str) -> List[Dict[str, Any]]:
    # Local deterministic retrieval
    standards = search_standards(product_description)
    results = []
    for s in standards:
        path = STANDARDS_DIR / f"{s['id']}.json"
        if path.exists():
            data = _load_json(path)
        else:
            data = {}
            
        results.append({
            "standard_number": data.get("standard_code", s.get("standard", s["id"])),
            "title": data.get("title", s.get("title", "")),
            "relevance": 0.85,
            "retrieval_reason": "Matched based on product description keywords.",
            "evidence": data.get("evidence", []),
            "source": data.get("source", "Bureau of Indian Standards"),
            "source_url": data.get("source_url", "https://www.bis.gov.in/"),
            "verification_status": data.get("verification_status", "unverified"),
            "document_type": data.get("document_type", "standard")
        })
    return results[:5]
