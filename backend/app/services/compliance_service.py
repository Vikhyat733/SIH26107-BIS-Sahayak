from typing import Any, Dict, Optional
import json
import io
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from ..core.config import STANDARDS_DIR
from ..engine import DeterministicEvaluator, FourStageVerifier

_evaluator = DeterministicEvaluator(schemas_dir=str(STANDARDS_DIR))
_verifier = FourStageVerifier()


def audit_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _evaluator.auto_audit_certificate(payload).model_dump()


import logging
import re

logger = logging.getLogger(__name__)

def _extract_data_from_text(text: str) -> dict:
    logger.debug(f"Extracted text length: {len(text)}")
    logger.debug(f"First 1000 chars: {text[:1000]}")
    logger.debug(f"IS 1786:2008 in text: {'IS 1786:2008' in text}")

    report_data = {"parameters": {}}
    
    # 1. Standard Extraction
    std_match = re.search(r'(?:IS|Indian\s+Standard)\s*(\d+)(?:\s*[:/\-]\s*(\d+))?', text, re.IGNORECASE)
    if std_match:
        std_num = std_match.group(1)
        std_year = std_match.group(2)
        if std_year:
            report_data["standard"] = f"IS {std_num}:{std_year}"
        else:
            report_data["standard"] = f"IS {std_num}"

    # 2. Product Extraction
    product_match = re.search(r'(High Strength Deformed Steel Bars(?: for Concrete Reinforcement)?|Drinking Water|Packaged Drinking Water)', text, re.IGNORECASE)
    if product_match:
        # Standardize capitalization
        report_data["product"] = product_match.group(1)

    # Grade Extraction
    grade_match = re.search(r'Grade(?:\s*:)?\s*(Fe\s*\d+[A-Z]*)', text, re.IGNORECASE)
    if grade_match:
        report_data["grade"] = grade_match.group(1).upper()

    # Batch/Heat extraction (if possible)
    heat_match = re.search(r'Heat\s+No(?:\.|umber)?(?:\s*:)?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
    if heat_match:
        report_data["heat_number"] = heat_match.group(1)
        
    batch_match = re.search(r'Batch\s+No(?:\.|umber)?(?:\s*:)?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
    if batch_match:
        report_data["batch_number"] = batch_match.group(1)

    # 3. Parameter Extraction
    param_patterns = {
        "yield_strength": r'(?:Yield\s+Strength|Yield\s+Stress)(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "tensile_strength": r'(?:Tensile\s+Strength|Ultimate\s+Tensile\s+Strength)(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "elongation": r'Elongation(?:\s*%)?(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "carbon": r'Carbon(?:\s*%)?(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "manganese": r'Manganese(?:\s*%)?(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "sulphur": r'(?:Sulphur|Sulfur)(?:\s*%)?(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "phosphorus": r'Phosphorus(?:\s*%)?(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "carbon_equivalent": r'Carbon\s+Equivalent(?:\s*%)?(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "nominal_diameter": r'Nominal\s+Diameter(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "ph_value": r'pH(?:\s*Value)?(?:\s*:)?\s*(\d+(?:\.\d+)?)',
        "turbidity": r'Turbidity(?:\s*:)?\s*(\d+(?:\.\d+)?)'
    }

    for key, pattern in param_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            unit = ""
            if key in ["yield_strength", "tensile_strength"]: unit = "MPa"
            elif key in ["elongation", "carbon", "manganese", "sulphur", "phosphorus", "carbon_equivalent"]: unit = "%"
            elif key == "nominal_diameter": unit = "mm"
            
            report_data["parameters"][key] = {"value": val, "unit": unit}

    return report_data


def analyze_document(filename: str, file_content: bytes, standard: Optional[str] = None, product: Optional[str] = None) -> Dict[str, Any]:
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext not in ['json', 'pdf', 'txt', 'csv']:
        return _review_result(filename, ext, standard, product, f"Unsupported file type: {ext}. Only PDF, TXT, JSON, CSV are supported.")

    report_data = {}
    if ext == 'json':
        try:
            report_data = json.loads(file_content.decode('utf-8'))
        except Exception:
            return _review_result(filename, ext, standard, product, "Required value could not be reliably extracted from the submitted document (invalid JSON).")
    elif ext == 'pdf':
        if not PdfReader:
            return _review_result(filename, ext, standard, product, "PDF extraction library not available.")
        try:
            reader = PdfReader(io.BytesIO(file_content))
            text = "".join(page.extract_text() or "" for page in reader.pages)
            report_data = _extract_data_from_text(text)
            
            # Fallback to pure JSON if it's somehow wrapped in PDF and regex failed to find any params
            if not report_data.get("standard") and not report_data["parameters"]:
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    report_data = json.loads(text[start:end+1])
        except Exception as e:
             return _review_result(filename, ext, standard, product, f"Required value could not be reliably extracted from the submitted document. Error: {str(e)}")
    else: # txt or csv
        try:
            text = file_content.decode('utf-8')
            report_data = _extract_data_from_text(text)
            
            # Fallback to JSON
            if not report_data.get("standard") and not report_data["parameters"]:
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    report_data = json.loads(text[start:end+1])
        except Exception:
             return _review_result(filename, ext, standard, product, "Required value could not be reliably extracted from the submitted document.")

    if standard and not report_data.get("standard"):
        report_data["standard"] = standard
    if product and not report_data.get("product"):
        report_data["product"] = product

    try:
        raw_result = _evaluator.auto_audit_certificate(report_data)
        return _format_result(raw_result, filename, ext)
    except Exception as e:
        return _review_result(filename, ext, standard, product, f"Compliance could not be determined because the applicable standard could not be established or data was missing. Error: {str(e)}")

def _review_result(filename, ext, standard, product, summary):
    return {
        "overall_status": "REVIEW",
        "standard": {"number": standard or "Unknown", "title": "Unknown"},
        "product": product or "Unknown",
        "grade": "Unknown",
        "document": {"filename": filename, "type": ext},
        "summary": summary,
        "checks": [],
        "missing_fields": [],
        "warnings": [],
        "verification": {"method": "deterministic", "source": "BIS standard schema"}
    }

def _format_result(res, filename, ext):
    checks = []
    has_fail = False
    
    for r in res.results:
        st = r.status
        if st == "FAIL":
            has_fail = True
        checks.append({
            "parameter": r.parameter_name,
            "reported_value": str(r.measured_value),
            "requirement": f"Min: {r.standard_min if r.standard_min is not None else 'N/A'}, Max: {r.standard_max if r.standard_max is not None else 'N/A'}",
            "unit": r.unit,
            "status": st,
            "reason": r.remarks,
            "evidence": r.clause_citation
        })
        
    overall = "PASS" if not has_fail else "FAIL"
    if res.overall_status == "NON-CONFORMING (FAIL)":
        overall = "FAIL"
        
    return {
        "overall_status": overall,
        "standard": {
            "number": res.standard_code,
            "title": "Extracted standard"
        },
        "product": res.product_name,
        "grade": getattr(res, "grade", "Unknown"),
        "document": {
            "filename": filename,
            "type": ext
        },
        "summary": f"Evaluated {res.total_parameters_checked} parameters. Passed: {res.passed_count}, Failed: {res.failed_count}",
        "checks": checks,
        "missing_fields": [],
        "warnings": res.violations,
        "verification": {
            "method": "deterministic",
            "source": "BIS standard schema"
        }
    }


def verify_identifier(identifier: str, target_grade: str | None = None, target_size_mm: int | None = None) -> Dict[str, Any]:
    kind = _verifier.detect_identifier_type(identifier)
    if kind == "ISI_CML":
        result = _verifier.verify_isi_license(identifier, target_grade=target_grade, target_size_mm=target_size_mm)
    elif kind == "CRS_REGISTRATION":
        result = _verifier.verify_crs_registration(identifier)
    else:
        result = _verifier.verify_hallmark_huid(identifier)
    return result.model_dump()
