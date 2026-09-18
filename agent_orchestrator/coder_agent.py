"""
agent_orchestrator/coder_agent.py
Qwen2.5-Coder Node for Mathematical & Scripting Execution.
Executes deterministic engineering tools and code logic.
"""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
import agent_orchestrator.base_agent as base_agent
from config.settings import MODEL_REGISTRY, logger

from tools.rag import rag_tool
from tools.asme_calculator import evaluate_vessel_integrity
from tools.material_lookup_tool import lookup_allowable_stress
from tools.api_579_ffs_tool import evaluate_lta
from schemas.mvp_schema import InspectionInput

def coder_agent_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    logger.info("[CoderAgent] Activated Qwen2.5-Coder.")
    current_task = state.get("current_task")
    if not current_task:
        return state
        
    model_name = MODEL_REGISTRY.get("coding", "qwen2.5-coder:1.5b")
    instructions = current_task.get("instructions", "")
    feedback = current_task.get("feedback", "")
    
    # 1. Deterministic Execution Phase
    inspection_data = state.get("inspection_data") or {}
    params = inspection_data.get("extracted_parameters", {})
    
    calc_results = {}
    
    if params:
        try:
            material = str(params.get("material", "Carbon Steel"))
            # Tool 1: Material Lookup to prevent hallucination
            allowable_stress = lookup_allowable_stress(material)
            
            inp = InspectionInput(
                equipment_id=str(params.get("equipment_id", "VESSEL-UNKNOWN")),
                equipment_name=str(params.get("equipment_name", "Pressure Vessel")),
                critical_location=str(params.get("critical_location", "Shell")),
                material=material,
                design_pressure_mpa=float(params.get("design_pressure_mpa", 1.0)),
                inside_radius_mm=float(params.get("inside_radius_mm", 1000.0)),
                allowable_stress_mpa=allowable_stress,
                measured_thickness_mm=float(params.get("measured_thickness_mm", 10.0)),
                joint_efficiency=float(params.get("joint_efficiency", 1.0)),
                corrosion_allowance_mm=float(params.get("corrosion_allowance_mm", 0.0)),
                corrosion_rate_mm_yr=float(params.get("corrosion_rate_mm_yr", 0.1)),
                inspector_notes="Automated extraction"
            )
            
            # Tool 2: ASME Calculation
            asme_res = evaluate_vessel_integrity(inp)
            calc_results["asme_ug27"] = asme_res.model_dump()
            
            # Tool 3: API 579 FFS (if breach)
            if asme_res.is_breach:
                # Assume a tiny flaw length for LTA evaluation if not provided
                flaw_len = float(params.get("flaw_length_mm", 50.0))
                ffs_res = evaluate_lta(
                    t_actual_global=inp.measured_thickness_mm,
                    t_min_lta=inp.measured_thickness_mm, # Worst case
                    t_req=asme_res.t_req_mm,
                    flaw_length_mm=flaw_len,
                    inside_radius_mm=inp.inside_radius_mm
                )
                calc_results["api_579_ffs"] = ffs_res
            else:
                calc_results["api_579_ffs"] = "Not Required (Safe Global Thickness)"

            state["calculation_data"] = calc_results
        except Exception as e:
            calc_results = {"error": str(e)}
            logger.error(f"[CoderAgent] Deterministic execution failed: {e}")

    # 2. RAG Context Gathering
    rag_context = ""
    try:
        if rag_tool:
            rag_context = rag_tool.invoke("ASME UG-27 and API 579 requirements")
    except Exception as e:
        logger.warning(f"RAG failed in CoderAgent: {e}")

    # 3. LLM Summarization Phase
    prompt = (
        f"Task: {instructions}\n"
        f"Feedback: {feedback}\n"
        f"Deterministic Math Results: {calc_results}\n"
        f"RAG Context: {rag_context}\n"
        "Provide a clear, strictly factual engineering summary of the math results."
    )
    try:
        output = base_agent.call_ollama(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a strict deterministic mathematical and engineering assistant. Do not invent numbers."
        )
    except Exception as e:
        output = f"Error calling LLM: {e}"
        
    current_task["output"] = output
    state["current_task"] = current_task
    state["next_node"] = "supervisor"
    return state
