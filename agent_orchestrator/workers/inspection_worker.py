"""
agent_orchestrator/workers/inspection_worker.py
Inspection Worker Node.
Executes multimodal document parsing and parameter extraction via inspection_extractor_tool.
Enforces physical plausibility bounds and sets requires_human_confirmation on anomalies.
"""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
from tools.inspection_extractor_tool import extract_inspection_parameters
from tools.audit_trail import append_audit_event
from config.settings import logger


def inspection_worker_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Inspection Worker: Ingests uploaded inspection documents (PDF, image, text)
    and extracts core engineering parameters with physical sanity validation.
    """
    file_path = state.get("uploaded_file_path")
    user_query = state.get("user_query", "")

    # If human operator already confirmed or corrected data, preserve verified parameters
    if state.get("human_override") and not state.get("requires_human_confirmation", True):
        logger.info("[InspectionWorker] Human override active; preserving verified parameters.")
        return state

    logger.info(f"[InspectionWorker] Running extraction on file: {file_path}")

    # Invoke audited inspection extractor tool
    extraction_res = extract_inspection_parameters(
        file_path=file_path,
        raw_text=user_query if not file_path else None
    )

    state["inspection_data"] = extraction_res
    requires_conf = extraction_res.get("requires_human_confirmation", False)
    state["requires_human_confirmation"] = requires_conf

    if requires_conf:
        logger.warning(
            f"[InspectionWorker] Human confirmation required: {extraction_res.get('validation_warnings')}"
        )

    entry_hash = append_audit_event(
        tool_name="inspection_worker_node",
        inputs={"file_path": file_path},
        outputs={
            "status": extraction_res.get("status"),
            "confidence_score": extraction_res.get("confidence_score"),
            "requires_human_confirmation": requires_conf,
            "validation_warnings": extraction_res.get("validation_warnings", []),
        },
        status="EXTRACTION_COMPLETE",
        caller="inspection_worker_node"
    )
    state.setdefault("audit_trail_events", []).append(entry_hash)

    return state
