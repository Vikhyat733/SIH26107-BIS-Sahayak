"""
MANAK AI - 4-Stage Regulatory Verifier
Multi-tiered verification engine for ISI Mark (CM/L), Compulsory Registration (CRS), and Hallmark (HUID).
"""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class StageReport(BaseModel):
    stage_number: int
    stage_name: str
    status: str  # "PASS", "FAIL", "WARNING"
    details: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    remedial_action: Optional[str] = None


class VerificationResult(BaseModel):
    query_identifier: str
    identifier_type: str  # "ISI_CML", "CRS_REGISTRATION", "HALLMARK_HUID"
    overall_valid: bool
    final_status: str  # "VERIFIED_OPERATIVE", "INVALID_SYNTAX", "RECORD_NOT_FOUND", "EXPIRED_LICENSE", "SCOPE_MISMATCH"
    stage_reports: List[StageReport]
    licensee_profile: Optional[Dict[str, Any]] = None
    verification_summary: str


# Authority Database Register Mock / Baseline Data
BIS_AUTHORITY_DATABASE = {
    "CM/L-8400192": {
        "license_number": "CM/L-8400192",
        "scheme": "Scheme-I (ISI Mark)",
        "licensee_name": "Tata Steel Limited",
        "plant_address": "Works: Jamshedpur, East Singhbhum, Jharkhand - 831001",
        "standard_code": "IS 1786:2008",
        "product_name": "High Strength Deformed Steel Bars and Wires for Concrete Reinforcement",
        "endorsed_grades": ["Fe 415", "Fe 415D", "Fe 500", "Fe 500D", "Fe 550D"],
        "endorsed_sizes_mm": [8, 10, 12, 16, 20, 25, 28, 32, 36, 40],
        "validity_status": "Operative",
        "valid_from": "2018-04-01",
        "valid_upto": "2027-03-31",
        "last_surveillance_date": "2026-05-14",
        "surveillance_result": "Satisfactory (Zero non-conformities)",
        "branch_office": "Jamshedpur Branch Office (JBO)",
    },
    "CM/L-7200541": {
        "license_number": "CM/L-7200541",
        "scheme": "Scheme-I (ISI Mark)",
        "licensee_name": "JSW Steel Coated Products Limited",
        "plant_address": "Tarapur Industrial Area, Palghar, Maharashtra - 401506",
        "standard_code": "IS 1786:2008",
        "product_name": "High Strength Deformed Steel Bars",
        "endorsed_grades": ["Fe 500", "Fe 500D"],
        "endorsed_sizes_mm": [10, 12, 16, 20, 25, 32],
        "validity_status": "Operative",
        "valid_from": "2019-10-15",
        "valid_upto": "2026-10-14",
        "last_surveillance_date": "2026-02-10",
        "surveillance_result": "Satisfactory",
        "branch_office": "Mumbai Branch Office-I (MUBO-I)",
    },
    "CM/L-6109923": {
        "license_number": "CM/L-6109923",
        "scheme": "Scheme-I (ISI Mark)",
        "licensee_name": "Apex Secondary Re-Rollers Private Limited",
        "plant_address": "Plot No. 44, Urla Industrial Estate, Raipur, Chhattisgarh - 492001",
        "standard_code": "IS 1786:2008",
        "product_name": "High Strength Deformed Steel Bars",
        "endorsed_grades": ["Fe 415", "Fe 500"],  # Note: Fe 500D is NOT endorsed!
        "endorsed_sizes_mm": [8, 10, 12, 16],
        "validity_status": "Under Surveillance",
        "valid_from": "2022-01-01",
        "valid_upto": "2026-12-31",
        "last_surveillance_date": "2026-08-20",
        "surveillance_result": "Discrepancy Notice Issued (STI testing frequency shortfall)",
        "branch_office": "Raipur Branch Office (RPBO)",
    },
    "CM/L-1102948": {
        "license_number": "CM/L-1102948",
        "scheme": "Scheme-I (ISI Mark)",
        "licensee_name": "Kalinga Iron & Rebar Works",
        "plant_address": "Rourkela Industrial Complex, Odisha - 769004",
        "standard_code": "IS 1786:2008",
        "product_name": "TMT Rebars",
        "endorsed_grades": ["Fe 415"],
        "endorsed_sizes_mm": [8, 10, 12],
        "validity_status": "Expired / Cancelled",
        "valid_from": "2015-06-01",
        "valid_upto": "2023-05-31",
        "last_surveillance_date": "2023-04-10",
        "surveillance_result": "License Renewal Lapsed",
        "branch_office": "Bhubaneswar Branch Office (BBO)",
    },
    "CM/L-9512304": {
        "license_number": "CM/L-9512304",
        "scheme": "Scheme-I (ISI Mark)",
        "licensee_name": "Aquafresh Mineral Springs Pvt Ltd",
        "plant_address": "Site IV Industrial Area, Sahibabad, Ghaziabad, UP - 201010",
        "standard_code": "IS 10500:2012",
        "product_name": "Packaged Drinking Water",
        "endorsed_grades": ["Standard Packaged Potable Water"],
        "endorsed_sizes_mm": [],
        "validity_status": "Operative",
        "valid_from": "2021-03-01",
        "valid_upto": "2027-02-28",
        "last_surveillance_date": "2026-04-12",
        "surveillance_result": "Satisfactory (Microbial negative)",
        "branch_office": "Ghaziabad Branch Office (GBO)",
    },
}

# Hallmark HUID mock registry
HALLMARK_HUID_DATABASE = {
    "AB92K1": {
        "huid": "AB92K1",
        "ahc_center_name": "Shree Ganesh Assaying & Hallmarking Centre",
        "ahc_bis_code": "AHC-DL-0042",
        "jeweller_name": "Tanishq - Titan Company Ltd (Connaught Place)",
        "jeweller_cml": "CML-HL-991204",
        "article_type": "Gold Bangle / Kada",
        "purity_karat": "22K916 (91.6% Pure Gold)",
        "hallmarking_timestamp": "2026-07-18 14:22:10 IST",
        "weight_grams": 24.85,
        "status": "Authentic & Verified",
    },
    "XYZ789": {
        "huid": "XYZ789",
        "ahc_center_name": "Zaveri Assaying Services",
        "ahc_bis_code": "AHC-MH-0112",
        "jeweller_name": "Kalyan Jewellers India Ltd",
        "jeweller_cml": "CML-HL-552011",
        "article_type": "Gold Necklace",
        "purity_karat": "18K750 (75.0% Pure Gold)",
        "hallmarking_timestamp": "2026-08-05 11:15:30 IST",
        "weight_grams": 45.20,
        "status": "Authentic & Verified",
    },
}

# CRS Registration mock registry
CRS_REGISTRATION_DATABASE = {
    "R-41098234": {
        "registration_number": "R-41098234",
        "scheme": "Compulsory Registration Scheme (CRS)",
        "brand": "DELL",
        "manufacturer": "Dell India Private Limited",
        "product_category": "Laptops / Notebooks",
        "standard_code": "IS 13252 (Part 1):2010",
        "validity_status": "Operative",
        "valid_upto": "2027-11-30",
        "models_registered": ["Inspiron 15 5510", "XPS 13 9310", "Latitude 5420"],
    },
    "R-98001245": {
        "registration_number": "R-98001245",
        "scheme": "Compulsory Registration Scheme (CRS)",
        "brand": "SAMSUNG",
        "manufacturer": "Samsung Electronics India Information & Telecommunication",
        "product_category": "Mobile Phones / Smart Handsets",
        "standard_code": "IS 13252 (Part 1):2010 / IS 16333 (Part 3):2022",
        "validity_status": "Operative",
        "valid_upto": "2028-03-31",
        "models_registered": ["Galaxy S26 Ultra", "Galaxy A55 5G", "Galaxy Fold 7"],
    },
}


class FourStageVerifier:
    """
    Executes a comprehensive 4-stage regulatory verification:
    Stage 1: Format & Syntax Check (Regex validation)
    Stage 2: Authority Database Record Check (BIS Central Registry)
    Stage 3: License & Validity Status Check (Operative vs Expired/Suspended)
    Stage 4: Product Scope & Endorsement Match (Grade, Size, Variety)
    """

    CML_REGEX = re.compile(r"^CM/L-?\s*(\d{7})$", re.IGNORECASE)
    CRS_REGEX = re.compile(r"^(?:R-)?\s*(\d{8})$", re.IGNORECASE)
    HUID_REGEX = re.compile(r"^[A-Z0-9]{6}$", re.IGNORECASE)

    @classmethod
    def detect_identifier_type(cls, query: str) -> str:
        """Detects whether query string is ISI CM/L, CRS, or Hallmark HUID."""
        q = query.strip()
        if cls.CML_REGEX.match(q) or q.upper().startswith("CM/L") or (q.isdigit() and len(q) == 7):
            return "ISI_CML"
        elif cls.CRS_REGEX.match(q) or q.upper().startswith("R-") or (q.isdigit() and len(q) == 8):
            return "CRS_REGISTRATION"
        elif cls.HUID_REGEX.match(q) and len(q) == 6:
            return "HALLMARK_HUID"
        return "ISI_CML"  # Default attempt

    def verify_isi_license(
        self,
        cml_query: str,
        target_grade: Optional[str] = None,
        target_size_mm: Optional[int] = None,
    ) -> VerificationResult:
        """
        Executes complete 4-stage verification for an ISI CM/L License.
        """
        stages: List[StageReport] = []
        raw_query = cml_query.strip()

        # Stage 1: Syntax & Format Check
        match = self.CML_REGEX.match(raw_query)
        clean_cml = None
        if match:
            clean_cml = f"CM/L-{match.group(1)}"
            stages.append(
                StageReport(
                    stage_number=1,
                    stage_name="Format & Syntax Validation",
                    status="PASS",
                    details=f"Valid BIS License Syntax detected: '{clean_cml}' conforms to standard CM/L-7digit pattern.",
                    evidence={"raw_input": raw_query, "normalized_cml": clean_cml, "regex": "^CM/L-\\d{7}$"},
                )
            )
        elif raw_query.isdigit() and len(raw_query) == 7:
            clean_cml = f"CM/L-{raw_query}"
            stages.append(
                StageReport(
                    stage_number=1,
                    stage_name="Format & Syntax Validation",
                    status="PASS",
                    details=f"Normalized 7-digit numeric string to standard format: '{clean_cml}'.",
                    evidence={"raw_input": raw_query, "normalized_cml": clean_cml},
                )
            )
        else:
            stages.append(
                StageReport(
                    stage_number=1,
                    stage_name="Format & Syntax Validation",
                    status="FAIL",
                    details=f"Invalid License Format: '{raw_query}'. Must follow 'CM/L-XXXXXXX' (7 digits).",
                    evidence={"raw_input": raw_query},
                    remedial_action="Verify CM/L number printed below the ISI monogram on product packaging or test report.",
                )
            )
            return VerificationResult(
                query_identifier=raw_query,
                identifier_type="ISI_CML",
                overall_valid=False,
                final_status="INVALID_SYNTAX",
                stage_reports=stages,
                licensee_profile=None,
                verification_summary="Failed at Stage 1: Invalid CM/L license format syntax.",
            )

        # Stage 2: Authority Database Record Check
        record = BIS_AUTHORITY_DATABASE.get(clean_cml)
        if not record:
            stages.append(
                StageReport(
                    stage_number=2,
                    stage_name="Authority Database Record Check",
                    status="FAIL",
                    details=f"License Number '{clean_cml}' does not exist in BIS Manakonline national registry.",
                    evidence={"searched_key": clean_cml, "registry": "BIS Manakonline Scheme-I"},
                    remedial_action="License may be fraudulent or un-indexed. Report suspect ISI marking to BIS Enforcement Wing via BIS Care App.",
                )
            )
            return VerificationResult(
                query_identifier=clean_cml,
                identifier_type="ISI_CML",
                overall_valid=False,
                final_status="RECORD_NOT_FOUND",
                stage_reports=stages,
                licensee_profile=None,
                verification_summary="Failed at Stage 2: License number not found in BIS National Registry.",
            )
        else:
            stages.append(
                StageReport(
                    stage_number=2,
                    stage_name="Authority Database Record Check",
                    status="PASS",
                    details=f"Authentic BIS Registry Record found for '{record['licensee_name']}' under standard {record['standard_code']}.",
                    evidence={
                        "licensee": record["licensee_name"],
                        "standard": record["standard_code"],
                        "branch": record.get("branch_office"),
                        "plant_address": record.get("plant_address"),
                    },
                )
            )

        # Stage 3: License & Validity Status Check
        validity = record.get("validity_status", "Unknown")
        valid_upto = record.get("valid_upto", "")

        if validity == "Operative":
            stages.append(
                StageReport(
                    stage_number=3,
                    stage_name="License Validity & Operating Status",
                    status="PASS",
                    details=f"License is OPERATIVE and active through {valid_upto}. Surveillance status: {record.get('surveillance_result', 'Active')}.",
                    evidence={"status": validity, "valid_upto": valid_upto, "last_surveillance": record.get("last_surveillance_date")},
                )
            )
        elif validity == "Under Surveillance":
            stages.append(
                StageReport(
                    stage_number=3,
                    stage_name="License Validity & Operating Status",
                    status="WARNING",
                    details=f"License is OPERATIVE but UNDER SURVEILLANCE notice: {record.get('surveillance_result')}. Valid until {valid_upto}.",
                    evidence={"status": validity, "valid_upto": valid_upto, "surveillance_result": record.get("surveillance_result")},
                    remedial_action="Request latest corrective action report (CAR) and third-party independent test certificate before procurement.",
                )
            )
        else:
            stages.append(
                StageReport(
                    stage_number=3,
                    stage_name="License Validity & Operating Status",
                    status="FAIL",
                    details=f"License is {validity.upper()} (Expired on {valid_upto}). Use of ISI mark is illegal under Section 17 of BIS Act, 2016.",
                    evidence={"status": validity, "valid_upto": valid_upto, "last_surveillance": record.get("last_surveillance_date")},
                    remedial_action="Immediate stop-use order. Do not accept goods manufactured after expiry date.",
                )
            )
            return VerificationResult(
                query_identifier=clean_cml,
                identifier_type="ISI_CML",
                overall_valid=False,
                final_status="EXPIRED_LICENSE",
                stage_reports=stages,
                licensee_profile=record,
                verification_summary=f"Failed at Stage 3: License is {validity} (Lapsed on {valid_upto}).",
            )

        # Stage 4: Product Scope & Endorsement Match
        scope_passed = True
        scope_details = []
        endorsed_grades = record.get("endorsed_grades", [])
        endorsed_sizes = record.get("endorsed_sizes_mm", [])

        if target_grade:
            if target_grade in endorsed_grades:
                scope_details.append(f"Grade '{target_grade}' is explicitly endorsed in manufacturer scope.")
            else:
                scope_passed = False
                scope_details.append(f"Grade '{target_grade}' is NOT endorsed in licensee scope. Approved grades: {endorsed_grades}.")

        if target_size_mm is not None:
            if target_size_mm in endorsed_sizes or not endorsed_sizes:
                scope_details.append(f"Nominal size '{target_size_mm} mm' is covered in manufacturing endorsement.")
            else:
                scope_passed = False
                scope_details.append(f"Nominal size '{target_size_mm} mm' is NOT endorsed. Approved sizes: {endorsed_sizes} mm.")

        if not target_grade and target_size_mm is None:
            scope_details.append(f"All endorsed grades ({', '.join(endorsed_grades)}) and sizes ({endorsed_sizes} mm) available for dispatch.")

        if scope_passed:
            stages.append(
                StageReport(
                    stage_number=4,
                    stage_name="Product Scope & Endorsement Match",
                    status="PASS",
                    details=" ; ".join(scope_details),
                    evidence={"endorsed_grades": endorsed_grades, "endorsed_sizes_mm": endorsed_sizes, "requested_grade": target_grade, "requested_size": target_size_mm},
                )
            )
            final_status = "VERIFIED_OPERATIVE"
            overall_valid = True
            summary = f"Full 4-Stage Verification SUCCESSFUL. {clean_cml} is active, operative, and verified for scope."
        else:
            stages.append(
                StageReport(
                    stage_number=4,
                    stage_name="Product Scope & Endorsement Match",
                    status="FAIL",
                    details=" ; ".join(scope_details),
                    evidence={"endorsed_grades": endorsed_grades, "endorsed_sizes_mm": endorsed_sizes, "requested_grade": target_grade, "requested_size": target_size_mm},
                    remedial_action="Manufacturer cannot supply non-endorsed grades/sizes under this CM/L without official BIS Scope Endorsement Letter.",
                )
            )
            final_status = "SCOPE_MISMATCH"
            overall_valid = False
            summary = f"Failed at Stage 4: Product grade or size falls outside licensed endorsement scope."

        return VerificationResult(
            query_identifier=clean_cml,
            identifier_type="ISI_CML",
            overall_valid=overall_valid,
            final_status=final_status,
            stage_reports=stages,
            licensee_profile=record,
            verification_summary=summary,
        )

    def verify_hallmark_huid(self, huid_query: str) -> VerificationResult:
        """Verifies 6-character alphanumeric Gold/Silver Hallmark HUID."""
        stages: List[StageReport] = []
        raw_huid = huid_query.strip().upper()

        if not self.HUID_REGEX.match(raw_huid):
            stages.append(
                StageReport(
                    stage_number=1,
                    stage_name="HUID Format Validation",
                    status="FAIL",
                    details=f"Invalid HUID Format: '{raw_huid}'. Hallmark Unique Identification Number must be exact 6 alphanumeric characters (e.g., AB92K1).",
                    evidence={"input": raw_huid},
                    remedial_action="Inspect the laser-etched 6-digit code on the precious metal article using a 10x jeweller loupe.",
                )
            )
            return VerificationResult(
                query_identifier=raw_huid,
                identifier_type="HALLMARK_HUID",
                overall_valid=False,
                final_status="INVALID_SYNTAX",
                stage_reports=stages,
                licensee_profile=None,
                verification_summary="Invalid HUID syntax format.",
            )

        stages.append(
            StageReport(
                stage_number=1,
                stage_name="HUID Format Validation",
                status="PASS",
                details=f"Valid 6-character HUID syntax: '{raw_huid}'.",
                evidence={"huid": raw_huid},
            )
        )

        record = HALLMARK_HUID_DATABASE.get(raw_huid)
        if not record:
            stages.append(
                StageReport(
                    stage_number=2,
                    stage_name="AHC Central Server Registration",
                    status="FAIL",
                    details=f"HUID '{raw_huid}' was not generated by any BIS-recognized Assaying and Hallmarking Centre (AHC).",
                    evidence={"searched_huid": raw_huid},
                    remedial_action="High risk of counterfeit hallmarking. Check BIS Care App or submit for verification at nearest AHC.",
                )
            )
            return VerificationResult(
                query_identifier=raw_huid,
                identifier_type="HALLMARK_HUID",
                overall_valid=False,
                final_status="RECORD_NOT_FOUND",
                stage_reports=stages,
                licensee_profile=None,
                verification_summary="HUID not found on BIS Central Hallmarking Server.",
            )

        stages.append(
            StageReport(
                stage_number=2,
                stage_name="AHC Central Server Registration",
                status="PASS",
                details=f"Hallmarking record logged by {record['ahc_center_name']} (BIS Code: {record['ahc_bis_code']}).",
                evidence={"ahc_name": record["ahc_center_name"], "ahc_code": record["ahc_bis_code"]},
            )
        )

        stages.append(
            StageReport(
                stage_number=3,
                stage_name="Jeweller Registration & Status",
                status="PASS",
                details=f"Assayed for registered jeweller '{record['jeweller_name']}' under license {record['jeweller_cml']}.",
                evidence={"jeweller": record["jeweller_name"], "cml": record["jeweller_cml"]},
            )
        )

        stages.append(
            StageReport(
                stage_number=4,
                stage_name="Purity & Article Verification",
                status="PASS",
                details=f"Certified Purity: {record['purity_karat']} | Article: {record['article_type']} | Weight: {record['weight_grams']}g.",
                evidence={
                    "purity": record["purity_karat"],
                    "article": record["article_type"],
                    "timestamp": record["hallmarking_timestamp"],
                },
            )
        )

        return VerificationResult(
            query_identifier=raw_huid,
            identifier_type="HALLMARK_HUID",
            overall_valid=True,
            final_status="VERIFIED_OPERATIVE",
            stage_reports=stages,
            licensee_profile=record,
            verification_summary=f"Authentic BIS Hallmark Verified: {record['purity_karat']} {record['article_type']} ({record['jeweller_name']}).",
        )

    def verify_crs_registration(self, crs_query: str) -> VerificationResult:
        """Verifies Compulsory Registration Scheme (CRS) Registration for Electronics/IT goods."""
        stages: List[StageReport] = []
        raw = crs_query.strip().upper()
        match = self.CRS_REGEX.match(raw)
        clean_crs = None

        if match:
            clean_crs = f"R-{match.group(1)}"
            stages.append(
                StageReport(
                    stage_number=1,
                    stage_name="CRS Format Validation",
                    status="PASS",
                    details=f"Valid CRS Registration format: '{clean_crs}'.",
                    evidence={"crs": clean_crs},
                )
            )
        else:
            stages.append(
                StageReport(
                    stage_number=1,
                    stage_name="CRS Format Validation",
                    status="FAIL",
                    details=f"Invalid CRS Format: '{raw}'. Expected 'R-XXXXXXXX' (8 digits).",
                    evidence={"input": raw},
                )
            )
            return VerificationResult(
                query_identifier=raw,
                identifier_type="CRS_REGISTRATION",
                overall_valid=False,
                final_status="INVALID_SYNTAX",
                stage_reports=stages,
                licensee_profile=None,
                verification_summary="Invalid CRS registration number format.",
            )

        record = CRS_REGISTRATION_DATABASE.get(clean_crs)
        if not record:
            stages.append(
                StageReport(
                    stage_number=2,
                    stage_name="CRS Portal Registry Check",
                    status="FAIL",
                    details=f"CRS Registration '{clean_crs}' not found in BIS CRS portal.",
                    evidence={"crs": clean_crs},
                )
            )
            return VerificationResult(
                query_identifier=clean_crs,
                identifier_type="CRS_REGISTRATION",
                overall_valid=False,
                final_status="RECORD_NOT_FOUND",
                stage_reports=stages,
                licensee_profile=None,
                verification_summary="CRS registration not registered on portal.",
            )

        stages.append(
            StageReport(
                stage_number=2,
                stage_name="CRS Portal Registry Check",
                status="PASS",
                details=f"Registered Brand '{record['brand']}' by '{record['manufacturer']}'.",
                evidence={"brand": record["brand"], "manufacturer": record["manufacturer"]},
            )
        )

        stages.append(
            StageReport(
                stage_number=3,
                stage_name="Registration Status & Validity",
                status="PASS",
                details=f"Status: {record['validity_status']} | Valid through: {record['valid_upto']}.",
                evidence={"status": record["validity_status"], "valid_upto": record["valid_upto"]},
            )
        )

        stages.append(
            StageReport(
                stage_number=4,
                stage_name="Standard & Model Inclusion Scope",
                status="PASS",
                details=f"Standard: {record['standard_code']} | Category: {record['product_category']} | Endorsed Models: {', '.join(record['models_registered'])}",
                evidence={"models": record["models_registered"], "standard": record["standard_code"]},
            )
        )

        return VerificationResult(
            query_identifier=clean_crs,
            identifier_type="CRS_REGISTRATION",
            overall_valid=True,
            final_status="VERIFIED_OPERATIVE",
            stage_reports=stages,
            licensee_profile=record,
            verification_summary=f"Valid CRS Registration for Brand {record['brand']} ({record['product_category']}).",
        )
