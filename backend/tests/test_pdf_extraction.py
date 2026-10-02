import pytest
from app.services.compliance_service import _extract_data_from_text

def test_extract_data_from_text():
    sample_text = """
    IS 1786:2008
    High Strength Deformed Steel Bars for Concrete Reinforcement
    Grade: Fe 500D
    Yield Strength: 535 MPa
    Tensile Strength: 610 MPa
    Elongation: 20%
    Carbon: 0.20%
    Manganese: 1.20%
    Sulphur: 0.025%
    Phosphorus: 0.025%
    Nominal Diameter: 16 mm
    """
    
    extracted = _extract_data_from_text(sample_text)
    
    assert extracted.get("standard") == "IS 1786:2008"
    assert extracted.get("product") == "High Strength Deformed Steel Bars for Concrete Reinforcement"
    assert extracted.get("grade") == "FE 500D"
    
    params = extracted.get("parameters", {})
    assert params.get("yield_strength", {}).get("value") == 535.0
    assert params.get("tensile_strength", {}).get("value") == 610.0
    assert params.get("elongation", {}).get("value") == 20.0
    assert params.get("carbon", {}).get("value") == 0.20
    assert params.get("manganese", {}).get("value") == 1.20
    assert params.get("sulphur", {}).get("value") == 0.025
    assert params.get("phosphorus", {}).get("value") == 0.025
    assert params.get("nominal_diameter", {}).get("value") == 16.0

def test_extract_alternate_standard_formats():
    text1 = "Indian Standard 1786 - 2008"
    assert _extract_data_from_text(text1).get("standard") == "IS 1786:2008"
    
    text2 = "IS1786/2008"
    assert _extract_data_from_text(text2).get("standard") == "IS 1786:2008"
