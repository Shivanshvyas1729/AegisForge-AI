#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import sys
sys.path.append(os.path.abspath('..'))
import json
import hashlib
from typing import Literal, TypedDict, List, Annotated
import operator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt



# In[2]:


# ==========================================
# 1. IMPORT ALL TOOL MODULES FROM YOUR IMAGE


# In[3]:


# ==========================================
from tools import (
    api_579_ffs_tool,
    asme_calculator,
    audit_trail,
    compliance_auditor,
    doc_generator,
    docker_sandbox,
    file_io,
    inspection_extractor_tool,
    material_lookup_tool,
    network_verifier,
    risk_based_inspection_tool,
    routing_guard,
    thickness_grid_analyzer,
)



# In[4]:


# ==========================================
# 2. DEFINE SYSTEM STATE


# In[5]:


# ==========================================
class AgentState(MessagesState):
    retry_count: int
    max_retries: int
    human_approved: bool
    human_feedback: str



# In[6]:


# ==========================================
# 3. INITIALIZE OLLAMA LOCAL MODELS


# In[7]:


# ==========================================
# Make sure these models are pulled locally in Ollama prior to execution:
#   ollama pull qwen2.5:3b
#   ollama pull qwen2.5-coder:1.5b
#   ollama pull deepseek-r1:1.5b
#   ollama pull llama3.2-vision (or similar local vision model)
#   ollama pull llama3.2:3b

supervisor_llm = ChatOllama(model="llama3.1:8b", temperature=0)
coder_llm = ChatOllama(model="llama3.1:8b", temperature=0)
reasoning_llm = ChatOllama(model="deepseek-r1:8b", temperature=0)
vision_llm = ChatOllama(model="moondream:latest", temperature=0)
reviewer_llm = ChatOllama(model="llama3.2:3b", temperature=0)



# In[8]:


# ==========================================
# 4. ASSIGN TOOLS TO SPECIALIZED AGENTS


# In[9]:


# ==========================================
# Vision Agent Tools
vision_tools = [
    inspection_extractor_tool.extract_inspection_data,
    thickness_grid_analyzer.analyze_thickness_grid,
    file_io.read_scanned_pdf,
]

# Coder Agent Tools
coder_tools = [
    asme_calculator.calculate_asme_stresses,
    api_579_ffs_tool.run_ffs_assessment,
    material_lookup_tool.lookup_material,
    docker_sandbox.execute_in_sandbox,
]

# Reasoning / Compliance Agent Tools
reasoning_tools = [
    compliance_auditor.audit_cvc_compliance,
    risk_based_inspection_tool.calculate_rbi_score,
    routing_guard.verify_routing_policy,
]

# Publisher Agent Tools
publisher_tools = [
    doc_generator.generate_nfa_documents,
    audit_trail.write_sha256_audit_seal,
    network_verifier.verify_zero_egress,
]



# In[10]:


# ==========================================
# 5. AGENT HELPER / WORKER AGENTS


# In[11]:


# ==========================================
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
    import re
    import json
    system_prompt = (
        "You are the Chief Supervisor Agent coordinating an engineering dossier processing system.
"
        "Analyze the context and route tasks to one of these agents:
"
        "- 'vision_agent': for extracted parameters, drawings, or scanned PDFs.
"
        "- 'coder_agent': for ASME math, calculations, material lookups, or sandbox runs.
"
        "- 'reasoning_agent': for compliance audits or RBI assessments.
"
        "- 'chief_reviewer': if all required extractions, calculations, and compliance steps are complete.
"
        "Respond with ONLY JSON format: {\"next\": \"<agent_name>\", \"instruction\": \"<task>\"}
"
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



# In[12]:


# ==========================================
# 6. CONSTRUCT STATE GRAPH


# In[13]:


# ==========================================
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



# In[14]:


# ==========================================
# 7. EXECUTION EXAMPLE


# In[15]:


# ==========================================
if __name__ == "__main__":
    initial_input = {
        "messages": [
            HumanMessage(
                content="Process dossier at data/test_dossiers/ID-9982_UT_Scan.pdf. Extract thickness grid, run ASME Section VIII Div 1 calculations, check CVC compliance, and publish signed NFA."
            )
        ],
        "retry_count": 0,
        "max_retries": 3,
        "human_approved": False,
        "human_feedback": ""
    }

    # Stream execution through Ollama LLM nodes
    for chunk in app.stream(initial_input, stream_mode="values"):
        latest_msg = chunk["messages"][-1]
        print(f"[{getattr(latest_msg, 'name', 'System')}]: {latest_msg.content}\n")


# In[16]:


if __name__ == "__main__":
    initial_input = {
        "messages": [
            HumanMessage(
                content="I need you to write a Python script that calculates the volume of a cylindrical vessel with a radius of 1200mm and a height of 5000mm. Execute this script in the secure sandbox and give me the result."
            )
        ],
        "retry_count": 0,
        "max_retries": 3,
        "human_approved": False,
        "human_feedback": ""
    }

    # Stream execution through Ollama LLM nodes
    for chunk in app.stream(initial_input, stream_mode="values"):
        latest_msg = chunk["messages"][-1]
        print(f"[{getattr(latest_msg, 'name', 'System')}]: {latest_msg.content}\n")


# In[17]:


if __name__ == "__main__":
    initial_input = {
        "messages": [
            HumanMessage(
                content="""I need you to write a Python script that creates a custom Word Document (.docx) summarizing the health of a pressure vessel. Use the `python-docx` library.

The document should contain:
1. A heading: 'Agentic AI Custom Summary Report'
2. A small table with mock metrics (e.g., Corrosion Pits Found: 42, Remaining Life: 5 Years).

Because you are running in a secure, air-gapped Docker sandbox, YOU MUST NOT SAVE THE FILE TO DISK. 
Instead, you must:
1. Save the document to an in-memory `io.BytesIO` buffer.
2. Encode the buffer to base64.
3. Print the base64 string exactly wrapped inside <<<<FILE_START>>>> and <<<<FILE_END>>>> tags so the host system can extract it.

Execute this script in the secure sandbox."""
            )
        ],
        "retry_count": 0,
        "max_retries": 3,
        "human_approved": False,
        "human_feedback": ""
    }

    # Stream execution through Ollama LLM nodes
    for chunk in app.stream(initial_input, stream_mode="values"):
        latest_msg = chunk["messages"][-1]
        print(f"[{getattr(latest_msg, 'name', 'System')}]: {latest_msg.content}\n")


# # ---------------------------------------------------------
# # Direct Tool Testing Sandbox (LLM Driven)
# # ---------------------------------------------------------

# ### LLM Tool Call Test: ASME Calculator

# In[18]:


from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from tools.asme_calculator import calculate_asme_stresses

print('Testing LLM tool execution for ASME Calculator...')
llm = ChatOllama(model="llama3.1:8b", temperature=0)
llm_with_tools = llm.bind_tools([calculate_asme_stresses])

msg = HumanMessage(content="Calculate the ASME Section VIII minimum thickness for equipment TEST-1 with design pressure 1.5 MPa, radius 1200mm, allowable stress 137.9 MPa, joint efficiency 1.0, CA 3.0mm, measured thickness 16.5mm, and corrosion rate 0.15mm/yr.")
result = llm_with_tools.invoke([msg])

if result.tool_calls:
    print(f"✅ Success! LLM generated tool call: {result.tool_calls[0]['name']}")
    print(f"Arguments: {result.tool_calls[0]['args']}")

    print("\n--- Executing Tool with LLM Arguments ---")
    tool_args = result.tool_calls[0]['args']
    execution_result = calculate_asme_stresses.invoke(tool_args)
    print(f"Tool Output: {execution_result}")
else:
    print(f"❌ Failed! LLM generated text instead: {result.content}")


# ### LLM Tool Call Test: Docker Sandbox

# In[19]:


from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from tools.docker_sandbox import execute_in_sandbox

print('Testing LLM tool execution for Docker Sandbox...')
llm = ChatOllama(model="llama3.1:8b", temperature=0)
llm_with_tools = llm.bind_tools([execute_in_sandbox])

msg = HumanMessage(content="Write a python script that prints 'Hello Sandbox' and execute it in the secure sandbox.")
result = llm_with_tools.invoke([msg])

if result.tool_calls:
    print(f"✅ Success! LLM generated tool call: {result.tool_calls[0]['name']}")
    print(f"Arguments: {result.tool_calls[0]['args']}")

    print("\n--- Executing Tool with LLM Arguments ---")
    tool_args = result.tool_calls[0]['args']
    execution_result = execute_in_sandbox.invoke(tool_args)
    print(f"Tool Output: {execution_result}")
else:
    print(f"❌ Failed! LLM generated text instead: {result.content}")


# ### LLM Tool Call Test: API 579 FFS

# In[20]:


from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from tools.api_579_ffs_tool import run_ffs_assessment

print('Testing LLM tool execution for API 579 FFS Tool...')
llm = ChatOllama(model="llama3.1:8b", temperature=0)
llm_with_tools = llm.bind_tools([run_ffs_assessment])

msg = HumanMessage(content="Run an API 579 FFS Assessment for a vessel with global actual thickness 16.5mm, LTA min thickness 12.0mm, required thickness 16.0mm, flaw length 100mm, inside radius 1200mm, and allowable RSF 0.90.")
result = llm_with_tools.invoke([msg])

if result.tool_calls:
    print(f"✅ Success! LLM generated tool call: {result.tool_calls[0]['name']}")
    print(f"Arguments: {result.tool_calls[0]['args']}")

    print("\n--- Executing Tool with LLM Arguments ---")
    tool_args = result.tool_calls[0]['args']
    execution_result = run_ffs_assessment.invoke(tool_args)
    print(f"Tool Output: {execution_result}")
else:
    print(f"❌ Failed! LLM generated text instead: {result.content}")


# ### LLM Tool Call Test: Compliance Auditor

# In[21]:


from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from tools.compliance_auditor import audit_cvc_compliance

print('Testing LLM tool execution for Compliance Auditor...')
llm = ChatOllama(model="llama3.1:8b", temperature=0)
llm_with_tools = llm.bind_tools([audit_cvc_compliance])

msg = HumanMessage(content="Audit CVC compliance for procurement request REQ-123. It is a single source procurement for 500000 INR. It has no PAC but it is an emergency, justified by 'CVC Circular 02/02/2004 Emergency Exception', approved by the Director.")
result = llm_with_tools.invoke([msg])

if result.tool_calls:
    print(f"✅ Success! LLM generated tool call: {result.tool_calls[0]['name']}")
    print(f"Arguments: {result.tool_calls[0]['args']}")

    print("\n--- Executing Tool with LLM Arguments ---")
    tool_args = result.tool_calls[0]['args']
    execution_result = audit_cvc_compliance.invoke(tool_args)
    print(f"Tool Output: {execution_result}")
else:
    print(f"❌ Failed! LLM generated text instead: {result.content}")


# ## 🛡️ Audit Ledger Dashboard
# Run the cell below to securely query the cryptographic audit ledger and view the latest tool executions, inputs, and errors across all agents.

# In[24]:


import sqlite3
import pandas as pd
import os

# Find the DB depending on which folder the notebook is in
db_path = '../data/audit/audit_ledger.db'
if not os.path.exists(db_path):
    db_path = 'data/audit/audit_ledger.db'

def show_audit_ledger():
    try:
        conn = sqlite3.connect(db_path)
        # Removed the 'LIMIT 15' from the SQL query to get all rows
        df = pd.read_sql_query("SELECT id, timestamp, workflow_id, tool_name, caller, status FROM audit_chain ORDER BY id DESC", conn)
        conn.close()

        # Tell pandas to display all rows without truncating
        pd.set_option('display.max_rows', None)

        # Style the dataframe for the notebook
        def color_status(val):
            color = 'red' if 'ERROR' in str(val) or 'FAILED' in str(val) or 'BLOCKED' in str(val) else 'green'
            return f'color: {color}; font-weight: bold'

        display(df.style.map(color_status, subset=['status']))

        # Reset the pandas option back to default if you don't want it affecting other cells
        pd.reset_option('display.max_rows')

    except Exception as e:
        print(f"Ledger not found or empty: {e}")

show_audit_ledger()

