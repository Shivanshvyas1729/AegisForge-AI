from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from tools.docker_sandbox import execute_in_sandbox

def test_model(model_name):
    print(f"\n--- Testing {model_name} ---")
    llm = ChatOllama(model=model_name, temperature=0)
    llm_with_tools = llm.bind_tools([execute_in_sandbox])

    msg = HumanMessage(content="Write a python script that prints 'hello' and execute it in the sandbox.")
    result = llm_with_tools.invoke([msg])

    if result.tool_calls:
        print(f"✅ Success! Parsed as native tool call: {result.tool_calls[0]['name']}")
    else:
        print(f"❌ Failed! Output as text instead:\n{result.content}")

test_model("llama3.1:8b")
test_model("qwen2.5-coder:7b")
