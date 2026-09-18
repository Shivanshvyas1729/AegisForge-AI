"""
agent_orchestrator/rag_prefetch_agent.py
Asynchronous Parallel RAG Prefetch Node.
Executes RAG searches in the background while other agents compute math and parse vision.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
from tools.rag import rag_tool
from config.settings import logger

def rag_prefetch_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    logger.info("[RAG-Prefetch] Executing parallel asynchronous RAG search...")
    
    try:
        # We can dynamically decide what to search, but for SIH, CVC is standard.
        query = "CVC Circular 02/02/2004 compliance"
        if rag_tool:
            context = rag_tool.invoke(query)
            logger.info(f"[RAG-Prefetch] Successfully pre-fetched {len(context)} bytes of compliance data.")
            return {"rag_prefetch_context": context}
        else:
            logger.warning("[RAG-Prefetch] RAG tool is disabled or unavailable.")
    except Exception as e:
        logger.error(f"[RAG-Prefetch] Failed: {e}")
        
    return {"rag_prefetch_context": ""}
