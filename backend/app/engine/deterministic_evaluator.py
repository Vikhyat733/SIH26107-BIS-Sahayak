"""
MANAK AI - Deterministic Compliance Verification Engine
Zero-Hallucination, Rule-Based Mathematical Evaluation Engine for BIS Standards.
"""

from typing import Dict, Any, List, Optional
import json
import os
from pydantic import BaseModel, Field


class ParameterAuditResult(BaseModel):
    parameter_key: str
    parameter_name: str
    measured_value: Optional[float] = None
    unit: str
    standard_min: Optional[float] = None
    standard_max: Optional[float] = None
    status: str  # "PASS", "FAIL", "WARNING", "REVIEW"
    delta: Optional[float] = None  # Difference from threshold (positive when exceeding max or distance from min)
    delta_type: str  # "EXCEEDED_MAX", "BELOW_MIN", "WITHIN_LIMITS", "UNKNOWN"
    clause_citation: str
    remarks: str


class CertificateAuditReport(BaseModel):
    certificate_id: str
    standard_code: str
    product_name: str
    grade: Optional[str] = None
    lot_size_tonnes: Optional[float] = None
    overall_status: str  # "CONFORMING (PASS)" or "NON-CONFORMING (FAIL)"
    total_parameters_checked: int
    passed_count: int
    failed_count: int
    compliance_score_pct: float
    carbon_equivalent: Optional[float] = None
    carbon_equivalent_clause: Optional[str] = None
    ts_ys_ratio: Optional[float] = None
    results: List[ParameterAuditResult]
    violations: List[str]
    audit_timestamp: str
    audit_engine_version: str = "MANAK-DET-v2.6"


class DeterministicEvaluator:
    """
    Deterministic rule engine that validates MTC/Lab Test reports against
    official BIS ground truth schemas with exact mathematical comparisons.
    """

    def __init__(self, schemas_dir: Optional[str] = None):
        if schemas_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.schemas_dir = os.path.join(base_dir, "data", "standards")
        else:
            self.schemas_dir = schemas_dir
        self.schemas_cache: Dict[str, Dict[str, Any]] = {}
        self._load_schemas()

    def _load_schemas(self):
        """Loads all available ground truth schemas from data directory."""
        if os.path.exists(self.schemas_dir):
            for fname in os.listdir(self.schemas_dir):
                if fname.endswith(".json"):
                    path = os.path.join(self.schemas_dir, fname)
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        code = data.get("standard_code")
                        if code:
                            self.schemas_cache[code] = data
                            # Normalize key aliases (e.g., IS 1786:2008 -> IS 1786)
                            short_code = code.split(":")[0].strip()
                            self.schemas_cache[short_code] = data

    @staticmethod
    def calculate_carbon_equivalent(
        carbon: float,
        manganese: float,
        chromium: float = 0.0,
        molybdenum: float = 0.0,
        vanadium: float = 0.0,
        nickel: float = 0.0,
        copper: float = 0.0,
    ) -> float:
        """
        Calculates Carbon Equivalent (CE) per IS 1786:2008 Table 1 Note 1:
        CE = C + (Mn / 6) + ((Cr + Mo + V) / 5) + ((Ni + Cu) / 15)
        """
        ce = (
            carbon
            + (manganese / 6.0)
            + ((chromium + molybdenum + vanadium) / 5.0)
            + ((nickel + copper) / 15.0)
        )
        return round(ce, 4)

    @staticmethod
    def calculate_ts_ys_ratio(tensile_strength: float, yield_stress: float) -> float:
        """Calculates TS/YS ratio with safety guard for division by zero."""
        if yield_stress <= 0:
            return 0.0
        return round(tensile_strength / yield_stress, 4)

    def evaluate_tmt_mtc(self, mtc_data: Dict[str, Any]) -> CertificateAuditReport:
        """
        Evaluates a TMT Steel Reinforcement Bar MTC against IS 1786:2008.
        Computes chemical limits, mechanical properties, CE, TS/YS, and mass variation.
        """
        schema = self.schemas_cache.get("IS 1786:2008") or self.schemas_cache.get("IS 1786")
        if not schema:
            raise ValueError("IS 1786:2008 schema not loaded in engine.")

        prod_details = mtc_data.get("product_details", {})
        grade = prod_details.get("grade", "Fe 500D")
        cert_id = mtc_data.get("certificate_id", "UNKNOWN-CERT")
        lot_weight = prod_details.get("lot_weight_tonnes", 0.0)

        if grade not in schema["grades"]:
            # Fallback to Fe 500D if grade missing/mismatched
            grade_key = "Fe 500D"
        else:
            grade_key = grade

        grade_rules = schema["grades"][grade_key]
        chem_limits = grade_rules.get("chemical_limits", {})
        mech_limits = grade_rules.get("mechanical_limits", {})

        chem_input = mtc_data.get("chemical_composition", {})
        mech_input = mtc_data.get("mechanical_properties", {})
        phys_input = mtc_data.get("physical_properties", {})

        results: List[ParameterAuditResult] = []
        violations: List[str] = []

        def safe_float(val):
            if val is None: return None
            try: return float(val)
            except (ValueError, TypeError): return None

        # 1. Chemical Composition Evaluation
        c = safe_float(chem_input.get("carbon"))
        s = safe_float(chem_input.get("sulfur"))
        p = safe_float(chem_input.get("phosphorus"))
        
        sp = safe_float(chem_input.get("sulfur_plus_phosphorus"))
        if sp is None and s is not None and p is not None:
            sp = round(s + p, 4)
            
        mn = safe_float(chem_input.get("manganese"))
        cr = safe_float(chem_input.get("chromium"))
        mo = safe_float(chem_input.get("molybdenum"))
        v = safe_float(chem_input.get("vanadium"))
        ni = safe_float(chem_input.get("nickel"))
        cu = safe_float(chem_input.get("copper"))

        # Carbon Equivalent calculation
        ce_calc = None
        if c is not None and mn is not None:
            ce_calc = self.calculate_carbon_equivalent(c, mn, cr or 0.0, mo or 0.0, v or 0.0, ni or 0.0, cu or 0.0)

        chem_dict_to_check = {
            "carbon": ("Carbon (%C)", c, chem_limits.get("carbon", {})),
            "sulfur": ("Sulfur (%S)", s, chem_limits.get("sulfur", {})),
            "phosphorus": ("Phosphorus (%P)", p, chem_limits.get("phosphorus", {})),
            "sulfur_plus_phosphorus": ("Sulfur + Phosphorus (S+P)", sp, chem_limits.get("sulfur_plus_phosphorus", {})),
            "carbon_equivalent": ("Carbon Equivalent (CE)", ce_calc, chem_limits.get("carbon_equivalent", {})),
        }

        for param_k, (pname, val, rule) in chem_dict_to_check.items():
            if not rule:
                continue
            max_val = rule.get("max")
            clause = rule.get("clause", "IS 1786 Table 1")
            unit = rule.get("unit", "%")

            if val is None:
                status = "REVIEW"
                delta = None
                delta_type = "UNKNOWN"
                rem = "Missing or unparseable value"
                violations.append(f"{pname}: Value missing or unparseable (requires manual review) [{clause}]")
            elif max_val is not None and val > max_val:
                delta = round(val - max_val, 4)
                status = "FAIL"
                delta_type = "EXCEEDED_MAX"
                rem = f"Exceeds max allowable limit of {max_val}{unit} by +{delta}{unit}"
                violations.append(f"{pname}: {val}{unit} > Max {max_val}{unit} (Violation: +{delta}{unit}) [{clause}]")
            else:
                delta = round((max_val - val) if max_val is not None else 0.0, 4)
                status = "PASS"
                delta_type = "WITHIN_LIMITS"
                rem = f"Within specification (Margin: {delta}{unit})"

            results.append(
                ParameterAuditResult(
                    parameter_key=param_k,
                    parameter_name=pname,
                    measured_value=val,
                    unit=unit,
                    standard_min=None,
                    standard_max=max_val,
                    status=status,
                    delta=delta,
                    delta_type=delta_type,
                    clause_citation=clause,
                    remarks=rem,
                )
            )

        # 2. Mechanical Properties Evaluation
        ys = safe_float(mech_input.get("yield_stress"))
        ts = safe_float(mech_input.get("tensile_strength"))
        
        # Calculate or verify TS/YS ratio
        ts_ys = safe_float(mech_input.get("ts_ys_ratio"))
        if ts_ys is None and ts is not None and ys is not None:
            ts_ys = self.calculate_ts_ys_ratio(ts, ys)
            
        elong = safe_float(mech_input.get("elongation"))
        tot_elong = safe_float(mech_input.get("total_elongation_at_max_force"))

        mech_dict_to_check = {
            "yield_stress": ("0.2% Proof Stress / Yield Stress", ys, mech_limits.get("yield_stress", {})),
            "tensile_strength": ("Tensile Strength", ts, mech_limits.get("tensile_strength", {})),
            "ts_ys_ratio": ("TS/YS Ratio", ts_ys, mech_limits.get("ts_ys_ratio", {})),
            "elongation": ("Elongation at Gauge Length 5.65√A", elong, mech_limits.get("elongation", {})),
            "total_elongation_at_max_force": ("Total Elongation at Max Force", tot_elong, mech_limits.get("total_elongation_at_max_force", {})),
        }

        for param_k, (pname, val, rule) in mech_dict_to_check.items():
            if not rule:
                continue
            min_val = rule.get("min")
            clause = rule.get("clause", "IS 1786 Table 3")
            unit = rule.get("unit", "")

            # If min_val is 0.0 and total_elongation is not tested / not mandatory for that grade, pass
            if val is None:
                # If rule has a min_val > 0, it's mandatory
                if min_val is not None and min_val > 0.0:
                    status = "REVIEW"
                    delta = None
                    delta_type = "UNKNOWN"
                    rem = "Missing or unparseable value"
                    violations.append(f"{pname}: Value missing or unparseable (requires manual review) [{clause}]")
                else:
                    status = "PASS"
                    delta = None
                    delta_type = "WITHIN_LIMITS"
                    rem = "Not mandatory for this grade"
            elif min_val is not None and min_val > 0.0 and val < min_val:
                delta = round(min_val - val, 4)
                status = "FAIL"
                delta_type = "BELOW_MIN"
                rem = f"Deficient by -{delta}{unit} (Required Min {min_val}{unit})"
                violations.append(f"{pname}: {val}{unit} < Min {min_val}{unit} (Deficit: -{delta}{unit}) [{clause}]")
            else:
                delta = round((val - min_val) if min_val is not None else 0.0, 4)
                status = "PASS"
                delta_type = "WITHIN_LIMITS"
                rem = f"Conforms to threshold (Surplus: +{delta}{unit})"

            results.append(
                ParameterAuditResult(
                    parameter_key=param_k,
                    parameter_name=pname,
                    measured_value=val,
                    unit=unit,
                    standard_min=min_val,
                    standard_max=None,
                    status=status,
                    delta=delta,
                    delta_type=delta_type,
                    clause_citation=clause,
                    remarks=rem,
                )
            )

        # 3. Mass per meter tolerance check (if nominal diameter provided)
        dia = str(prod_details.get("nominal_diameter_mm", "16"))
        mass_rules = schema.get("nominal_mass_per_meter", {})
        if dia in mass_rules and "mass_per_meter" in phys_input:
            m_rule = mass_rules[dia]
            nom_mass = m_rule["nominal_mass"]
            tol_pct = m_rule["tolerance_pct"]
            min_mass = round(nom_mass * (1 - tol_pct / 100.0), 3)
            max_mass = round(nom_mass * (1 + tol_pct / 100.0), 3)
            actual_mass = float(phys_input["mass_per_meter"])
            clause = m_rule.get("clause", "IS 1786 Table 2")

            if actual_mass < min_mass or actual_mass > max_mass:
                status = "FAIL"
                delta = round(actual_mass - nom_mass, 4)
                delta_type = "BELOW_MIN" if actual_mass < min_mass else "EXCEEDED_MAX"
                rem = f"Mass per metre {actual_mass} kg/m deviates beyond ±{tol_pct}% allowable range [{min_mass}, {max_mass}]"
                violations.append(f"Nominal Mass ({dia}mm): {actual_mass} kg/m outside [{min_mass}, {max_mass}] [{clause}]")
            else:
                status = "PASS"
                delta = round(abs(actual_mass - nom_mass), 4)
                delta_type = "WITHIN_LIMITS"
                rem = f"Within ±{tol_pct}% tolerance band [{min_mass} - {max_mass}] kg/m"

            results.append(
                ParameterAuditResult(
                    parameter_key="mass_per_meter",
                    parameter_name=f"Nominal Mass ({dia}mm bar)",
                    measured_value=actual_mass,
                    unit="kg/m",
                    standard_min=min_mass,
                    standard_max=max_mass,
                    status=status,
                    delta=delta,
                    delta_type=delta_type,
                    clause_citation=clause,
                    remarks=rem,
                )
            )

        total_checked = len(results)
        failed = sum(1 for r in results if r.status == "FAIL")
        review = sum(1 for r in results if r.status == "REVIEW")
        passed = total_checked - failed - review
        score = round((passed / total_checked * 100.0), 1) if total_checked > 0 else 100.0

        if review > 0:
            overall = "REVIEW"
        else:
            overall = "CONFORMING (PASS)" if failed == 0 else "NON-CONFORMING (FAIL)"

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

        return CertificateAuditReport(
            certificate_id=cert_id,
            standard_code=schema["standard_code"],
            product_name=schema["title"],
            grade=grade_key,
            lot_size_tonnes=lot_weight,
            overall_status=overall,
            total_parameters_checked=total_checked,
            passed_count=passed,
            failed_count=failed,
            compliance_score_pct=score,
            carbon_equivalent=ce_calc,
            carbon_equivalent_clause="IS 1786 Table 1 Note 1",
            ts_ys_ratio=ts_ys,
            results=results,
            violations=violations,
            audit_timestamp=timestamp,
        )

    def evaluate_drinking_water(self, test_data: Dict[str, Any]) -> CertificateAuditReport:
        """
        Evaluates Drinking Water sample report against IS 10500:2012.
        Checks acceptable vs permissible limits and toxic metals.
        """
        schema = self.schemas_cache.get("IS 10500:2012") or self.schemas_cache.get("IS 10500")
        if not schema:
            raise ValueError("IS 10500:2012 schema not loaded in engine.")

        cert_id = test_data.get("sample_id", test_data.get("certificate_id", "WATER-SAMPLE-01"))
        params_input = test_data.get("parameters", test_data)

        schema_params = schema.get("parameters", {})
        results: List[ParameterAuditResult] = []
        violations: List[str] = []

        for pkey, pmeta in schema_params.items():
            if pkey in params_input or pkey.replace("_", "") in params_input:
                raw_val = params_input.get(pkey, params_input.get(pkey.replace("_", "")))
                try:
                    val = float(raw_val)
                except (ValueError, TypeError):
                    continue

                pname = pmeta["name"]
                unit = pmeta["unit"]
                clause = pmeta["clause"]
                acc_min = pmeta.get("acceptable_limit_min", 0.0)
                acc_max = pmeta.get("acceptable_limit_max")
                perm_max = pmeta.get("permissible_limit_max", acc_max)

                # Evaluation against acceptable and permissible bounds
                if val < acc_min:
                    status = "FAIL"
                    delta = round(acc_min - val, 4)
                    delta_type = "BELOW_MIN"
                    rem = f"Below minimum acceptable limit of {acc_min} {unit}"
                    violations.append(f"{pname}: {val} < Min {acc_min} {unit} [{clause}]")
                elif acc_max is not None and val > perm_max:
                    status = "FAIL"
                    delta = round(val - perm_max, 4)
                    delta_type = "EXCEEDED_MAX"
                    rem = f"Exceeds maximum permissible limit of {perm_max} {unit} by +{delta}"
                    violations.append(f"{pname}: {val} > Permissible Max {perm_max} {unit} [{clause}]")
                elif acc_max is not None and val > acc_max:
                    status = "WARNING"
                    delta = round(val - acc_max, 4)
                    delta_type = "WITHIN_LIMITS"
                    rem = f"Exceeds acceptable limit ({acc_max} {unit}) but within permissible limit ({perm_max} {unit})"
                else:
                    status = "PASS"
                    delta = round(acc_max - val if acc_max is not None else 0.0, 4)
                    delta_type = "WITHIN_LIMITS"
                    rem = f"Fully conforming to acceptable limit (≤ {acc_max} {unit})"

                results.append(
                    ParameterAuditResult(
                        parameter_key=pkey,
                        parameter_name=pname,
                        measured_value=val,
                        unit=unit,
                        standard_min=acc_min,
                        standard_max=acc_max,
                        status=status,
                        delta=delta,
                        delta_type=delta_type,
                        clause_citation=clause,
                        remarks=rem,
                    )
                )

        total_checked = len(results)
        failed = sum(1 for r in results if r.status == "FAIL")
        passed = total_checked - failed
        score = round((passed / total_checked * 100.0), 1) if total_checked > 0 else 100.0
        overall = "CONFORMING (PASS)" if failed == 0 else "NON-CONFORMING (FAIL)"

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

        return CertificateAuditReport(
            certificate_id=cert_id,
            standard_code=schema["standard_code"],
            product_name=schema["title"],
            grade="Potable Drinking Water",
            overall_status=overall,
            total_parameters_checked=total_checked,
            passed_count=passed,
            failed_count=failed,
            compliance_score_pct=score,
            results=results,
            violations=violations,
            audit_timestamp=timestamp,
        )

    def auto_audit_certificate(self, data: Dict[str, Any]) -> CertificateAuditReport:
        """
        Auto-detects the applicable standard from input JSON/Dict and executes
        the corresponding deterministic rule engine.
        """
        std = ""
        if "product_details" in data and "standard" in data["product_details"]:
            std = data["product_details"]["standard"]
        elif "standard" in data:
            std = data["standard"]
        elif "chemical_composition" in data and "mechanical_properties" in data:
            std = "IS 1786:2008"
        elif "parameters" in data and ("ph_value" in data["parameters"] or "turbidity" in data["parameters"]):
            std = "IS 10500:2012"
        elif "ph_value" in data or "turbidity" in data:
            std = "IS 10500:2012"

        if std and "1786" in std:
            return self.evaluate_tmt_mtc(data)
        elif std and "10500" in std:
            return self.evaluate_drinking_water(data)
        else:
            raise ValueError(f"Compliance could not be determined because the applicable standard could not be established or is not supported (Detected: {std or 'None'}).")
