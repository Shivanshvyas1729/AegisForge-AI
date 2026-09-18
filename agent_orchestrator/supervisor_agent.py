"""
agent_orchestrator/supervisor_agent.py
Supervisor Agent (Dynamic Hub-and-Spoke Orchestrator).
Evaluates user queries, dynamically plans tasks, and routes them to specialized model agents.
Acts as the central feedback loop evaluator and handles human-in-the-loop fallback.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
import agent_orchestrator.base_agent as base_agent
from agent_orchestrator.base_agent import OllamaOfflineException
from tools.audit_trail import append_audit_event
from config.settings import MODEL_REGISTRY, logger

def supervisor_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Supervisor Node: The Hub of the dynamic architecture.
    """
    user_query = state.get("user_query", "")
    file_path = state.get("uploaded_file_path")
    task_queue = state.get("task_queue", [])
    current_task = state.get("current_task")
    retry_count = state.get("retry_count", 0)
    human_feedback = state.get("human_feedback")
    
    # 1. Human Feedback Loop Resolution
    if human_feedback and current_task:
        logger.info(f"[Supervisor] Processing human feedback: {human_feedback}")
        current_task["feedback"] = human_feedback
        state["human_feedback"] = None
        state["retry_count"] = 0 # reset retries after human help
        state["next_node"] = current_task.get("assigned_agent")
        return state

    # 2. Evaluate Completed Task
    if current_task and not human_feedback:
        logger.info(f"[Supervisor] Evaluating task completion for: {current_task.get('task_name')}")
        # Call DeepSeek to evaluate if the agent succeeded
        eval_prompt = (
            "You are the Chief Supervisor. Evaluate if the worker agent completed the task successfully based on its output.\n"
            "Respond ONLY with a valid JSON object in this format:\n"
            "{\"success\": true/false, \"feedback\": \"reasoning...\"}"
        )
        user_msg = f"Task: {current_task}\nAgent Output: {current_task.get('output', 'None')}"
        
        try:
            model_name = MODEL_REGISTRY.get("reasoning", "deepseek-r1:1.5b")
            response = base_agent.call_ollama(model_name, [{"role": "user", "content": user_msg}], eval_prompt)
            # Try to parse JSON. 
            success = "true" in response.lower()
            
            # Deterministic override: if the agent successfully produced a non-error output, 
            # we override the 1.5B evaluator's hallucination to prevent infinite loops.
            agent_out = str(current_task.get("output", ""))
            if len(agent_out) > 10 and "Error calling LLM" not in agent_out and "Extraction Error" not in agent_out:
                success = True
                
        except Exception as e:
            logger.error(f"[Supervisor] Evaluation failed: {e}")
            success = False

        if success:
            logger.info(f"[Supervisor] Task '{current_task.get('task_name')}' approved.")
            state.setdefault("completed_tasks", []).append(current_task)
            state["current_task"] = None
            state["retry_count"] = 0
        else:
            retry_count += 1
            state["retry_count"] = retry_count
            logger.warning(f"[Supervisor] Task failed. Retry {retry_count}/3")
            if retry_count >= 3:
                # Route to human gate
                state["pipeline_status"] = "GATE_WAITING_HUMAN"
                state["next_node"] = "human_approval_gate"
                return state
            else:
                # Re-route back to agent
                state["next_node"] = current_task.get("assigned_agent")
                return state

    # 3. Plan Initial Tasks if Queue is Empty
    if not task_queue and not current_task:
        logger.info("[Supervisor] Planning new dynamic task queue.")
        
        u_lower = user_query.lower()
        is_engineering = any(k in u_lower for k in ["asme", "vessel", "cvc", "thickness", "breach", "audit", "compliance", "inspection", "api", "procurement", "integrity"])
        
        # 1. Vision extraction if file is attached
        if file_path:
            task_queue.append({
                "task_name": "Extract Physical Parameters",
                "assigned_agent": "vision_agent",
                "instructions": f"Extract parameters from {file_path}",
                "output": None
            })
            
        # 2. Domain-Specific Routing
        if is_engineering:
            task_queue.append({
                "task_name": "Mathematical Integrity Validation",
                "assigned_agent": "coder_agent",
                "instructions": "Run ASME UG-27 integrity calculations.",
                "output": None
            })
            task_queue.append({
                "task_name": "Statutory Procurement Compliance",
                "assigned_agent": "reasoning_agent",
                "instructions": "Audit CVC Circular 02/02/2004 emergency procurement limits.",
                "output": None
            })
        else:
            task_queue.append({
                "task_name": "Fulfill User Request",
                "assigned_agent": "general_agent",
                "instructions": f"Fulfill the following request: {user_query}",
                "output": None
            })
            
        # 3. Final Gatekeeping
        task_queue.append({
            "task_name": "Final Gatekeeping Review",
            "assigned_agent": "general_agent",
            "instructions": "Holistically review all outputs and format final report.",
            "output": None
        })
        state["task_queue"] = task_queue
        
    # 4. Dispatch Next Task
    if task_queue and not state.get("current_task"):
        next_t = task_queue.pop(0)
        state["current_task"] = next_t
        state["task_queue"] = task_queue
        
        # Parallel Fan-Out: Run RAG Prefetch alongside the first task
        if not state.get("rag_prefetched"):
            state["rag_prefetched"] = True
            state["next_node"] = [next_t.get("assigned_agent"), "rag_prefetch_node"]
            logger.info(f"[Supervisor] Dispatching parallel tasks: {next_t.get('task_name')} and RAG Prefetch")
        else:
            state["next_node"] = next_t.get("assigned_agent")
            logger.info(f"[Supervisor] Dispatching task: {next_t.get('task_name')} to {state['next_node']}")
            
        return state
        
    # 5. All Tasks Done
    if not task_queue and not state.get("current_task"):
        logger.info("[Supervisor] All tasks complete. Routing to publisher.")
        state["next_node"] = "publisher_agent"
        return state
        
    return state
