import json
import os
from pathlib import Path
from typing import Dict, Any, List

GENERAL_KB_DIR = Path(__file__).resolve().parents[2] / "data" / "general"

DEFAULT_KB = [
  {
    'id': 'bis_what_is',
    'title': 'What is BIS?',
    'category': 'General',
    'content': 'The Bureau of Indian Standards (BIS) is the National Standard Body of India established under the BIS Act 2016 for the harmonious development of the activities of standardization, marking and quality certification of goods.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'bis_certification',
    'title': 'Product Certification Overview',
    'search_queries': ['what is bis certification', 'bis certification', 'product certification'],
    'category': 'Certification',
    'content': 'BIS Product Certification Schemes provide third-party assurance of product quality, safety, and reliability. BIS certification is basically voluntary in nature. However, the Government can make compliance mandatory for specified products through Quality Control Orders (QCOs). For products covered by applicable QCOs, the relevant BIS certification and Standard Mark requirements apply according to the order.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/product-certification/',
    'section': 'Overview of Certification',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'isi_mark',
    'title': 'ISI Mark',
    'category': 'Certification',
    'content': 'The ISI mark is a standards-compliance mark for industrial products in India since 1955. It certifies that a product conforms to an Indian Standard (IS) developed by the Bureau of Indian Standards.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'bis_product_certification',
    'title': 'BIS Product Certification',
    'category': 'Certification',
    'content': 'The BIS Product Certification Scheme aims at providing third party assurance of quality, safety and reliability of products to the customer. The presence of the ISI Certification Mark on a product is an assurance of conformity to the specifications.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'bis_licensing',
    'title': 'BIS Licensing',
    'category': 'Certification',
    'content': 'BIS grants a licence based on assessment of the manufacturing infrastructure, production process, quality control and testing capabilities of a manufacturer through a visit to its manufacturing premises.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'certification_process_overview',
    'title': 'Certification Process Overview',
    'category': 'Certification',
    'content': 'The certification process generally involves application submission, preliminary inspection of manufacturing capability, testing of product samples, and finally, the grant of a license upon successful evaluation.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'qco_overview',
    'title': 'Quality Control Orders',
    'search_queries': ['what is a quality control order under bis', 'qco', 'quality control orders', 'quality control order under bis', 'quality control order'],
    'category': 'Regulatory',
    'content': 'A Quality Control Order (QCO) is issued by the Government of India making it mandatory for specific products to conform to the relevant Indian Standard and bear the Standard Mark (ISI Mark) under a license from BIS.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/quality-control-orders/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'testing_labs',
    'title': 'BIS Testing Laboratories',
    'category': 'Labs',
    'content': 'BIS operates its own testing laboratories and also recognizes private and government laboratories under the Laboratory Recognition Scheme (LRS) to test products for conformity to Indian Standards.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'standards_search',
    'title': 'Standards Search',
    'category': 'Standards',
    'content': 'Indian Standards can be searched and downloaded from the official BIS e-sale portal or through ManakMitra. Over 21,000 standards are available across various disciplines.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'hallmarking',
    'title': 'Hallmarking',
    'category': 'Certification',
    'content': 'Hallmarking is the accurate determination and official recording of the proportionate content of precious metal in precious metal articles. Hallmarks are thus official marks used in many countries as a guarantee of purity or fineness of precious metal articles.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  },
  {
    'id': 'bis_care',
    'title': 'BIS CARE App / Consumer Verification',
    'category': 'Consumer',
    'content': 'BIS CARE is the official mobile application of the Bureau of Indian Standards. It allows consumers to verify the authenticity of ISI-marked products, Hallmarked jewelry, and CRS-registered electronic goods.',
    'source': 'Bureau of Indian Standards',
    'source_url': 'https://www.bis.gov.in/',
    'verification_status': 'authoritative',
    'document_type': 'general_knowledge'
  }
]

def init_kb():
    if not GENERAL_KB_DIR.exists():
        GENERAL_KB_DIR.mkdir(parents=True)
    for item in DEFAULT_KB:
        p = GENERAL_KB_DIR / f"{item['id']}.json"
        if not p.exists():
            p.write_text(json.dumps(item, indent=2), encoding='utf-8')

def load_general_kb() -> List[Dict[str, Any]]:
    init_kb()
    kb = []
    for p in GENERAL_KB_DIR.glob("*.json"):
        kb.append(json.loads(p.read_text(encoding="utf-8")))
    return kb

def answer_general_query(query: str) -> Dict[str, Any]:
    q = query.lower().strip()
    kb = load_general_kb()
    
    # 1. Generate keywords
    stopwords = {"what", "which", "how", "does", "do", "the", "a", "an", "is", "are", "under", "of", "and", "or"}
    keywords = [kw.strip("?.,!") for kw in q.split() if kw.strip("?.,!") not in stopwords and len(kw.strip("?.,!")) >= 3]
    
    # 2. Retrieve relevant authoritative BIS knowledge
    best_match = None
    best_score = 0
    for doc in kb:
        score = 0
        content_blob = (doc.get("title", "") + " " + doc.get("content", "")).lower()
        for kw in keywords:
            if kw in content_blob:
                score += 1
            if kw in doc.get("title", "").lower():
                score += 3
        
        # Exact title or search_queries match gives a huge boost
        clean_q = q.replace("?", "").strip()
        search_qs = doc.get("search_queries", [])
        if clean_q == doc.get("title", "").lower() or clean_q in doc.get("title", "").lower():
            score += 10
        elif any(clean_q == sq.lower() for sq in search_qs):
            score += 10
        elif any(sq.lower() in clean_q for sq in search_qs):
            score += 5
            
        if score > best_score:
            best_score = score
            best_match = doc
            
    # 3. Select evidence & 4. Generate grounded response
    if best_match and best_score > 0:
        return {
            "intent": "BIS_GENERAL_QUERY",
            "answer": best_match["content"],
            "evidence": [
                {
                    "text": best_match["content"],
                    "document_title": best_match.get("title", ""),
                    "section": best_match.get("section", "Overview"),
                    "source": best_match.get("source", "Bureau of Indian Standards"),
                    "source_url": best_match.get("source_url", "https://www.bis.gov.in/"),
                    "verification_status": "authoritative"
                }
            ],
            "sources": [
                {
                    "name": best_match.get("source", "Bureau of Indian Standards"),
                    "url": best_match.get("source_url", "https://www.bis.gov.in/"),
                    "document": best_match.get("title", best_match.get("id"))
                }
            ],
            "confidence": 0.9,
            "needs_verification": False
        }
    else:
        # Safe insufficient-evidence response
        return {
            "intent": "BIS_GENERAL_QUERY",
            "answer": "This question could not be answered reliably from the current knowledge base.",
            "evidence": [],
            "sources": [],
            "confidence": 0.0,
            "needs_verification": True
        }
