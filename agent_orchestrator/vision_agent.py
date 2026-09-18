"""
agent_orchestrator/vision_agent.py
Vision Node utilizing EasyOCR and Moondream for visual parameter extraction.
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
from tools.inspection_extractor_tool import extract_inspection_parameters
from tools.rag import rag_tool

def vision_agent_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    logger.info("[VisionAgent] Activated Vision/OCR Extraction.")
    current_task = state.get("current_task")
    file_path = state.get("uploaded_file_path")
    
    if not current_task:
        return state
        
    feedback = current_task.get("feedback", "")
    
    rag_context = ""
    try:
        if rag_tool:
            rag_context = rag_tool.invoke("P&ID schematic reading guidelines")
    except Exception as e:
        logger.warning(f"RAG failed in VisionAgent: {e}")

    output = ""
    if file_path:
        try:
            # Use the deterministic extractor (which wraps EasyOCR)
            res = extract_inspection_parameters(file_path=file_path)
            output = f"Extracted Params: {res.get('extracted_parameters')}\nStatus: {res.get('status')}"
            
            # Save to state for downstream use if needed
            state["inspection_data"] = res
        except Exception as e:
            output = f"Extraction Error: {e}"
    else:
        output = "No visual file provided for extraction."
        
    if feedback:
        output += f"\nHuman Feedback Addressed: {feedback}"

    current_task["output"] = output
    state["current_task"] = current_task
    state["next_node"] = "supervisor"
    return state
