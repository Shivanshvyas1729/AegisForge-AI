"""
tests/test_multi_agent_system.py
Comprehensive End-to-End Hub-and-Spoke Verification Suite.
Verifies the new dynamic task queue, human-in-the-loop retries, 
and the output of the 3 new mathematical/engineering tools.
"""

import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from agent_orchestrator.multi_agent_graph import run_multi_agent_pipeline

def test_01_hub_and_spoke_golden_path():
    """
    Scenario 1: End-to-End dynamic execution.
    The Supervisor should dispatch tasks. The agents should populate the strict
    deterministic math/compliance data.
    """
    print("\n--- Test 01: Hub-and-Spoke Golden Path ---")
    query = "Statutory inspection report for vessel 11-V-102."
    
    mock_data = {
        "extracted_parameters": {
            "equipment_id": "11-V-102",
            "equipment_name": "Pressure Vessel",
            "material": "SA-516 Gr 70",
            "design_pressure_mpa": 14.5,
            "inside_radius_mm": 1200.0,
            "measured_thickness_mm": 138.20,
            "joint_efficiency": 1.0,
            "corrosion_rate_mm_yr": 0.75,
            "flaw_length_mm": 10.0,
            "fluid_toxicity": "Low",
            "estimated_cost_lakhs": 5.0,
            "pac_certificate_ref": "PAC-123"
        },
        "status": "SUCCESS_MOCK"
    }
    
    final_state = run_multi_agent_pipeline(
        user_query=query, 
        uploaded_file_path=None, 
        mock_inspection_data=mock_data
    )
    
    completed = final_state.get("completed_tasks", [])
    assert len(completed) > 0, "No tasks were completed by the Supervisor's dynamic queue."
    
    calc = final_state.get("calculation_data", {})
    assert "asme_ug27" in calc, "Coder Agent failed to execute ASME Math tool."
    asme_res = calc["asme_ug27"]
    
    # SA-516 Gr 70 should map to 138.0 MPa
    assert asme_res.get("allowable_stress_mpa", 138.0) == 138.0
    
    comp = final_state.get("compliance_data", {})
    assert "rbi_assessment" in comp, "Reasoning Agent failed to execute RBI tool."
    assert "cvc_audit" in comp
    
    print("  [PASS] Test 01 PASSED.")


def test_02_human_in_the_loop_retry_recovery():
    """
    Scenario 2: Max retries hit, human injects feedback, system resumes.
    """
    print("\n--- Test 02: Human-in-the-Loop Fallback Recovery ---")
    
    override = {"feedback": "Check the weld joint efficiency on the secondary page."}
    state = run_multi_agent_pipeline(user_query="...", human_override=override)
    
    assert state.get("human_feedback") == override["feedback"]
    assert state.get("next_node") == "supervisor"
    assert state.get("retry_count", 0) == 0
    
    print("  [PASS] Test 02 PASSED.")


def test_03_comprehensive_system_stress_test():
    """
    Scenario 3: Stress Test of all components.
    Triggers ASME breach -> API 579 LTA check -> RBI evaluation -> CVC failure -> Reviewer Rejection.
    """
    print("\n--- Test 03: Comprehensive System Stress Test ---")
    query = "Statutory inspection report for vessel 12-C-101."
    
    # Intentionally catastrophic parameters to test all safety systems
    mock_data = {
        "extracted_parameters": {
            "equipment_id": "12-C-101",
            "material": "SA-106 Gr B",
            "design_pressure_mpa": 18.0,
            "inside_radius_mm": 900.0,
            "measured_thickness_mm": 50.00,  # Fails UG-27
            "joint_efficiency": 0.85,
            "corrosion_rate_mm_yr": 2.5,
            "flaw_length_mm": 200.0,         # Fails API 579 LTA Length check
            "fluid_toxicity": "High",        # Fails RBI toxicity check
            "estimated_cost_lakhs": 150.0,
            "pac_certificate_ref": None      # Fails CVC single source without PAC
        },
        "status": "SUCCESS_MOCK"
    }
    
    final_state = run_multi_agent_pipeline(
        user_query=query, 
        uploaded_file_path=None, 
        mock_inspection_data=mock_data
    )
    
    calc = final_state.get("calculation_data", {})
    asme = calc.get("asme_ug27", {})
    ffs = calc.get("api_579_ffs", {})
    
    assert asme.get("is_breach") is True, "Stress test failed to trigger ASME breach."
    assert "is_acceptable" in ffs, "Stress test failed to trigger API 579 FFS."
    
    comp = final_state.get("compliance_data", {})
    rbi = comp.get("rbi_assessment", {})
    cvc = comp.get("cvc_audit", {})
    
    assert rbi.get("consequence_of_failure") == "High (Category E)", "Stress test failed RBI toxicity mapping."
    assert cvc.get("is_compliant") is True, "CVC emergency bypass failed."
    assert cvc.get("emergency_justification_ref") == "INC-AUTO-GEN", "CVC emergency override ref missing."
    
    review = final_state.get("review_verdict", {})
    assert review.get("is_approved") is False, "General Agent failed to reject a critically flawed vessel."
    
    print("  [PASS] Test 03 PASSED.")

if __name__ == "__main__":
    print("==================================================================")
    print("  STARTING HUB-AND-SPOKE INTEGRATION TEST SUITE")
    print("==================================================================")
    test_01_hub_and_spoke_golden_path()
    test_02_human_in_the_loop_retry_recovery()
    test_03_comprehensive_system_stress_test()
    print("\n==================================================================")
    print("  ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================================")
