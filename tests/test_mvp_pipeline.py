"""
tests/test_mvp_pipeline.py
Automated end-to-end integration test validating the Golden Path MVP workflow:
Inspection Defect Ingestion -> ASME Code Verification -> DeepSeek-R1 Synthesis -> Native Word (.docx) Generation.
"""

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from agent_orchestrator.orchestrator_mvp import run_mvp_pipeline


def test_golden_path_mvp():
    sample_log = PROJECT_ROOT / "sample_data" / "06_inspection_reports" / "field_inspector_raw_ocr_log.txt"
    assert sample_log.exists(), f"Sample log not found at: {sample_log}"

    # Execute full pipeline
    payload = run_mvp_pipeline(sample_log, output_filename="Test_IOCL_Approval_Note.docx")

    # Assert Step 1: Ingestion
    assert payload.inspection_data.equipment_id == "11-V-102"
    assert payload.inspection_data.measured_thickness_mm == 138.20
    assert payload.inspection_data.critical_location == "BK-01"

    # Assert Step 2: ASME Engineering Calculations
    assert payload.calculation_data.t_req_mm == 138.57
    assert payload.calculation_data.delta_mm == -0.37
    assert payload.calculation_data.is_breach is True
    assert payload.calculation_data.remaining_life_years < 0
    assert payload.calculation_data.status == "CRITICAL_BREACH"

    # Assert Step 3: Reasoning
    assert len(payload.reasoning_data.executive_summary) > 20
    assert "CVC" in payload.reasoning_data.cvc_guideline_clause

    # Assert Step 4: Word Document Emission
    assert os.path.exists(payload.docx_path)
    assert os.path.getsize(payload.docx_path) > 5000
    assert len(payload.sha256_hash) == 64

    print("\n" + "=" * 60)
    print("🎉 ALL END-TO-END INTEGRATION TESTS PASSED (100% GREEN)!")
    print(f"Generated Document: {payload.docx_path}")
    print(f"Integrity SHA-256:  {payload.sha256_hash}")
    print("=" * 60)


if __name__ == "__main__":
    test_golden_path_mvp()
