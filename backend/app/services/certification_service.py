from typing import Any, Dict, List
import json
from .standards_service import recommend_standards
from ..core.config import QCO_FILE

def get_certification_info(query: str) -> Dict[str, Any]:
    q = query.lower().strip()
    
    # 1. Try to find the applicable standard based on the query
    recs = recommend_standards(query)
    
    if not recs:
        # Safe refusal
        return {
            "intent": "CERTIFICATION_QUERY",
            "answer": "Certification/QCO applicability could not be verified from the available authoritative BIS evidence.",
            "certification_data": {
                "product": query,
                "standard": "Unknown",
                "certification_status": "unknown",
                "qco": {
                    "applicable": False,
                    "title": "",
                    "source_url": ""
                },
                "scheme": {
                    "scheme_name": "",
                    "scheme_number": "",
                    "source_url": ""
                },
                "next_steps": []
            },
            "evidence": [],
            "sources": [],
            "confidence": 0.0,
            "needs_verification": True
        }
        
    # We have a recommended standard
    best_rec = recs[0]
    standard_number = best_rec.get("standard_number", "")
    product_title = best_rec.get("title", "")
    
    # 2. Check QCO registry for this standard
    qco_registry = json.loads(QCO_FILE.read_text(encoding="utf-8")) if QCO_FILE.exists() else []
    
    applicable_qco = None
    for qco in qco_registry:
        for app_std in qco.get("applicable_standards", []):
            if standard_number and standard_number.lower() in app_std.get("standard", "").lower():
                applicable_qco = qco
                break
        if applicable_qco:
            break
            
    if applicable_qco:
        # We have mandatory certification evidence
        cert_status = "mandatory"
        qco_title = applicable_qco.get("title", "")
        qco_source_url = "https://www.bis.gov.in/quality-control-orders/"
        scheme_name = applicable_qco.get("scheme", "")
        
        answer = f"Yes, BIS certification is mandatory for {product_title} under the {qco_title}."
        
        evidence = [
            {
                "text": f"{product_title} is covered under {qco_title}. Applicable standard: {standard_number}. Status: {applicable_qco.get('status', 'Active & Mandatory')}.",
                "document_title": qco_title,
                "section": "Applicable Standards",
                "source": "Bureau of Indian Standards",
                "source_url": qco_source_url,
                "verification_status": "authoritative"
            }
        ]
        sources = [
            {
                "name": "Bureau of Indian Standards",
                "url": qco_source_url,
                "document": qco_title
            }
        ]
        
        cert_data = {
            "product": product_title,
            "standard": standard_number,
            "certification_status": cert_status,
            "qco": {
                "applicable": True,
                "title": qco_title,
                "source_url": qco_source_url
            },
            "scheme": {
                "scheme_name": scheme_name,
                "scheme_number": "Scheme-I",
                "source_url": "https://www.bis.gov.in/product-certification/"
            },
            "next_steps": [
                "Verify MSME exemption rules if applicable.",
                f"Obtain a license for {scheme_name} from BIS.",
                "Ensure product testing is done at BIS recognized labs."
            ]
        }
        
        return {
            "intent": "CERTIFICATION_QUERY",
            "answer": answer,
            "certification_data": cert_data,
            "evidence": evidence,
            "sources": sources,
            "confidence": 0.9,
            "needs_verification": False
        }
    else:
        # Standard exists, but no QCO evidence found
        cert_data = {
            "product": product_title,
            "standard": standard_number,
            "certification_status": "unknown",
            "qco": {
                "applicable": False,
                "title": "Not established",
                "source_url": ""
            },
            "scheme": {
                "scheme_name": "Product Certification Scheme",
                "scheme_number": "Scheme-I",
                "source_url": "https://www.bis.gov.in/product-certification/"
            },
            "next_steps": [
                "Verify current QCO notifications on the official BIS website.",
                "If voluntary, you can still apply for BIS certification for quality assurance."
            ]
        }
        
        return {
            "intent": "CERTIFICATION_QUERY",
            "answer": "Certification/QCO applicability could not be verified from the available authoritative BIS evidence. While an Indian Standard exists, it is not listed in the provided Quality Control Orders registry.",
            "certification_data": cert_data,
            "evidence": best_rec.get("evidence", []),
            "sources": [],
            "confidence": 0.0,
            "needs_verification": True
        }
