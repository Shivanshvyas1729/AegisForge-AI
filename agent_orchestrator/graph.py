"""
AegisForge-AI — LangGraph Workflow Assembly
=============================================
Assembles all nodes into the compiled StateGraph application.
Import `app` from here for all invocations.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent_orchestrator.state import AgentState

# Import all nodes
from agent_orchestrator.nodes.router     import route_question, direct_answer_node, human_approval_gate
from agent_orchestrator.nodes.supervisor import supervisor_node
from agent_orchestrator.nodes.vision     import vision_node
from agent_orchestrator.nodes.coder      import coder_node
from agent_orchestrator.nodes.reasoning  import reasoning_node
from agent_orchestrator.nodes.reviewer   import chief_reviewer_node
from agent_orchestrator.nodes.publisher  import deliverable_publisher_node

# ============================================================================
# GRAPH DEFINITION
# ============================================================================
workflow = StateGraph(AgentState)

# Add all nodes
workflow.add_node("direct_answer",        direct_answer_node)
workflow.add_node("supervisor",           supervisor_node)
workflow.add_node("vision_agent",         vision_node)
workflow.add_node("coder_agent",          coder_node)
workflow.add_node("reasoning_agent",      reasoning_node)
workflow.add_node("human_approval_gate",  human_approval_gate)
workflow.add_node("chief_reviewer",       chief_reviewer_node)
workflow.add_node("deliverable_publisher", deliverable_publisher_node)

# Conditional entry routing
workflow.add_conditional_edges(START, route_question, {
    "direct_answer": "direct_answer",
    "supervisor":    "supervisor",
})
workflow.add_edge("direct_answer", END)

# Compile with persistent in-memory checkpointer
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
