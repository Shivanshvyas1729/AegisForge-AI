import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph.graph import StateGraph, START

from agent_orchestrator.state import AgentState
from agent_orchestrator.nodes import (
    supervisor_node,
    vision_node,
    coder_node,
    reasoning_node,
    human_approval_gate,
    chief_reviewer_node,
    deliverable_publisher_node
)

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("vision_agent", vision_node)
workflow.add_node("coder_agent", coder_node)
workflow.add_node("reasoning_agent", reasoning_node)
workflow.add_node("human_approval_gate", human_approval_gate)
workflow.add_node("chief_reviewer", chief_reviewer_node)
workflow.add_node("deliverable_publisher", deliverable_publisher_node)

# Set Graph Entry Point
workflow.add_edge(START, "supervisor")

app = workflow.compile()
