"""
tests/test_tools_and_downloads.py
Comprehensive automated test suite verifying all Layer 4 tools and Layer 5/6 document generators:
- asme_calculator (deterministic math + tool)
- sandbox (subprocess isolation + tool)
- file_io (safe read/write + tool)
- rag (sample knowledge retrieval + tool)
- docx_generator & pdf_generator (native Office & PDF deliverables + hashes)
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from schemas.mvp_schema import InspectionInput, CalculationOutput, ReasoningOutput
from tools.asme_calculator import evaluate_vessel_integrity, asme_calc_tool
from tools.sandbox import execute_python_code, sandbox
from tools.file_io import read_or_write_file, file_io_tool
from tools.rag import search_local_knowledge, rag
from tools.doc_generator import (
    generate_docx_deliverable,
    generate_pdf_deliverable,
    generate_both_deliverables,
)
from output_generation.docx_generator import generate_approval_nfa_docx, compute_file_sha256 as compute_docx_sha256
from output_generation.pdf_generator import generate_approval_nfa_pdf, compute_file_sha256 as compute_pdf_sha256


# ---------------------------------------------------------------------------
# 1. Test ASME Calculator
# ---------------------------------------------------------------------------
def test_asme_calculator_accuracy():
    inp = InspectionInput(
        equipment_id="11-V-102",
        design_pressure_mpa=14.5,
        inside_radius_mm=1200.0,
        allowable_stress_mpa=138.0,
        joint_efficiency=1.0,
        corrosion_allowance_mm=4.0,
        measured_thickness_mm=138.20,
        corrosion_rate_mm_yr=0.75,
    )
    res = evaluate_vessel_integrity(inp)
    assert res.t_req_mm == 138.57
    assert res.delta_mm == -0.37
    assert res.is_breach is True
    assert res.status == "CRITICAL_BREACH"
    assert res.derated_mawp_bar > 0


def test_asme_calculator_langchain_tool():
    if asme_calc_tool:
        output = asme_calc_tool.invoke({
            "equipment_id": "11-V-102",
            "design_pressure_mpa": 14.5,
            "inside_radius_mm": 1200.0,
            "allowable_stress_mpa": 138.0,
            "joint_efficiency": 1.0,
            "corrosion_allowance_mm": 4.0,
            "measured_thickness_mm": 138.20,
            "corrosion_rate_mm_yr": 0.75,
        })
        assert "138.57" in str(output)
        assert "BREACH DETECTED" in str(output)


# ---------------------------------------------------------------------------
# 2. Test Air-Gapped Code Sandbox
# ---------------------------------------------------------------------------
def test_sandbox_execution():
    res = execute_python_code("print(12345 + 54321)")
    assert res["success"] is True
    assert "66666" in res["stdout"]


def test_sandbox_langchain_tool():
    if sandbox:
        output = sandbox.invoke({"code": "print('SANDBOX_OK')"})
        assert "SANDBOX_OK" in str(output)


# ---------------------------------------------------------------------------
# 3. Test Safe File I/O Tool
# ---------------------------------------------------------------------------
def test_file_io_operations(tmp_path):
    txt_file = tmp_path / "test_io.txt"
    json_file = tmp_path / "test_io.json"

    # Text write & read
    assert read_or_write_file(str(txt_file), mode="w", data="AegisForge Sovereign Test") is True
    read_txt = read_or_write_file(str(txt_file), mode="r")
    assert read_txt == "AegisForge Sovereign Test"

    # JSON write & read
    assert read_or_write_file(str(json_file), mode="w", data={"status": "AIR_GAPPED"}) is True
    read_json = read_or_write_file(str(json_file), mode="r")
    assert read_json["status"] == "AIR_GAPPED"


def test_file_io_langchain_tool(tmp_path):
    if file_io_tool:
        test_file = tmp_path / "tool_test.txt"
        w_res = file_io_tool.invoke({"file_path": str(test_file), "mode": "w", "data": "Tool Data"})
        assert "Successfully wrote" in str(w_res)
        r_res = file_io_tool.invoke({"file_path": str(test_file), "mode": "r"})
        assert "Tool Data" in str(r_res)


# ---------------------------------------------------------------------------
# 4. Test RAG Local Knowledge Retrieval
# ---------------------------------------------------------------------------
def test_rag_knowledge_search():
    results = search_local_knowledge("CVC circular emergency procurement")
    assert len(results) > 20
    assert "relevant knowledge snippet" in results.lower() or "source:" in results.lower()


def test_rag_langchain_tool():
    if rag:
        tool_out = rag.invoke({"query": "ASME Section VIII hydrocracker"})
        assert len(str(tool_out)) > 20


# ---------------------------------------------------------------------------
# 5. Test DOCX and PDF Output Deliverable Generators
# ---------------------------------------------------------------------------
def get_sample_payload_data():
    insp = InspectionInput(
        equipment_id="11-V-102",
        equipment_name="HP Separator Drum",
        material="2.25Cr-1Mo",
        design_pressure_mpa=14.5,
        inside_radius_mm=1200.0,
        allowable_stress_mpa=138.0,
        joint_efficiency=1.0,
        corrosion_allowance_mm=4.0,
        critical_location="BK-01",
        measured_thickness_mm=138.20,
        corrosion_rate_mm_yr=0.75,
    )
    calc = evaluate_vessel_integrity(insp)
    reason = ReasoningOutput(
        executive_summary="ASME Section VIII Div 1 wall thickness breach discovered.",
        cvc_guideline_clause="CVC Circular No. 02/02/2004 applies.",
        recommended_action="Emergency Inconel 625 weld overlay repair.",
        estimated_cost="Rs. 88.0 Lakhs",
        raw_model_response="Synthesis model output.",
    )
    return insp, calc, reason


def test_docx_generation(tmp_path, sample_payload_data):
    insp, calc, reason = sample_payload_data
    out_docx = str(tmp_path / "test_nfa.docx")
    path = generate_approval_nfa_docx(insp, calc, reason, out_docx)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000
    sha = compute_docx_sha256(path)
    assert len(sha) == 64


def test_pdf_generation(tmp_path, sample_payload_data):
    insp, calc, reason = sample_payload_data
    out_pdf = str(tmp_path / "test_nfa.pdf")
    path = generate_approval_nfa_pdf(insp, calc, reason, out_pdf)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 1000
    sha = compute_pdf_sha256(path)
    assert len(sha) == 64
    # Verify PDF header
    with open(path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def test_generate_both_deliverables(tmp_path, sample_payload_data):
    insp, calc, reason = sample_payload_data
    both = generate_both_deliverables(insp, calc, reason, "Test_Both", output_dir=tmp_path)
    assert os.path.exists(both["docx"]["path"])
    assert os.path.exists(both["pdf"]["path"])
    assert both["docx"]["size_bytes"] > 1000
    assert both["pdf"]["size_bytes"] > 1000
    assert both["docx"]["sha256"] != both["pdf"]["sha256"]


if __name__ == "__main__":
    import tempfile
    import shutil

    print("Running all Tool & Document tests...")
    
    print("\n1. Testing ASME Calculator...")
    test_asme_calculator_accuracy()
    test_asme_calculator_langchain_tool()
    print("   -> ASME Calculator: PASSED")

    print("\n2. Testing Code Sandbox...")
    test_sandbox_execution()
    test_sandbox_langchain_tool()
    print("   -> Code Sandbox: PASSED")

    temp_d = Path(tempfile.mkdtemp())
    try:
        print("\n3. Testing Safe File I/O...")
        test_file_io_operations(temp_d)
        test_file_io_langchain_tool(temp_d)
        print("   -> Safe File I/O: PASSED")

        print("\n4. Testing Local RAG Knowledge Search...")
        test_rag_knowledge_search()
        test_rag_langchain_tool()
        print("   -> Local RAG: PASSED")

        insp_ex = InspectionInput(equipment_id="11-V-102")
        calc_ex = evaluate_vessel_integrity(insp_ex)
        reason_ex = ReasoningOutput(
            executive_summary="Test summary",
            cvc_guideline_clause="CVC clause",
            recommended_action="Action",
            raw_model_response="Raw"
        )
        sample_tuple = (insp_ex, calc_ex, reason_ex)

        print("\n5. Testing DOCX Generator...")
        test_docx_generation(temp_d, sample_tuple)
        print("   -> DOCX Generator: PASSED")

        print("\n6. Testing PDF Generator...")
        test_pdf_generation(temp_d, sample_tuple)
        print("   -> PDF Generator: PASSED")

        print("\n7. Testing Dual Deliverable Generator...")
        test_generate_both_deliverables(temp_d, sample_tuple)
        print("   -> Dual Deliverables: PASSED")

        print("\n" + "=" * 50)
        print("ALL 7 TOOL & DELIVERABLE TEST SUITES PASSED!")
        print("=" * 50)
    finally:
        shutil.rmtree(temp_d, ignore_errors=True)
