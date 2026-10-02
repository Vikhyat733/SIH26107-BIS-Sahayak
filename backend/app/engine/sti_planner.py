"""
MANAK AI - Scheme of Testing & Inspection (STI) Planner
Generates factory quality control quotas, testing frequency schedules,
and lab apparatus calibration registers based on production capacity.
"""

import math
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class LabEquipmentCheck(BaseModel):
    equipment_name: str
    purpose: str
    standard_method: str
    calibration_frequency_months: int
    is_mandatory: bool = True
    audit_check_points: str


class TestingQuota(BaseModel):
    test_name: str
    sampling_rule: str
    clause_reference: str
    estimated_daily_tests: int
    tests_per_month: int
    test_method_standard: str
    responsible_person: str


class STIFactoryPlan(BaseModel):
    standard_code: str
    product_name: str
    daily_tonnage: float
    operating_shifts: int
    sizes_produced: List[int]
    total_lots_per_day: int
    total_mandatory_tests_per_day: int
    testing_quotas: List[TestingQuota]
    required_equipment: List[LabEquipmentCheck]
    sti_document_number: str
    record_keeping_mandate: str
    sampling_summary: str


class STIPlanner:
    """
    Computes factory testing quotas and lab infrastructure requirements
    conforming to BIS Scheme of Testing & Inspection guidelines.
    """

    @classmethod
    def generate_tmt_sti_plan(
        cls,
        daily_tonnage: float = 120.0,
        operating_shifts: int = 3,
        sizes_produced: Optional[List[int]] = None,
        heats_per_day: int = 4,
    ) -> STIFactoryPlan:
        """
        Generates STI plan for TMT Rebars under STI/1786/7 (IS 1786:2008).
        """
        if sizes_produced is None:
            sizes_produced = [10, 12, 16, 20]

        num_sizes = max(len(sizes_produced), 1)
        lot_size = 40.0  # Tonnes per lot per size

        # Lots per day calculation: 40 tonnes or part thereof per size
        tonnage_per_size = daily_tonnage / num_sizes
        lots_per_size = math.ceil(tonnage_per_size / lot_size)
        total_lots = lots_per_size * num_sizes

        # 1. Chemical Ladle Analysis (1 per heat/cast)
        ladle_tests = max(heats_per_day, 1)

        # 2. Tensile / Proof Stress (1 test per 40T or part thereof per size)
        tensile_tests = total_lots

        # 3. Bend & Rebend Test (1 test per 40T per size)
        bend_tests = total_lots

        # 4. Mass per Metre Variation (1 test per 10T or part thereof)
        mass_tests = math.ceil(daily_tonnage / 10.0)

        # 5. Rib Geometry / Surface Characteristics (1 test per size per shift)
        rib_tests = num_sizes * operating_shifts

        quotas: List[TestingQuota] = [
            TestingQuota(
                test_name="Ladle Chemical Analysis (C, S, P, Mn, Si, CE)",
                sampling_rule="1 test per heat / ladle cast",
                clause_reference="STI/1786/7 Clause 3.1 & IS 1786 Cl 4.2",
                estimated_daily_tests=ladle_tests,
                tests_per_month=ladle_tests * 26,
                test_method_standard="IS 8811 (OES) / IS 228 (Wet Chemical)",
                responsible_person="Chief Metallurgist / Spectro Lab Chemist",
            ),
            TestingQuota(
                test_name="0.2% Proof Stress / Yield Stress & Tensile Strength",
                sampling_rule="1 test per 40 tonnes or part thereof for each nominal size and heat",
                clause_reference="STI/1786/7 Clause 4.1 & IS 1786 Table 3",
                estimated_daily_tests=tensile_tests,
                tests_per_month=tensile_tests * 26,
                test_method_standard="IS 1608 (Part 1):2018 (Metallic Tensile Testing)",
                responsible_person="Physical Testing QA Engineer",
            ),
            TestingQuota(
                test_name="Cold Bend & Reverse Rebend Test",
                sampling_rule="1 test per 40 tonnes or part thereof for each nominal size",
                clause_reference="STI/1786/7 Clause 4.2 & IS 1786 Cl 9.2",
                estimated_daily_tests=bend_tests,
                tests_per_month=bend_tests * 26,
                test_method_standard="IS 1599:2019 (Metallic Bend Test)",
                responsible_person="Mechanical Lab Technician",
            ),
            TestingQuota(
                test_name="Nominal Mass Variation per Metre",
                sampling_rule="1 sample per 10 tonnes or part thereof (min 3 bars of 0.5m length)",
                clause_reference="STI/1786/7 Clause 5.1 & IS 1786 Table 2",
                estimated_daily_tests=mass_tests,
                tests_per_month=mass_tests * 26,
                test_method_standard="IS 1786 Clause 6.2 (Gravimetric & length method)",
                responsible_person="Rolling Mill Quality Inspector",
            ),
            TestingQuota(
                test_name="Rib Geometry & Transverse Deformation Height",
                sampling_rule="1 test per nominal size per 8-hour operating shift",
                clause_reference="STI/1786/7 Clause 5.2 & IS 1786 Cl 5",
                estimated_daily_tests=rib_tests,
                tests_per_month=rib_tests * 26,
                test_method_standard="IS 1786 Clause 5.3 & Annex A",
                responsible_person="Shift Quality In-Charge",
            ),
        ]

        total_daily_tests = sum(q.estimated_daily_tests for q in quotas)

        equipment_list: List[LabEquipmentCheck] = [
            LabEquipmentCheck(
                equipment_name="Optical Emission Spectrometer (OES) / Spark Spectrometer",
                purpose="Direct multi-element chemical analysis (C, S, P, Mn, Si, Cr, Mo, V, Ni, Cu)",
                standard_method="IS 8811",
                calibration_frequency_months=6,
                is_mandatory=True,
                audit_check_points="Certified Reference Materials (CRM standards), Argon gas purity >99.999%, daily drift correction log.",
            ),
            LabEquipmentCheck(
                equipment_name="Universal Testing Machine (UTM) - Minimum 600kN or 1000kN with Extensometer",
                purpose="Measurement of 0.2% Proof Stress, Tensile Strength, and Total Elongation",
                standard_method="IS 1608 (Part 1)",
                calibration_frequency_months=12,
                is_mandatory=True,
                audit_check_points="NABL accredited calibration certificate, load cell verification Class 1.0, electronic extensometer gauge length 5.65√A.",
            ),
            LabEquipmentCheck(
                equipment_name="Motorized Mandrel Cold Bend & Reverse Rebend Test Rig",
                purpose="180° Cold Bend and 135° + 157.5° reverse bend test with hot water bath aging at 100°C",
                standard_method="IS 1599 / IS 1786",
                calibration_frequency_months=12,
                is_mandatory=True,
                audit_check_points="Mandrel diameter sets matching Table 4 of IS 1786, digital water temperature controller for aging bath.",
            ),
            LabEquipmentCheck(
                equipment_name="High-Precision Digital Weighing Balance (0.01g resolution) & Steel Scale",
                purpose="Nominal Mass per Metre tolerance checking (IS 1786 Table 2)",
                standard_method="IS 1786 Clause 6.2",
                calibration_frequency_months=6,
                is_mandatory=True,
                audit_check_points="Standard F1/M1 class reference weights, daily zero balance verification register.",
            ),
            LabEquipmentCheck(
                equipment_name="Optical Profile Projector / Depth Micrometer Gauge",
                purpose="Transverse rib height, rib spacing, flank angle, and longitudinal rib dimension",
                standard_method="IS 1786 Annex A",
                calibration_frequency_months=12,
                is_mandatory=True,
                audit_check_points="Magnification calibration scale (10x/20x), slip gauges, zero error verification.",
            ),
        ]

        summary = (
            f"For a daily production of {daily_tonnage} Metric Tonnes across {num_sizes} section sizes "
            f"({', '.join(str(s)+'mm' for s in sizes_produced)}) and {operating_shifts} shifts: "
            f"Mandatory minimum {total_daily_tests} in-house tests across {total_lots} sampling lots per day."
        )

        mandate = (
            "BIS STI/1786/7 requires all test records, raw charts, calibration logs, and heat register "
            "to be maintained for a minimum of 3 years and made readily available for BIS surveillance auditors."
        )

        return STIFactoryPlan(
            standard_code="IS 1786:2008",
            product_name="High Strength Deformed Steel Bars and Wires for Concrete Reinforcement",
            daily_tonnage=daily_tonnage,
            operating_shifts=operating_shifts,
            sizes_produced=sizes_produced,
            total_lots_per_day=total_lots,
            total_mandatory_tests_per_day=total_daily_tests,
            testing_quotas=quotas,
            required_equipment=equipment_list,
            sti_document_number="STI/1786/7 (Edition 4)",
            record_keeping_mandate=mandate,
            sampling_summary=summary,
        )

    @classmethod
    def generate_water_sti_plan(
        cls,
        daily_capacity_liters: float = 50000.0,
        operating_shifts: int = 2,
    ) -> STIFactoryPlan:
        """
        Generates STI plan for Packaged/Drinking Water under STI/10500/Doc-1.
        """
        batches = max(math.ceil(daily_capacity_liters / 10000.0), 1)

        quotas: List[TestingQuota] = [
            TestingQuota(
                test_name="pH, Turbidity, Color & Odour Routine Check",
                sampling_rule="Every 2 hours of continuous production stream",
                clause_reference="STI/10500 Clause 2.1 & Table 1",
                estimated_daily_tests=operating_shifts * 4,
                tests_per_month=operating_shifts * 4 * 26,
                test_method_standard="IS 3025 (Parts 4, 10, 11)",
                responsible_person="Water Quality Chemist",
            ),
            TestingQuota(
                test_name="Total Dissolved Solids (TDS) & Total Hardness",
                sampling_rule="1 test per filling batch / shift",
                clause_reference="STI/10500 Clause 2.3",
                estimated_daily_tests=batches,
                tests_per_month=batches * 26,
                test_method_standard="IS 3025 (Parts 16, 21)",
                responsible_person="Analytical Chemist",
            ),
            TestingQuota(
                test_name="Microbiological Screening (E. coli, Coliform, Yeast/Mould)",
                sampling_rule="1 composite test per day per filling line",
                clause_reference="STI/10500 Clause 3.1 & Table 4",
                estimated_daily_tests=2,
                tests_per_month=52,
                test_method_standard="IS 15185 & IS 5403",
                responsible_person="Chief Microbiologist",
            ),
            TestingQuota(
                test_name="Toxic Heavy Metals (Lead, Arsenic, Cadmium, Mercury)",
                sampling_rule="1 composite monthly sample (External or in-house AAS)",
                clause_reference="STI/10500 Clause 4.1 & Table 3",
                estimated_daily_tests=1,  # Projected prorated
                tests_per_month=1,
                test_method_standard="IS 3025 (Parts 37, 41, 47, 48)",
                responsible_person="Senior Analytical Chemist",
            ),
        ]

        total_daily_tests = sum(q.estimated_daily_tests for q in quotas)

        equipment_list: List[LabEquipmentCheck] = [
            LabEquipmentCheck(
                equipment_name="Digital Microprocessor pH & Conductivity Meter",
                purpose="Measurement of pH and TDS (IS 3025 Part 11 & 16)",
                standard_method="IS 3025",
                calibration_frequency_months=3,
                is_mandatory=True,
                audit_check_points="Standard buffer solutions (pH 4.0, 7.0, 9.2), electrode slope check >95%.",
            ),
            LabEquipmentCheck(
                equipment_name="Digital Nephelometric Turbidity Meter",
                purpose="Turbidity measurement in 0-10 NTU range",
                standard_method="IS 3025 Part 10",
                calibration_frequency_months=6,
                is_mandatory=True,
                audit_check_points="Formazin standard suspensions (0.1 NTU, 1.0 NTU, 10.0 NTU).",
            ),
            LabEquipmentCheck(
                equipment_name="Microbiology Lab: Autoclave, Laminar Air Flow & B.O.D. Incubators",
                purpose="Coliform and E. coli incubation at 37°C and 44.5°C",
                standard_method="IS 15185",
                calibration_frequency_months=6,
                is_mandatory=True,
                audit_check_points="Temperature mapping logs, HEPA filter integrity test, negative control sterility checks.",
            ),
            LabEquipmentCheck(
                equipment_name="Atomic Absorption Spectrophotometer (AAS) / Heavy Metal Test Kit",
                purpose="Screening for toxic heavy metals (Pb, As, Cd, Hg)",
                standard_method="IS 3025",
                calibration_frequency_months=12,
                is_mandatory=True,
                audit_check_points="NIST traceable multi-element standard solution calibration curves.",
            ),
        ]

        return STIFactoryPlan(
            standard_code="IS 10500:2012",
            product_name="Drinking Water — Specification (Potable Water Bottling & Distribution)",
            daily_tonnage=daily_capacity_liters / 1000.0,  # in kL
            operating_shifts=operating_shifts,
            sizes_produced=[1],  # 1L / bulk
            total_lots_per_day=batches,
            total_mandatory_tests_per_day=total_daily_tests,
            testing_quotas=quotas,
            required_equipment=equipment_list,
            sti_document_number="STI/10500/Doc-1",
            record_keeping_mandate="Maintain all bacteriological and chemical logs for 2 years per BIS Scheme-I regulations.",
            sampling_summary=f"For {daily_capacity_liters:,.0f} Litres/day capacity across {operating_shifts} shifts: Minimum {total_daily_tests} daily tests across {batches} filling batches.",
        )
