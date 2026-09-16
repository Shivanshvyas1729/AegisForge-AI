"""
tools/routing_guard.py
Multi-Agent Supervisor Routing Guard & Dispatch Controller.
Structurally enforces pipeline halting whenever inspection parameter extraction
triggers human-confirmation gating (requires_human_confirmation == True).
Guarantees that downstream ASME calculation tools are NEVER invoked on unverified data.
Provides 3-way Human Approval Gate execution (CONFIRM_UNEDITED, CORRECT_AND_RERUN, REJECT_AND_HALT)
with permanent cryptographic anchoring into the sovereign audit ledger.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.asme_calculator import evaluate_vessel_integrity
from schemas.mvp_schema import InspectionInput
from tools.audit_trail import append_audit_event


def supervisor_dispatch_guard(
    extraction_output: Dict[str, Any],
    allow_human_override: bool = False
) -> Dict[str, Any]:
    """
    Evaluates extraction results and conditionally routes:
    - If requires_human_confirmation is True and allow_human_override is False:
      STRICTLY BLOCKS dispatch to ASME math engine, returning DISPATCH_BLOCKED_AWAITING_HUMAN_CONFIRMATION.
    - If clean (requires_human_confirmation == False) or explicitly overridden by human engineer:
      Authorizes dispatch and invokes ASME Section VIII Div 1 calculation.
    """
    requires_confirmation = extraction_output.get("requires_human_confirmation", True)
    status = extraction_output.get("status", "UNKNOWN")
    params = extraction_output.get("extracted_parameters", {})

    # 1. Structural Gate Enforcement
    if requires_confirmation and not allow_human_override:
        event = {
            "routing_verdict": "DISPATCH_BLOCKED_AWAITING_HUMAN_CONFIRMATION",
            "dispatch_authorized": False,
            "blocked_reason": (
                f"Supervisor Routing Guard Triggered: Extraction status '{status}' "
                f"requires mandatory human confirmation. Automated dispatch to ASME calculator is blocked."
            ),
            "validation_warnings": extraction_output.get("validation_warnings", []),
            "calculation_result": None,
        }
        append_audit_event(
            tool_name="supervisor_dispatch_guard",
            inputs={"file_name": extraction_output.get("file_name"), "status": status},
            outputs={"routing_verdict": event["routing_verdict"], "blocked": True},
            status="GATE_BLOCKED",
            caller="supervisor_dispatch_guard"
        )
        return event

    # 2. Parameter Completeness Validation (No Non-Conservative Defaults)
    missing_fields = []
    required_keys = [
        "equipment_id",
        "design_pressure_mpa",
        "inside_radius_mm",
        "allowable_stress_mpa",
        "measured_thickness_mm",
        "joint_efficiency",
        "corrosion_allowance_mm",
    ]
    for req in required_keys:
        if req not in params or params[req] is None:
            missing_fields.append(req)

    if missing_fields:
        event = {
            "routing_verdict": "DISPATCH_REJECTED_MISSING_MANDATORY_PARAMETERS",
            "dispatch_authorized": False,
            "blocked_reason": f"Cannot invoke ASME engine: missing mandatory parameters {missing_fields}",
            "calculation_result": None,
        }
        append_audit_event(
            tool_name="supervisor_dispatch_guard",
            inputs={"file_name": extraction_output.get("file_name")},
            outputs={"routing_verdict": event["routing_verdict"], "missing": missing_fields},
            status="PARAMETER_REJECTED",
            caller="supervisor_dispatch_guard"
        )
        return event

    # 3. Authorized Dispatch to ASME Engine
    inp = InspectionInput(
        equipment_id=str(params["equipment_id"]),
        design_pressure_mpa=float(params["design_pressure_mpa"]),
        inside_radius_mm=float(params["inside_radius_mm"]),
        allowable_stress_mpa=float(params["allowable_stress_mpa"]),
        measured_thickness_mm=float(params["measured_thickness_mm"]),
        joint_efficiency=float(params["joint_efficiency"]),
        corrosion_allowance_mm=float(params["corrosion_allowance_mm"]),
        corrosion_rate_mm_yr=float(params.get("corrosion_rate_mm_yr", 0.0)),
    )
    calc_res = evaluate_vessel_integrity(inp)

    event = {
        "routing_verdict": "DISPATCH_AUTHORIZED_AND_EXECUTED",
        "dispatch_authorized": True,
        "calculation_result": calc_res.model_dump(),
    }
    append_audit_event(
        tool_name="supervisor_dispatch_guard",
        inputs={"equipment_id": inp.equipment_id},
        outputs={"t_req_mm": calc_res.t_req_mm, "status": calc_res.status},
        status="DISPATCH_SUCCESS",
        caller="supervisor_dispatch_guard"
    )
    return event


def execute_human_override(
    state: Dict[str, Any],
    action: str,
    override_by: str,
    override_reason: str,
    corrected_parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Executes 3-way Human Approval Gate intervention:
    1. CONFIRM_UNEDITED: Certifies extracted anomaly is physically real. Clears confirmation flag.
    2. CORRECT_AND_RERUN: Injects verified parameters to fix OCR/measurement errors. Merges corrections, clears flag.
    3. REJECT_AND_HALT: Rejects extraction. Halts pipeline.

    Permanently writes the override action and parameter diffs into sovereign_audit_ledger.jsonl
    and appends the entry hash into state['audit_trail_events'].
    """
    valid_actions = {"CONFIRM_UNEDITED", "CORRECT_AND_RERUN", "REJECT_AND_HALT"}
    if action not in valid_actions:
        raise ValueError(f"Invalid human override action '{action}'. Expected one of {valid_actions}")

    timestamp_utc = datetime.utcnow().isoformat() + "Z"
    inspection_data = state.setdefault("inspection_data", {})
    extracted_params = inspection_data.setdefault("extracted_parameters", {})
    original_params = dict(extracted_params)

    if action == "CONFIRM_UNEDITED":
        state["requires_human_confirmation"] = False
        state["pipeline_status"] = "IN_PROGRESS"
        override_record = {
            "action": "CONFIRM_UNEDITED",
            "override_by": override_by,
            "reason": override_reason,
            "original_parameters": original_params,
            "corrected_parameters": None,
            "timestamp_utc": timestamp_utc,
        }
        entry_record = append_audit_event(
            tool_name="human_approval_gate",
            inputs={
                "action": action,
                "override_by": override_by,
                "reason": override_reason,
                "original_parameters": original_params,
            },
            outputs={
                "verdict": "AUTHORIZED_PROCEED_TO_MATH_UNEDITED",
                "requires_human_confirmation": False,
            },
            status="HUMAN_OVERRIDE_CONFIRMED",
            caller="human_approval_gate"
        )
        entry_hash = entry_record.get("entry_hash") if isinstance(entry_record, dict) else str(entry_record)
        override_record["ledger_entry_hash"] = entry_hash
        state["human_override"] = override_record
        state.setdefault("audit_trail_events", []).append(entry_hash)

    elif action == "CORRECT_AND_RERUN":
        if not corrected_parameters or not isinstance(corrected_parameters, dict):
            raise ValueError("CORRECT_AND_RERUN requires non-empty corrected_parameters dictionary.")

        extracted_params.update(corrected_parameters)
        state["requires_human_confirmation"] = False
        state["pipeline_status"] = "IN_PROGRESS"
        override_record = {
            "action": "CORRECT_AND_RERUN",
            "override_by": override_by,
            "reason": override_reason,
            "original_parameters": original_params,
            "corrected_parameters": corrected_parameters,
            "timestamp_utc": timestamp_utc,
        }
        entry_record = append_audit_event(
            tool_name="human_approval_gate",
            inputs={
                "action": action,
                "override_by": override_by,
                "reason": override_reason,
                "original_parameters": original_params,
                "corrected_parameters": corrected_parameters,
            },
            outputs={
                "verdict": "AUTHORIZED_PROCEED_TO_MATH_WITH_CORRECTIONS",
                "requires_human_confirmation": False,
            },
            status="HUMAN_OVERRIDE_CORRECTED",
            caller="human_approval_gate"
        )
        entry_hash = entry_record.get("entry_hash") if isinstance(entry_record, dict) else str(entry_record)
        override_record["ledger_entry_hash"] = entry_hash
        state["human_override"] = override_record
        state.setdefault("audit_trail_events", []).append(entry_hash)

    elif action == "REJECT_AND_HALT":
        state["requires_human_confirmation"] = True
        state["pipeline_status"] = "HALTED_BY_HUMAN_OVERRIDE"
        state["calculation_data"] = None
        override_record = {
            "action": "REJECT_AND_HALT",
            "override_by": override_by,
            "reason": override_reason,
            "original_parameters": original_params,
            "corrected_parameters": None,
            "timestamp_utc": timestamp_utc,
        }
        entry_record = append_audit_event(
            tool_name="human_approval_gate",
            inputs={
                "action": action,
                "override_by": override_by,
                "reason": override_reason,
                "original_parameters": original_params,
            },
            outputs={
                "verdict": "DISPATCH_HALTED_BY_HUMAN_REJECTION",
                "requires_human_confirmation": True,
            },
            status="HUMAN_OVERRIDE_REJECTED",
            caller="human_approval_gate"
        )
        entry_hash = entry_record.get("entry_hash") if isinstance(entry_record, dict) else str(entry_record)
        override_record["ledger_entry_hash"] = entry_hash
        state["human_override"] = override_record
        state.setdefault("audit_trail_events", []).append(entry_hash)

    return state
