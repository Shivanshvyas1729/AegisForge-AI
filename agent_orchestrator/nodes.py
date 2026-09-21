import sys
import os
import json
import re
from typing import Literal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt
from langgraph.graph import END

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import (
    supervisor_llm,
    coder_llm,
    reasoning_llm,
    vision_llm,
    reviewer_llm
)
from agent_orchestrator.tools_config import (
    vision_tools,
    coder_tools,
    reasoning_tools,
    publisher_tools
)

def get_next_node(last_message: BaseMessage, default_goto: str, state: AgentState) -> str:
    """Helper to detect retry thresholds or completion triggers."""
    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        return "human_approval_gate"
    if "FINAL ANSWER" in last_message.content or "COMPLETED" in last_message.content:
        return "chief_reviewer"
    return default_goto

# Vision Worker Agent
vision_agent = create_react_agent(
    vision_llm,
    tools=vision_tools,
    prompt="You are a Vision & Extraction Agent. Extract parameters from scanned PDFs, inspection sheets, and thickness grids."
)

def vision_node(state: AgentState) -> Command[Literal["supervisor", "human_approval_gate"]]:
    result = vision_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "supervisor", state)
    result["messages"][-1] = HumanMessage(content=result["messages"][-1].content, name="vision_agent")
    return Command(update={"messages": result["messages"]}, goto=goto)

# Coder Worker Agent
coder_agent = create_react_agent(
    coder_llm,
    tools=coder_tools,
    prompt="You are a Senior Coder Agent. When using execute_in_sandbox, provide ONLY the python code as the code_string argument."
)

def coder_node(state: AgentState) -> Command[Literal["supervisor", "human_approval_gate"]]:
    result = coder_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "supervisor", state)
    result["messages"][-1] = HumanMessage(content=result["messages"][-1].content, name="coder_agent")
    return Command(update={"messages": result["messages"]}, goto=goto)

# Reasoning Worker Agent
reasoning_agent = create_react_agent(
    reasoning_llm,
    tools=reasoning_tools,
    prompt="You are a Compliance & Reasoning Agent. Perform CVC audits, RBI scores, and compliance evaluations."
)

def reasoning_node(state: AgentState) -> Command[Literal["supervisor", "human_approval_gate"]]:
    result = reasoning_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "supervisor", state)
    result["messages"][-1] = HumanMessage(content=result["messages"][-1].content, name="reasoning_agent")
    return Command(update={"messages": result["messages"]}, goto=goto)

# Supervisor Agent
def supervisor_node(state: AgentState) -> Command[Literal["vision_agent", "coder_agent", "reasoning_agent", "chief_reviewer", "human_approval_gate"]]:
    system_prompt = (
        "You are the Chief Supervisor Agent coordinating an engineering dossier processing system.\n"
        "Analyze the context and route tasks to one of these agents:\n"
        "- 'vision_agent': for extracted parameters, drawings, or scanned PDFs.\n"
        "- 'coder_agent': for ASME math, calculations, material lookups, or sandbox runs.\n"
        "- 'reasoning_agent': for compliance audits or RBI assessments.\n"
        "- 'chief_reviewer': if all required extractions, calculations, and compliance steps are complete.\n"
        "Respond with ONLY JSON format: {\"next\": \"<agent_name>\", \"instruction\": \"<task>\"}\n"
        "Do not include any other conversational text or markdown blocks."
    )
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = supervisor_llm.invoke(messages)

    try:
        # Use regex to find the first JSON object in the response
        match = re.search(r'\{.*?\}', response.content, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            next_target = parsed.get("next", "chief_reviewer")
        else:
            # Fallback if no {} found
            parsed = json.loads(response.content)
            next_target = parsed.get("next", "chief_reviewer")
    except Exception as e:
        print(f"Failed to parse Supervisor JSON: {e}")
        next_target = "chief_reviewer"

    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        next_target = "human_approval_gate"

    return Command(
        update={"messages": [HumanMessage(content=response.content, name="supervisor")]},
        goto=next_target
    )

# Human Approval Gate Node
def human_approval_gate(state: AgentState) -> Command[Literal["supervisor", "chief_reviewer"]]:
    # Interrupt execution and wait for human engineer sign-off
    user_input = interrupt({
        "message": "CRITICAL: Max retries exceeded or safety flag raised. Human engineer sign-off required.",
        "status": "Awaiting Sign-off"
    })

    approved = user_input.get("approved", False)
    feedback = user_input.get("feedback", "")

    if approved:
        return Command(
            update={
                "human_approved": True,
                "human_feedback": feedback,
                "retry_count": 0,
                "messages": [HumanMessage(content=f"Human Engineer Approved: {feedback}", name="HumanGate")]
            },
            goto="chief_reviewer"
        )
    else:
        return Command(
            update={
                "human_approved": False,
                "human_feedback": feedback,
                "retry_count": 0,
                "messages": [HumanMessage(content=f"Human Engineer Rejected/Re-routed: {feedback}", name="HumanGate")]
            },
            goto="supervisor"
        )

# Chief Reviewer Agent
chief_reviewer_agent = create_react_agent(
    reviewer_llm,
    tools=[],
    prompt="You are the Chief Reviewer. Perform final safety, compliance, and sanity checks on all worker agent outputs."
)

def chief_reviewer_node(state: AgentState) -> Command[Literal["deliverable_publisher"]]:
    result = chief_reviewer_agent.invoke(state)
    result["messages"][-1] = HumanMessage(content=result["messages"][-1].content, name="chief_reviewer")
    return Command(
        update={"messages": result["messages"]},
        goto="deliverable_publisher"
    )

# Deliverable Publisher Agent
publisher_agent = create_react_agent(
    supervisor_llm,
    tools=publisher_tools,
    prompt="You are the Deliverable Publisher. Compile outputs into Word/PDF documents and apply the SHA-256 audit seal."
)

def deliverable_publisher_node(state: AgentState) -> Command[Literal[END]]:
    result = publisher_agent.invoke(state)
    return Command(
        update={"messages": result["messages"]},
        goto=END
    )
