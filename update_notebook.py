import json
import re

notebook_path = 'c:/Users/DELL/Desktop/SIH/agent_orchestrator/agents.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

new_supervisor_code = '''# Supervisor Agent
def supervisor_node(state: AgentState) -> Command[Literal["vision_agent", "coder_agent", "reasoning_agent", "chief_reviewer", "human_approval_gate"]]:
    import re
    import json
    system_prompt = (
        "You are the Chief Supervisor Agent coordinating an engineering dossier processing system.\\n"
        "Analyze the context and route tasks to one of these agents:\\n"
        "- 'vision_agent': for extracted parameters, drawings, or scanned PDFs.\\n"
        "- 'coder_agent': for ASME math, calculations, material lookups, or sandbox runs.\\n"
        "- 'reasoning_agent': for compliance audits or RBI assessments.\\n"
        "- 'chief_reviewer': if all required extractions, calculations, and compliance steps are complete.\\n"
        "Respond with ONLY JSON format: {\\\"next\\\": \\\"<agent_name>\\\", \\\"instruction\\\": \\\"<task>\\\"}\\n"
        "Do not include any other conversational text or markdown blocks."
    )
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = supervisor_llm.invoke(messages)
    
    try:
        # Use regex to find the first JSON object in the response
        match = re.search(r'\\{.*?\\}', response.content, re.DOTALL)
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

'''

for cell in nb.get('cells', []):
    if cell['cell_type'] == 'code':
        source = cell['source']
        source_str = ''.join(source)
        if 'def supervisor_node' in source_str:
            pattern = re.compile(r'# Supervisor Agent.*?# Human Approval Gate Node', re.DOTALL)
            replacement = new_supervisor_code + '# Human Approval Gate Node'
            new_source_str = re.sub(pattern, replacement, source_str)
            
            lines = new_source_str.splitlines(True)
            cell['source'] = lines
            print('Successfully updated supervisor_node in the notebook.')
            break

with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
