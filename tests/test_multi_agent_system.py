"""
tests/test_multi_agent_system.py
Comprehensive End-to-End Multi-Agent System Verification Suite.
Verifies the complete 4-stage sovereign air-gapped pipeline:
1. Golden Path End-to-End (clean inspection to signed deliverable).
2. Anomaly Gating & Automated Halting (unverified extraction blocked).
3. Human Approval Recovery: CORRECT_AND_RERUN (injected parameters + ledger hash).
4. Human Approval Recovery: CONFIRM_UNEDITED (ratified anomaly + recovery edge).
5. Compliance Causal Dependency (safe vessel Delta > 0 rejects emergency CVC).
6. PAC Expiry Rejection by Chief Reviewer Gatekeeper.
7. Ollama Service Outage Fail-Fast (no pseudo-heuristics, zero deliverables).
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from agent_orchestrator.state import create_initial_state, MultiAgentSystemState
from agent_orchestrator.base_agent import OllamaOfflineException
from agent_orchestrator.multi_agent_graph import build_multi_agent_graph, run_multi_agent_pipeline
from tools.routing_guard import execute_human_override
from tools.audit_trail import verify_audit_ledger_integrity, append_audit_event


def test_01_golden_path_end_to_end():
    """
    Scenario 1: Clean report proceeds through all stages to signed deliverable.
    """
    print("\n--- Test 01: Multi-Agent System Golden Path End-to-End ---")
    query = (
        "Statutory inspection report for vessel 11-V-102 (1st Stage HP Separator Drum). "
        "Base Material: 2.25Cr-1Mo + 347 SS cladding. "
        "Design Pressure: 14.5 MPa, Inside Radius: 1200.0 mm, Allowable Stress: 138.0 MPa, "
        "Measured Thickness: 138.20 mm, Joint Efficiency: 1.0, Corrosion Allowance: 4.0 mm, "
        "Corrosion Rate: 0.75 mm/yr. PAC Ref: PAC-2026-OEM-V102, Valid Until: 2026-12-31, "
        "Estimated Cost INR: 48500000."
    )

    final_state = run_multi_agent_pipeline(user_query=query)

    # 1. Verify Planning
    assert final_state.get("mission_plan") is not None
    assert len(final_state["mission_plan"]) >= 4
    print(f"  [PASS] Supervisor Mission Plan generated ({len(final_state['mission_plan'])} steps).")

    # 2. Verify Extraction & Routing
    insp = final_state.get("inspection_data", {})
    assert insp.get("status") == "VERIFIED_CONFIDENT"
    assert final_state.get("requires_human_confirmation") is False
    print("  [PASS] Inspection data extracted and verified clean; human gating bypassed.")

    # 3. Verify Deterministic ASME Calculation
    calc = final_state.get("calculation_data", {})
    assert calc is not None
    assert calc["t_req_mm"] == 138.57
    assert calc["delta_mm"] == -0.37
    assert calc["status"] == "CRITICAL_BREACH"
    assert calc["remaining_life_years"] < 0
    print(f"  [PASS] Math Worker computed ASME Section VIII t_req={calc['t_req_mm']} mm, delta={calc['delta_mm']} mm.")

    # 4. Verify Compliance
    comp = final_state.get("compliance_data", {})
    assert comp is not None
    assert comp["cvc_justification_valid"] is True
    assert comp["sanction_authority"] in ("Director (Refineries)", "Chairman / Board of Directors")
    print(f"  [PASS] Compliance Worker justified emergency sole-source sanction: {comp['sanction_authority']}")

    # 5. Verify Reviewer & Publisher
    review = final_state.get("review_verdict", {})
    assert review.get("is_approved") is True
    assert review.get("air_gap_verified") is True
    print(f"  [PASS] Chief Reviewer approved package: {review.get('verdict')}")

    deliv = final_state.get("deliverable_payload", {})
    assert deliv.get("docx_path") is not None
    assert Path(deliv["docx_path"]).exists()
    assert Path(deliv["pdf_path"]).exists()
    assert deliv.get("docx_sha256") is not None
    assert final_state["pipeline_status"] == "PUBLISHED"
    print(f"  [PASS] Deliverables published with SHA-256 seal: {deliv['docx_sha256'][:16]}...")
    print("  --> Test 01 PASSED.")


def test_02_anomaly_gating_and_automated_halting():
    """
    Scenario 2: Extraction anomaly (CR = 15.0 mm/yr) halts pipeline at gate; math never runs.
    """
    print("\n--- Test 02: Anomaly Gating & Enforced Automated Halting ---")
    query = (
        "Statutory inspection report for vessel 11-V-102. "
        "Design Pressure: 14.5 MPa, Inside Radius: 1200.0 mm, Allowable Stress: 138.0 MPa, "
        "Measured Thickness: 138.20 mm, Joint Efficiency: 1.0, Corrosion Allowance: 4.0 mm, "
        "Corrosion Rate: 15.0 mm/yr."  # Exceeds physical 10.0 mm/yr ceiling!
    )

    final_state = run_multi_agent_pipeline(user_query=query)

    # Asserts
    assert final_state.get("requires_human_confirmation") is True
    assert final_state.get("pipeline_status") in ("GATE_WAITING_HUMAN", "PIPELINE_HALTED")
    assert final_state.get("calculation_data") is None, "Math Worker must NEVER execute on unverified data!"
    assert final_state.get("deliverable_payload") is None, "No deliverables may be emitted on gated anomalies!"
    print(f"  [PASS] Pipeline halted cleanly: status={final_state.get('pipeline_status')}, calculation_data=None")
    print("  --> Test 02 PASSED.")


def test_03_human_approval_recovery_correct_and_rerun():
    """
    Scenario 3: OCR misreads thickness (t = 250 mm), tripping anomaly.
    Human operator injects verified parameters (CORRECT_AND_RERUN).
    Pipeline resumes into Math Worker on corrected data and writes SHA-256 ledger entry.
    """
    print("\n--- Test 03: Human Approval Recovery (CORRECT_AND_RERUN) ---")
    query = (
        "Vessel 11-V-102. Design Pressure: 14.5 MPa, Inside Radius: 1200.0 mm, Allowable Stress: 138.0 MPa, "
        "Measured Thickness: 250.0 mm, Joint Efficiency: 1.0, Corrosion Allowance: 4.0 mm, Corrosion Rate: 15.0 mm/yr."
    )

    # Initial run trips the anomaly
    graph = build_multi_agent_graph()
    state = create_initial_state(user_query=query)

    # Step 1: Supervisor + Inspection
    state = graph.invoke(state)
    assert state.get("requires_human_confirmation") is True
    assert state.get("calculation_data") is None

    # Step 2: Operator supplies verified correction via execute_human_override
    corrected_params = {
        "measured_thickness_mm": 138.20,
        "corrosion_rate_mm_yr": 0.75,
        "joint_efficiency": 1.0,
        "corrosion_allowance_mm": 4.0,
        "pac_certificate_ref": "PAC-2026-OEM-V102",
        "pac_valid_until": "2026-12-31",
    }
    state = execute_human_override(
        state=state,
        action="CORRECT_AND_RERUN",
        override_by="R. Sharma (Chief Refinery Inspector, IOCL)",
        override_reason="Corrected OCR decimal shift: physical UT gauge confirmed 138.20 mm; CR is 0.75 mm/yr.",
        corrected_parameters=corrected_params
    )

    # Verify override record & ledger anchoring
    override = state.get("human_override")
    assert override is not None
    assert override["action"] == "CORRECT_AND_RERUN"
    assert override["ledger_entry_hash"] is not None
    assert state["requires_human_confirmation"] is False
    print(f"  [PASS] Human override ledger entry anchored with SHA-256: {override['ledger_entry_hash'][:16]}...")

    # Step 3: Resume pipeline execution into Math Worker
    final_state = graph.invoke(state)

    # Verify calculation ran on CORRECTED thickness
    calc = final_state.get("calculation_data")
    assert calc is not None
    assert calc["measured_thickness_mm"] == 138.20
    assert calc["t_req_mm"] == 138.57
    assert calc["status"] == "CRITICAL_BREACH"
    assert final_state["pipeline_status"] == "PUBLISHED"
    print(f"  [PASS] Recovery edge verified: Math Worker evaluated corrected thickness {calc['measured_thickness_mm']} mm.")
    print("  --> Test 03 PASSED.")


def test_04_human_approval_recovery_confirm_unedited():
    """
    Scenario 4: Severe cracking confirmed unedited by human inspector.
    Pipeline resumes into Math Worker with original parameters.
    """
    print("\n--- Test 04: Human Approval Recovery (CONFIRM_UNEDITED) ---")
    query = (
        "Vessel 11-V-102. Design Pressure: 14.5 MPa, Inside Radius: 1200.0 mm, Allowable Stress: 138.0 MPa, "
        "Measured Thickness: 138.20 mm, Joint Efficiency: 1.0, Corrosion Allowance: 4.0 mm, Corrosion Rate: 5.0 mm/yr."
    )

    graph = build_multi_agent_graph()
    state = create_initial_state(user_query=query)
    state = graph.invoke(state)

    # Assume human confirms unedited
    state = execute_human_override(
        state=state,
        action="CONFIRM_UNEDITED",
        override_by="A. K. Verma (NDT Superintendent)",
        override_reason="Severe sour-cracking loss confirmed by specialized ultrasonic phased array."
    )

    assert state["requires_human_confirmation"] is False
    final_state = graph.invoke(state)
    assert final_state.get("calculation_data") is not None
    print(f"  [PASS] CONFIRM_UNEDITED successfully authorized ASME evaluation on original parameters.")
    print("  --> Test 04 PASSED.")


def test_05_compliance_causal_dependency():
    """
    Scenario 5: Safe vessel (Delta > 0) -> Compliance Worker rejects emergency CVC justification.
    """
    print("\n--- Test 05: Compliance Causal Dependency (Safe Vessel Delta > 0) ---")
    query = (
        "Statutory inspection report for vessel 11-V-102. "
        "Design Pressure: 14.5 MPa, Inside Radius: 1200.0 mm, Allowable Stress: 138.0 MPa, "
        "Measured Thickness: 155.00 mm, Joint Efficiency: 1.0, Corrosion Allowance: 4.0 mm, "  # Thick, well above t_req 138.57 mm
        "Corrosion Rate: 0.20 mm/yr. PAC Ref: PAC-2026-OEM-V102, Valid Until: 2026-12-31."
    )

    final_state = run_multi_agent_pipeline(user_query=query)
    calc = final_state.get("calculation_data")
    assert calc["delta_mm"] > 0
    assert calc["status"] in ("SAFE", "ACCEPTABLE")

    comp = final_state.get("compliance_data")
    assert comp["is_emergency_justified"] is False
    assert comp["cvc_justification_valid"] is False
    assert "COMPLIANT" in comp["verdict"]
    print(f"  [PASS] Causal ordering enforced: Safe vessel (+{calc['delta_mm']} mm) rejected emergency single-source under CVC.")
    print("  --> Test 05 PASSED.")


def test_06_pac_expiry_rejection_by_chief_reviewer():
    """
    Scenario 6: PAC certificate expired -> Chief Reviewer issues REJECTED_AUDIT_HOLD; halted.
    """
    print("\n--- Test 06: PAC Expiry Rejection by Chief Reviewer Gatekeeper ---")
    query = (
        "Statutory inspection report for vessel 11-V-102. "
        "Design Pressure: 14.5 MPa, Inside Radius: 1200.0 mm, Allowable Stress: 138.0 MPa, "
        "Measured Thickness: 138.20 mm, Joint Efficiency: 1.0, Corrosion Allowance: 4.0 mm, "
        "Corrosion Rate: 0.75 mm/yr. PAC Ref: PAC-2026-OEM-V102, Valid Until: 2022-01-01."  # EXPIRED PAC!
    )

    final_state = run_multi_agent_pipeline(user_query=query)
    review = final_state.get("review_verdict")
    assert review is not None
    assert review["is_approved"] is False
    assert review["verdict"] == "REJECTED_AUDIT_HOLD"
    assert any("EXPIRED" in r or "compliance" in r.lower() for r in review["rejection_reasons"])
    assert final_state["deliverable_payload"] is None
    print(f"  [PASS] Chief Reviewer caught expired PAC certificate: {review['rejection_reasons']}")
    print("  --> Test 06 PASSED.")


def test_07_ollama_service_outage_fail_fast():
    """
    Scenario 7: Simulates Ollama outage -> Pipeline fails fast with HALTED_OLLAMA_SERVICE_UNAVAILABLE.
    Zero deliverables produced.
    """
    print("\n--- Test 07: Local Ollama Outage Fail-Fast Check ---")
    query = "Inspect vessel 11-V-102."

    with patch("agent_orchestrator.base_agent.call_ollama", side_effect=OllamaOfflineException("Ollama daemon offline on port 11434")):
        final_state = run_multi_agent_pipeline(user_query=query)
        assert final_state["pipeline_status"] == "HALTED_OLLAMA_SERVICE_UNAVAILABLE"
        assert final_state.get("deliverable_payload") is None
        print(f"  [PASS] Pipeline halted immediately on Ollama outage: status={final_state['pipeline_status']}")
        print("  --> Test 07 PASSED.")


if __name__ == "__main__":
    print("==================================================================")
    print("  STARTING MULTI-AGENT ORCHESTRATION INTEGRATION TEST SUITE")
    print("==================================================================")
    test_01_golden_path_end_to_end()
    test_02_anomaly_gating_and_automated_halting()
    test_03_human_approval_recovery_correct_and_rerun()
    test_04_human_approval_recovery_confirm_unedited()
    test_05_compliance_causal_dependency()
    test_06_pac_expiry_rejection_by_chief_reviewer()
    test_07_ollama_service_outage_fail_fast()
    print("\n==================================================================")
    print("  ALL 7 MULTI-AGENT INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================================")
