"""
MANAK AI - Test Suite for Deterministic Compliance Engine, 4-Stage Verifier & STI Planner
"""

import os
import json
import pytest
from app.engine.deterministic_evaluator import DeterministicEvaluator
from app.engine.four_stage_verifier import FourStageVerifier
from app.engine.sti_planner import STIPlanner


@pytest.fixture
def evaluator():
    return DeterministicEvaluator()


@pytest.fixture
def verifier():
    return FourStageVerifier()


# -------------------------------------------------------------
# 1. Carbon Equivalent & Mathematical Precision Tests
# -------------------------------------------------------------
def test_carbon_equivalent_formula_precision(evaluator):
    """
    Test CE formula: CE = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15
    C=0.20, Mn=0.60, Cr=0.05, Mo=0.03, V=0.02, Ni=0.03, Cu=0.03
    CE = 0.20 + (0.60/6) + (0.10/5) + (0.06/15)
       = 0.20 + 0.10 + 0.02 + 0.004 = 0.324
    """
    ce = evaluator.calculate_carbon_equivalent(
        carbon=0.20,
        manganese=0.60,
        chromium=0.05,
        molybdenum=0.03,
        vanadium=0.02,
        nickel=0.03,
        copper=0.03,
    )
    assert ce == 0.3240


def test_ts_ys_ratio_calculation(evaluator):
    """
    Test TS/YS ratio calculation: 615 / 535 = 1.1495
    """
    ratio = evaluator.calculate_ts_ys_ratio(tensile_strength=615.0, yield_stress=535.0)
    assert ratio == 1.1495
    # Zero division guard
    assert evaluator.calculate_ts_ys_ratio(500.0, 0.0) == 0.0


# -------------------------------------------------------------
# 2. MTC Certificate Verification Tests (Pass vs Fail)
# -------------------------------------------------------------
def test_sample_mtc_pass_conformance(evaluator):
    """
    Tests that sample_mtc_pass.json (IS 1786 Fe 500D) passes all checks with zero violations.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pass_file = os.path.join(base_dir, "data", "demo_reports", "sample_mtc_pass.json")
    
    with open(pass_file, "r", encoding="utf-8") as f:
        mtc_data = json.load(f)

    report = evaluator.auto_audit_certificate(mtc_data)
    assert report.overall_status == "CONFORMING (PASS)"
    assert report.failed_count == 0
    assert report.compliance_score_pct == 100.0
    assert len(report.violations) == 0
    assert report.grade == "Fe 500D"
    assert report.carbon_equivalent is not None
    assert report.carbon_equivalent <= 0.42


def test_sample_mtc_fail_violations_detected(evaluator):
    """
    Tests that sample_mtc_fail.json is correctly flagged as NON-CONFORMING
    with explicit violations for Carbon (0.28% > 0.25%), Sulfur (0.048% > 0.040%),
    and TS/YS ratio (1.08 < 1.10).
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fail_file = os.path.join(base_dir, "data", "demo_reports", "sample_mtc_fail.json")
    
    with open(fail_file, "r", encoding="utf-8") as f:
        mtc_data = json.load(f)

    report = evaluator.auto_audit_certificate(mtc_data)
    assert report.overall_status == "NON-CONFORMING (FAIL)"
    assert report.failed_count >= 3
    assert report.compliance_score_pct < 100.0

    # Verify specific parameter failures
    param_status = {r.parameter_key: r.status for r in report.results}
    assert param_status.get("carbon") == "FAIL"
    assert param_status.get("sulfur") == "FAIL"
    assert param_status.get("ts_ys_ratio") == "FAIL"


def test_drinking_water_audit(evaluator):
    """
    Tests drinking water test evaluation against IS 10500:2012.
    """
    sample_data = {
        "standard": "IS 10500:2012",
        "sample_id": "WATER-MUNICIPAL-01",
        "parameters": {
            "ph_value": 7.4,
            "turbidity": 0.8,
            "total_dissolved_solids": 240.0,
            "lead": 0.005,
            "arsenic": 0.002,
        },
    }
    report = evaluator.auto_audit_certificate(sample_data)
    assert report.overall_status == "CONFORMING (PASS)"
    assert report.failed_count == 0


def test_adversarial_stress_test_certificate(evaluator):
    """
    Tests adversarial certificate with extreme out-of-bound values and 0.0 yield stress
    (division by zero test). Verifies zero crashes and 100% detection of all critical violations.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    adv_file = os.path.join(base_dir, "data", "demo_reports", "sample_adversarial_stress_test.json")
    with open(adv_file, "r", encoding="utf-8") as f:
        adv_data = json.load(f)

    report = evaluator.auto_audit_certificate(adv_data)
    assert report.overall_status == "NON-CONFORMING (FAIL)"
    # Must catch failures across chemical, mechanical, and physical
    assert report.failed_count >= 5
    assert report.compliance_score_pct < 50.0
    # Zero division guard must return 0.0 without exception
    assert report.ts_ys_ratio == 0.0
    # Mass per meter deviation check: 2.95 kg/m vs nominal 1.58 kg/m
    param_status = {r.parameter_key: r.status for r in report.results}
    assert param_status["carbon"] == "FAIL"
    assert param_status["yield_stress"] == "FAIL"
    assert param_status["mass_per_meter"] == "FAIL"


# -------------------------------------------------------------
# 3. 4-Stage Regulatory Verifier Tests
# -------------------------------------------------------------
def test_verifier_stage1_invalid_syntax(verifier):
    """Tests syntax failure for malformed license number."""
    res = verifier.verify_isi_license("INVALID-123")
    assert res.overall_valid is False
    assert res.final_status == "INVALID_SYNTAX"
    assert res.stage_reports[0].status == "FAIL"


def test_verifier_stage2_record_not_found(verifier):
    """Tests database check failure when CM/L is valid syntax but non-existent."""
    res = verifier.verify_isi_license("CM/L-0000000")
    assert res.overall_valid is False
    assert res.final_status == "RECORD_NOT_FOUND"
    assert res.stage_reports[0].status == "PASS"
    assert res.stage_reports[1].status == "FAIL"


def test_verifier_stage3_expired_license(verifier):
    """Tests validity check failure for lapsed license CM/L-1102948."""
    res = verifier.verify_isi_license("CM/L-1102948")
    assert res.overall_valid is False
    assert res.final_status == "EXPIRED_LICENSE"
    assert res.stage_reports[0].status == "PASS"
    assert res.stage_reports[1].status == "PASS"
    assert res.stage_reports[2].status == "FAIL"


def test_verifier_stage4_scope_mismatch(verifier):
    """Tests scope mismatch: Apex Re-Rollers (CM/L-6109923) has Fe 415/Fe 500, but NOT Fe 500D."""
    res = verifier.verify_isi_license("CM/L-6109923", target_grade="Fe 500D")
    assert res.overall_valid is False
    assert res.final_status == "SCOPE_MISMATCH"
    assert res.stage_reports[0].status == "PASS"
    assert res.stage_reports[1].status == "PASS"
    assert res.stage_reports[3].status == "FAIL"


def test_verifier_full_pass(verifier):
    """Tests full 4-stage pass for Tata Steel (CM/L-8400192) for Fe 500D 16mm."""
    res = verifier.verify_isi_license("CM/L-8400192", target_grade="Fe 500D", target_size_mm=16)
    assert res.overall_valid is True
    assert res.final_status == "VERIFIED_OPERATIVE"
    assert all(sr.status == "PASS" for sr in res.stage_reports)


def test_hallmark_huid_verifier(verifier):
    """Tests Hallmark HUID verification for authentic and invalid HUIDs."""
    res_pass = verifier.verify_hallmark_huid("AB92K1")
    assert res_pass.overall_valid is True
    assert res_pass.final_status == "VERIFIED_OPERATIVE"

    res_fail = verifier.verify_hallmark_huid("BADHUID")
    assert res_fail.overall_valid is False
    assert res_fail.final_status == "INVALID_SYNTAX"


def test_crs_registration_verifier(verifier):
    """Tests Compulsory Registration Scheme (CRS) verification."""
    res_pass = verifier.verify_crs_registration("R-41098234")
    assert res_pass.overall_valid is True
    assert res_pass.final_status == "VERIFIED_OPERATIVE"


# -------------------------------------------------------------
# 4. STI Factory Planner Tests
# -------------------------------------------------------------
def test_sti_planner_calculations():
    """Tests STI testing quotas and apparatus generation."""
    plan = STIPlanner.generate_tmt_sti_plan(daily_tonnage=160.0, operating_shifts=3, sizes_produced=[10, 12, 16, 20])
    assert plan.daily_tonnage == 160.0
    assert plan.total_lots_per_day == 4  # 4 sizes * ceil(40/40) = 4 lots
    assert plan.total_mandatory_tests_per_day > 0
    assert len(plan.testing_quotas) == 5
    assert len(plan.required_equipment) == 5
