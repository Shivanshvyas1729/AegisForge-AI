"""
agent_orchestrator/reasoning_agent.py
DeepSeek-R1 Node for Compliance & Logical Deductions.
Executes deterministic compliance rules and RBI calculations before summarizing.
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
from tools.risk_based_inspection_tool import calculate_rbi_interval
from tools.compliance_auditor import audit_procurement_compliance

def reasoning_agent_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    logger.info("[ReasoningAgent] Activated DeepSeek-R1.")
    current_task = state.get("current_task")
    if not current_task:
        return state
        
    model_name = MODEL_REGISTRY.get("reasoning", "deepseek-r1:1.5b")
    instructions = current_task.get("instructions", "")
    feedback = current_task.get("feedback", "")
    
    # 1. Deterministic Execution Phase
    inspection_data = state.get("inspection_data") or {}
    params = inspection_data.get("extracted_parameters", {})
    calc_data = state.get("calculation_data") or {}
    
    compliance_results = {}
    
    if params:
        try:
            # Tool 1: RBI Interval
            asme_res = calc_data.get("asme_ug27", {})
            rem_life = float(asme_res.get("remaining_life_years", 10.0))
            pressure = float(params.get("design_pressure_mpa", 1.0))
            toxicity = str(params.get("fluid_toxicity", "Low"))
            
            rbi_res = calculate_rbi_interval(rem_life, pressure, toxicity)
            compliance_results["rbi_assessment"] = rbi_res
            
            # Tool 2: Compliance Auditor
            equip_id = str(params.get("equipment_id", "VESSEL-UNKNOWN"))
            cost = float(params.get("estimated_cost_lakhs", 10.0))
            is_emerg = asme_res.get("is_breach", False)
            
            audit_res = audit_procurement_compliance(
                equipment_id=equip_id,
                estimated_cost_lakhs=cost,
                is_emergency=is_emerg,
                is_single_source=True,
                has_pac=bool(params.get("pac_certificate_ref")),
                pac_certificate_ref=params.get("pac_certificate_ref"),
                emergency_justification_ref="INC-AUTO-GEN" if is_emerg else None
            )
            compliance_results["cvc_audit"] = audit_res
            
            state["compliance_data"] = compliance_results
        except Exception as e:
            compliance_results = {"error": str(e)}
            logger.error(f"[ReasoningAgent] Deterministic execution failed: {e}")

    # 2. RAG Context Gathering
    rag_context = ""
    try:
        if rag_tool:
            rag_context = rag_tool.invoke("CVC Circular 02/02/2004 compliance")
    except Exception as e:
        logger.warning(f"RAG failed in ReasoningAgent: {e}")

    # 3. LLM Summarization Phase
    prompt = (
        f"Task: {instructions}\n"
        f"Feedback: {feedback}\n"
        f"Deterministic Compliance Results: {compliance_results}\n"
        f"RAG Context: {rag_context}\n"
        "Provide a detailed, factual logical deduction based strictly on the provided compliance results."
    )
    try:
        output = base_agent.call_ollama(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a strict compliance auditor. Do not hallucinate safety or legal justifications."
        )
    except Exception as e:
        output = f"Error calling LLM: {e}"
        
    current_task["output"] = output
    state["current_task"] = current_task
    state["next_node"] = "supervisor"
    return state
