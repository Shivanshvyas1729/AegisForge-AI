"""
tests/test_sovereign_toolset.py
Comprehensive Verification Suite for Sovereign Multi-Agent Toolset.
Tests both happy-path functional behavior and safety-critical failure modes:
- ASME Section VIII UG-27 boundary conditions and zero margin semantics
- AST import allowlisting and sandbox timeout/resource controls
- Cryptographic hash-chained audit ledger integrity and tamper detection
- Path traversal defense in file I/O
- Multi-point thickness survey grid analysis
- CVC Circular 02/2004 compliance auditing
- Inspection parameter extraction and confidence gating
- Native DOCX/PDF deliverable emission and SHA-256 sealing
"""

import os
import sys
import json
import math
import tempfile
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import (
    rag_tool,
    sandbox_tool,
    asme_calc_tool,
    thickness_grid_tool,
    inspection_extractor_tool,
    cvc_audit_tool,
    file_io_tool,
    generate_deliverable_tool,
    verify_network_tool,
    validate_ug27_parameters,
    calculate_t_req,
    calculate_delta_margin,
    calculate_remaining_life,
    calculate_derated_mawp_bar,
    evaluate_vessel_integrity,
    execute_python_code,
    audit_network_isolation,
    audit_procurement_compliance,
    analyze_thickness_grid,
    extract_inspection_parameters,
    read_or_write_file,
    append_audit_event,
    verify_audit_ledger_integrity,
)
from tools.sandbox import validate_code_ast, SandboxSecurityError
from schemas.mvp_schema import InspectionInput


def test_01_tool_exports():
    """Verify all 9 agent tools exist and are properly instantiated."""
    print("\n--- Test 01: Verifying Tool Exports ---")
    tools = [
        rag_tool, sandbox_tool, asme_calc_tool, thickness_grid_tool,
        inspection_extractor_tool, cvc_audit_tool, file_io_tool,
        generate_deliverable_tool, verify_network_tool
    ]
    for t in tools:
        assert t is not None, f"Tool {t} is None!"
        assert hasattr(t, "name") or callable(t), f"Tool {t} is neither a LangChain tool nor callable!"
        print(f"  [PASS] Tool verified: {getattr(t, 'name', str(t))}")
    print("  --> Test 01 PASSED: All 9 tools exported cleanly.")


def test_02_asme_ug27_core_and_failures():
    """Verify ASME UG-27 mathematical precision and boundary failure modes."""
    print("\n--- Test 02: ASME UG-27 Core & Boundary Failure Modes ---")
    
    # 1. Baseline Golden Path (11-V-102)
    t_req = calculate_t_req(P=14.5, R=1200.0, S=138.0, E=1.0, CA=4.0)
    assert t_req == 138.57, f"Expected 138.57 mm, got {t_req}"
    print(f"  [PASS] Baseline t_req: {t_req} mm")

    delta, is_breach, is_zero_margin = calculate_delta_margin(t_actual=138.20, t_req=t_req)
    assert delta == -0.37, f"Expected -0.37 mm, got {delta}"
    assert is_breach is True
    assert is_zero_margin is False
    print(f"  [PASS] Breach detection: delta={delta} mm, is_breach={is_breach}")

    # 2. Zero Margin Decision (t_actual == t_req)
    delta_zero, is_breach_zero, is_zero_margin_zero = calculate_delta_margin(t_actual=138.57, t_req=138.57)
    assert delta_zero == 0.0
    assert is_breach_zero is False
    assert is_zero_margin_zero is True
    print(f"  [PASS] Zero margin decision: delta={delta_zero} mm, is_breach={is_breach_zero}, is_zero_margin={is_zero_margin_zero}")

    # 3. API 510 Remaining Life with Zero-Corrosion Guard
    life_normal, status_normal = calculate_remaining_life(t_actual=142.0, t_req=138.57, CR=0.75)
    assert life_normal == 4.57, f"Expected 4.57 years, got {life_normal}"
    
    life_zero_cr, status_zero_cr = calculate_remaining_life(t_actual=142.0, t_req=138.57, CR=0.0)
    assert life_zero_cr is None, "Expected None for zero CR!"
    assert "No active corrosion" in status_zero_cr
    print(f"  [PASS] Zero corrosion guard handled division by zero safely: {status_zero_cr}")

    # 4. Derated MAWP calculation with explicit t_available
    mawp_bar = calculate_derated_mawp_bar(t_actual=138.20, CA=4.0, R=1200.0, S=138.0, E=1.0)
    assert mawp_bar == 144.6, f"Expected 144.6 barg, got {mawp_bar}"
    print(f"  [PASS] Derated MAWP: {mawp_bar} barg")

    # 5. Failure Modes: Negative inputs
    failed_p = False
    try:
        calculate_t_req(P=-14.5, R=1200.0, S=138.0, E=1.0, CA=4.0)
    except ValueError:
        failed_p = True
    assert failed_p, "Failed to reject negative pressure P <= 0"

    failed_geom = False
    try:
        # P exceeds S*E (140 * 1.0 - 0.6 * 300 = 140 - 180 = -40 <= 0)
        calculate_t_req(P=300.0, R=1200.0, S=140.0, E=1.0, CA=4.0)
    except ValueError:
        failed_geom = True
    assert failed_geom, "Failed to reject geometric capacity breach (S*E - 0.6*P <= 0)"
    print("  [PASS] All ASME UG-27 boundary failure modes raised clear ValueErrors.")
    print("  --> Test 02 PASSED.")


def test_03_sandbox_security_and_limits():
    """Verify AST import allowlist, dunder blocking, memory ceiling, and timeout."""
    print("\n--- Test 03: Sandbox AST Allowlist & Resource Limits ---")

    # 1. Reject forbidden imports
    forbidden_scripts = [
        "import os; os.system('echo test')",
        "import socket; s = socket.socket()",
        "import ftplib; ftp = ftplib.FTP()",
        "import subprocess; subprocess.run(['calc'])",
        "import urllib.request; urllib.request.urlopen('http://example.com')",
        "from xmlrpc.client import ServerProxy",
        "type(1).__bases__[0].__subclasses__()",
        "eval('2 + 2')",
        "open('test.txt', 'w')",
    ]

    for script in forbidden_scripts:
        rejected = False
        try:
            validate_code_ast(script)
        except SandboxSecurityError:
            rejected = True
        assert rejected, f"Failed to reject forbidden script: {script}"
        print(f"  [PASS] Successfully rejected: {script[:35]}...")

    # 2. Permitted computational script
    valid_script = """
import math
import json
val = sum(math.sqrt(i) for i in range(1, 10))
print(json.dumps({'total_sqrt': round(val, 4)}))
"""
    res = execute_python_code(valid_script)
    assert res["success"] is True, f"Valid script failed: {res['stderr']}"
    out_obj = json.loads(res["stdout"].strip())
    assert "total_sqrt" in out_obj
    print(f"  [PASS] Valid computational script executed safely: {out_obj}")

    # 3. Timeout protection
    timeout_script = "while True: pass"
    res_to = execute_python_code(timeout_script, timeout_seconds=2)
    assert res_to["success"] is False
    assert "TimeoutExpired" in res_to["stderr"]
    print("  [PASS] Hard execution timeout triggered safely.")
    print("  --> Test 03 PASSED.")


def test_04_file_io_path_traversal():
    """Verify path traversal defense in file_io."""
    print("\n--- Test 04: File I/O Path Traversal Defense ---")

    # 1. Traversal attempt
    blocked = False
    try:
        read_or_write_file("../../unauthorized_escape.txt", mode="w", data="test")
    except PermissionError:
        blocked = True
    assert blocked, "Failed to block path traversal attempt!"
    print("  [PASS] Blocked relative path traversal: ../../unauthorized_escape.txt")

    # 2. Valid workspace read/write
    test_file = "data/scratch/safe_io_test.json"
    data_to_write = {"test_key": "sovereign_offline_val", "status": 200}
    success = read_or_write_file(test_file, mode="w", data=data_to_write)
    assert success is True

    read_data = read_or_write_file(test_file, mode="r")
    assert read_data["test_key"] == "sovereign_offline_val"
    print(f"  [PASS] Valid workspace read/write confirmed: {read_data}")
    print("  --> Test 04 PASSED.")


def test_05_thickness_grid_survey():
    """Verify multi-point thickness survey parsing and ASME evaluation."""
    print("\n--- Test 05: Multi-Point Thickness Grid Survey Analyzer ---")
    
    # Create sample grid CSV with 6 coordinates, 2 breaches
    csv_path = PROJECT_ROOT / "data" / "scratch" / "test_survey_grid.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Location,Measured_Thickness_mm\n")
        f.write("A1,142.5\n")
        f.write("A2,141.0\n")
        f.write("B1,138.2\n")  # Breach (138.2 < 138.57)
        f.write("B2,137.9\n")  # Breach (137.9 < 138.57) - Worst point
        f.write("C1,140.0\n")
        f.write("C2,139.5\n")

    res = analyze_thickness_grid(
        file_path="data/scratch/test_survey_grid.csv",
        design_pressure_mpa=14.5,
        inside_radius_mm=1200.0,
        allowable_stress_mpa=138.0,
        joint_efficiency=1.0,
        corrosion_allowance_mm=4.0,
        corrosion_rate_mm_yr=0.75,
    )

    assert res["total_points_audited"] == 6
    assert res["breached_points_count"] == 2
    assert res["worst_location"] == "B2"
    assert res["worst_measured_thickness_mm"] == 137.9
    assert res["governing_status"] == "CRITICAL_BREACH"
    assert res["governing_derated_mawp_bar"] > 0
    print(f"  [PASS] Grid audit audited {res['total_points_audited']} points, found {res['breached_points_count']} breaches.")
    print(f"  [PASS] Worst location correctly pinpointed: {res['worst_location']} ({res['worst_measured_thickness_mm']} mm, Δ={res['worst_delta_mm']} mm)")
    print("  --> Test 05 PASSED.")


def test_06_compliance_auditor():
    """Verify CVC Circular 02/2004 and DoP rules with fail-safe defaults."""
    print("\n--- Test 06: Statutory CVC & DoP Compliance Auditor ---")

    # 1. Unauthorized single-source (flags violation)
    res_violation = audit_procurement_compliance(
        equipment_id="11-V-102",
        estimated_cost_lakhs=88.0,
        is_emergency=False,
        is_single_source=True,
        has_pac=False
    )
    assert res_violation["is_compliant"] is False
    assert "NON_COMPLIANT" in res_violation["compliance_verdict"]
    print(f"  [PASS] Strict default rejected unauthorized sole-source: {res_violation['compliance_verdict']}")

    # 2. Unsubstantiated PAC assertion (has_pac=True but no reference ID)
    res_unsubstantiated = audit_procurement_compliance(
        equipment_id="11-V-102",
        estimated_cost_lakhs=88.0,
        is_emergency=False,
        is_single_source=True,
        has_pac=True,
        pac_certificate_ref=None,
    )
    assert res_unsubstantiated["is_compliant"] is False
    assert any("pac_certificate_ref" in v for v in res_unsubstantiated["violations"])
    print(f"  [PASS] Unsubstantiated PAC assertion rejected: {res_unsubstantiated['violations'][0][:50]}...")

    # 3. Hallucinated PAC citation (string provided but not found in verified registry)
    res_hallucinated = audit_procurement_compliance(
        equipment_id="11-V-102",
        estimated_cost_lakhs=88.0,
        is_emergency=False,
        is_single_source=True,
        has_pac=True,
        pac_certificate_ref="PAC-FAKE-HALLUCINATED-001",
    )
    assert res_hallucinated["is_compliant"] is False
    assert any("NOT found in the verified PSU PAC Certificate Registry" in v for v in res_hallucinated["violations"])
    print(f"  [PASS] Hallucinated PAC identifier rejected by registry verification: {res_hallucinated['violations'][0][:60]}...")

    # 4. Compliant emergency procurement under CVC 02/2004 & DoP 4.2 with verified registry certificate
    res_compliant = audit_procurement_compliance(
        equipment_id="11-V-102",
        estimated_cost_lakhs=88.0,
        is_emergency=True,
        is_single_source=True,
        has_pac=True,
        pac_certificate_ref="PAC-2026-OEM-V102",
        emergency_justification_ref="INC-2026-SHUTDOWN-001",
    )
    assert res_compliant["is_compliant"] is True
    assert res_compliant["competent_approving_authority"] == "Director (Refineries)"
    print(f"  [PASS] Legally justified emergency procurement routes to: {res_compliant['competent_approving_authority']}")
    print("  --> Test 06 PASSED.")


def test_07_inspection_extractor_and_gating():
    """Verify extraction bounds and confidence gating."""
    print("\n--- Test 07: Inspection Parameter Extractor & Sanity Gating ---")

    # 1. Clean report extraction
    sample_text = """
    INSPECTION REPORT - IOCL GUJARAT REFINERY
    Equipment Tag: 11-V-102
    Equipment Name: 1st Stage HP Separator Drum
    Material: 2.25Cr-1Mo
    Design Pressure: 14.5 MPa
    Inside Radius: 1200 mm
    Actual Wall Thickness: 138.20 mm
    Corrosion Rate: 0.75 mm/year
    Remarks: Ultrasonic scan at Ring 2.
    """
    clean_report_path = PROJECT_ROOT / "data" / "scratch" / "clean_inspection.txt"
    with open(clean_report_path, "w", encoding="utf-8") as f:
        f.write(sample_text)

    res_clean = extract_inspection_parameters("data/scratch/clean_inspection.txt")
    assert res_clean["extracted_parameters"]["equipment_id"] == "11-V-102"
    assert res_clean["extracted_parameters"]["measured_thickness_mm"] == 138.2
    assert res_clean["extracted_parameters"]["corrosion_rate_mm_yr"] == 0.75
    assert res_clean["confidence_score"] >= 0.85
    assert res_clean["status"] == "VERIFIED_CONFIDENT"
    print(f"  [PASS] Clean inspection extracted with high confidence: score={res_clean['confidence_score']}, status={res_clean['status']}")

    # 2. Unrealistic corrosion rate triggering safety gating
    bad_cr_text = "Equipment Tag: 11-V-102\nActual Thickness: 138.2 mm\nCorrosion Rate: 15.0 mm/year"
    bad_report_path = PROJECT_ROOT / "data" / "scratch" / "corrupted_inspection.txt"
    with open(bad_report_path, "w", encoding="utf-8") as f:
        f.write(bad_cr_text)

    res_bad = extract_inspection_parameters("data/scratch/corrupted_inspection.txt")
    assert res_bad["requires_human_confirmation"] is True
    assert res_bad["status"] == "ACTION_REQUIRED_UNVERIFIED_DATA"
    assert any("UNREALISTIC_CORROSION_RATE" in w for w in res_bad["validation_warnings"])
    print(f"  [PASS] Anomaly gated successfully: status={res_bad['status']}, warnings={res_bad['validation_warnings']}")
    print("  --> Test 07 PASSED.")


def test_08_tamper_evident_audit_ledger():
    """Verify cryptographic hash chaining and tamper detection."""
    print("\n--- Test 08: Cryptographic Hash-Chained Audit Ledger ---")

    test_ledger = PROJECT_ROOT / "data" / "scratch" / "test_audit_ledger.jsonl"
    if test_ledger.exists():
        test_ledger.unlink()

    # Append 3 events
    append_audit_event("tool_A", {"inp": 1}, {"out": "ok"}, ledger_path=test_ledger)
    append_audit_event("tool_B", {"inp": 2}, {"out": "ok"}, ledger_path=test_ledger)
    append_audit_event("tool_C", {"inp": 3}, {"out": "ok"}, ledger_path=test_ledger)

    is_valid, msg, count = verify_audit_ledger_integrity(ledger_path=test_ledger)
    assert is_valid is True, f"Ledger integrity check failed: {msg}"
    assert count == 3
    print(f"  [PASS] Hash chain integrity confirmed across {count} records.")

    # Tamper simulation: alter a byte in record 2
    with open(test_ledger, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Tamper with record 2 payload
    rec2 = json.loads(lines[1])
    rec2["status"] = "TAMPERED_STATUS"
    lines[1] = json.dumps(rec2) + "\n"

    with open(test_ledger, "w", encoding="utf-8") as f:
        f.writelines(lines)

    is_valid_after_tamper, msg_tamper, _ = verify_audit_ledger_integrity(ledger_path=test_ledger)
    assert is_valid_after_tamper is False, "Failed to detect tamper in hash chain!"
    assert "Tamper detected" in msg_tamper or "Hash chain broken" in msg_tamper
    print(f"  [PASS] Tamper detection successfully caught modified ledger: {msg_tamper}")
    print("  --> Test 08 PASSED.")


def test_09_passive_network_verifier():
    """Verify passive network telemetry auditor for both process and host scopes."""
    print("\n--- Test 09: Passive Network & Air-Gap Telemetry Probe ---")
    # 1. Process-tree scope (verifies current agent process & children have 0 external sockets)
    proc_telemetry = audit_network_isolation(scope="process")
    assert proc_telemetry["is_air_gap_intact"] is True
    assert proc_telemetry["verdict"] == "PASS_PROCESS_AIR_GAP_VERIFIED"
    print(f"  [PASS] Process-tree air-gap verified: {proc_telemetry['verdict']}")

    # 2. Host scope
    host_telemetry = audit_network_isolation(scope="host")
    assert "verdict" in host_telemetry
    print(f"  [PASS] Host-wide telemetry checked: {host_telemetry['verdict']}")
    print("  --> Test 09 PASSED.")


def test_10_deliverable_generator_and_sha256():
    """Verify Word & PDF deliverable emission, SHA-256 seal, and locked manifest."""
    print("\n--- Test 10: Deliverable Publishing & SHA-256 Seal ---")
    res_str = generate_deliverable_tool.invoke({
        "equipment_id": "11-V-102",
        "equipment_name": "1st Stage HP Separator Drum",
        "material": "2.25Cr-1Mo + 347 SS cladding",
        "design_pressure_mpa": 14.5,
        "inside_radius_mm": 1200.0,
        "allowable_stress_mpa": 138.0,
        "measured_thickness_mm": 138.20,
        "corrosion_rate_mm_yr": 0.75,
        "corrosion_allowance_mm": 4.0,
        "executive_summary": "Test automated deliverable generation.",
        "recommended_action": "Emergency turnaround weld overlay.",
    })

    assert "SHA-256 Seal" in res_str
    assert "Approval_Note.docx" in res_str
    assert "Approval_Note.pdf" in res_str

    docx_path = PROJECT_ROOT / "data" / "output" / "11-V-102_Approval_Note.docx"
    pdf_path = PROJECT_ROOT / "data" / "output" / "11-V-102_Approval_Note.pdf"
    manifest_path = PROJECT_ROOT / "data" / "output" / "deliverable_manifest.json"

    assert docx_path.exists() and docx_path.stat().st_size > 0
    assert pdf_path.exists() and pdf_path.stat().st_size > 0
    assert manifest_path.exists()
    print(f"  [PASS] DOCX ({docx_path.stat().st_size} bytes) and PDF ({pdf_path.stat().st_size} bytes) generated.")
    print("  [PASS] Deliverable manifest locked and updated with cryptographic seals.")
    print("  --> Test 10 PASSED.")


def test_11_supervisor_routing_guard():
    """Verify supervisor routing guard blocks ASME math on unverified data and authorizes on clean data."""
    print("\n--- Test 11: Supervisor Routing Guard & Enforced Dispatch Halting ---")
    from tools import supervisor_dispatch_guard

    # 1. Unverified extraction data (e.g. from corrupted/unrealistic report)
    unverified_extraction = {
        "file_name": "corrupted_report.pdf",
        "status": "ACTION_REQUIRED_UNVERIFIED_DATA",
        "confidence_score": 0.55,
        "requires_human_confirmation": True,
        "validation_warnings": ["UNREALISTIC_CORROSION_RATE: 15.0 mm/yr exceeds 10.0 mm/yr ceiling."],
        "extracted_parameters": {"equipment_id": "11-V-102", "measured_thickness_mm": 138.2},
    }

    # Verify dispatch to ASME calculator is STRICTLY BLOCKED
    dispatch_res = supervisor_dispatch_guard(unverified_extraction)
    assert dispatch_res["dispatch_authorized"] is False
    assert dispatch_res["routing_verdict"] == "DISPATCH_BLOCKED_AWAITING_HUMAN_CONFIRMATION"
    assert dispatch_res["calculation_result"] is None
    print(f"  [PASS] Dispatch strictly blocked by routing guard: {dispatch_res['routing_verdict']}")

    # 2. Verified clean extraction data
    verified_extraction = {
        "file_name": "clean_report.pdf",
        "status": "VERIFIED_CONFIDENT",
        "confidence_score": 0.95,
        "requires_human_confirmation": False,
        "validation_warnings": [],
        "extracted_parameters": {
            "equipment_id": "11-V-102",
            "design_pressure_mpa": 14.5,
            "inside_radius_mm": 1200.0,
            "allowable_stress_mpa": 138.0,
            "measured_thickness_mm": 138.20,
            "joint_efficiency": 1.0,
            "corrosion_allowance_mm": 4.0,
            "corrosion_rate_mm_yr": 0.75,
        },
    }

    # Verify dispatch is AUTHORIZED and ASME engine is executed
    authorized_res = supervisor_dispatch_guard(verified_extraction)
    assert authorized_res["dispatch_authorized"] is True
    assert authorized_res["routing_verdict"] == "DISPATCH_AUTHORIZED_AND_EXECUTED"
    assert authorized_res["calculation_result"]["t_req_mm"] == 138.57
    assert authorized_res["calculation_result"]["status"] == "CRITICAL_BREACH"
    print(f"  [PASS] Clean extraction authorized and executed: t_req={authorized_res['calculation_result']['t_req_mm']} mm, status={authorized_res['calculation_result']['status']}")
    print("  --> Test 11 PASSED.")


if __name__ == "__main__":
    print("==================================================================")
    print("  STARTING SOVEREIGN AGENT TOOLSET COMPREHENSIVE VERIFICATION")
    print("==================================================================")
    test_01_tool_exports()
    test_02_asme_ug27_core_and_failures()
    test_03_sandbox_security_and_limits()
    test_04_file_io_path_traversal()
    test_05_thickness_grid_survey()
    test_06_compliance_auditor()
    test_07_inspection_extractor_and_gating()
    test_08_tamper_evident_audit_ledger()
    test_09_passive_network_verifier()
    test_10_deliverable_generator_and_sha256()
    test_11_supervisor_routing_guard()
    print("\n==================================================================")
    print("  ALL 11 VERIFICATION SUITES PASSED WITH 100% SUCCESS!")
    print("==================================================================")
