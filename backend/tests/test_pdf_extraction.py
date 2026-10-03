import pytest
from app.services.compliance_service import _extract_data_from_text
from app.engine.deterministic_evaluator import DeterministicEvaluator

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
    
    mech = extracted.get("mechanical_properties", {})
    assert mech.get("yield_stress") == 535.0
    assert mech.get("tensile_strength") == 610.0
    assert mech.get("elongation") == 20.0
    
    chem = extracted.get("chemical_composition", {})
    assert chem.get("carbon") == 0.20
    assert chem.get("manganese") == 1.20
    assert chem.get("sulfur") == 0.025
    assert chem.get("phosphorus") == 0.025
    
    params = extracted.get("parameters", {})
    assert params.get("nominal_diameter", {}).get("value") == 16.0

def test_extract_alternate_standard_formats():
    text1 = "Indian Standard 1786 - 2008"
    assert _extract_data_from_text(text1).get("standard") == "IS 1786:2008"
    
    text2 = "IS1786/2008"
    assert _extract_data_from_text(text2).get("standard") == "IS 1786:2008"

def test_extract_aliases_and_missing_values():
    sample_text = """
    IS 1786:2008
    0.2% Proof Stress: 535.5 N/mm2
    Ultimate Tensile Strength  :  610 N/mm2
    Total Elongation at Maximum Force: 6.5 %
    Carbon: unparseable_value
    """
    
    extracted = _extract_data_from_text(sample_text)
    
    mech = extracted.get("mechanical_properties", {})
    assert mech.get("yield_stress") == 535.5
    assert mech.get("tensile_strength") == 610.0
    assert mech.get("total_elongation_at_max_force") == 6.5
    
    chem = extracted.get("chemical_composition", {})
    # Unparseable carbon value should not be extracted as 0.0
    assert "carbon" not in chem

def test_engine_missing_values_become_review():
    evaluator = DeterministicEvaluator()
    # Provide missing sulfur, unparseable values should become REVIEW
    data = {
        "product_details": {"standard": "IS 1786:2008", "grade": "Fe 500"},
        "chemical_composition": {
            "carbon": 0.20
            # missing sulfur, phosphorus, etc.
        },
        "mechanical_properties": {
            "yield_stress": 535.0
            # missing tensile_strength
        }
    }
    
    report = evaluator.auto_audit_certificate(data)
    
    # Check that overall status is REVIEW
    assert report.overall_status == "REVIEW"
    
    # Check that missing fields have REVIEW status
    results_by_key = {r.parameter_key: r.status for r in report.results}
    assert results_by_key.get("sulfur") == "REVIEW"
    assert results_by_key.get("tensile_strength") == "REVIEW"
    assert results_by_key.get("carbon") == "PASS" # 0.20 <= 0.30 (Fe 500)

def test_extract_tabular_chemical_labels_and_missing_elongation():
    # PDF tabular extraction often includes (C), (Mn), etc. and puts value on next line
    tabular_text = """
    IS 1786:2008
    Carbon (C)
    0.20
    %
    Manganese (Mn)
    1.20
    %
    Sulphur (S)
    0.025
    %
    Phosphorus (P)
    0.025
    %
    """
    
    extracted = _extract_data_from_text(tabular_text)
    
    chem = extracted.get("chemical_composition", {})
    assert chem.get("carbon") == 0.20
    assert chem.get("manganese") == 1.20
    assert chem.get("sulfur") == 0.025
    assert chem.get("phosphorus") == 0.025
    
    # Verify genuinely absent Total Elongation remains absent
    mech = extracted.get("mechanical_properties", {})
    assert "total_elongation_at_max_force" not in mech
    
    # Run through deterministic evaluator to ensure it correctly triggers REVIEW
    evaluator = DeterministicEvaluator()
    data = {
        "product_details": {"standard": "IS 1786:2008", "grade": "Fe 500D"},
        "chemical_composition": chem,
        "mechanical_properties": mech
    }
    report = evaluator.auto_audit_certificate(data)
    
    # Total Elongation is mandatory for Fe 500D (min 5.0), so it should be REVIEW when absent
    results_by_key = {r.parameter_key: r.status for r in report.results}
    assert results_by_key.get("total_elongation_at_max_force") == "REVIEW"

