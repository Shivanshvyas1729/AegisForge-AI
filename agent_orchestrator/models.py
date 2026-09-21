from langchain_ollama import ChatOllama

# Make sure these models are pulled locally in Ollama prior to execution:
#   ollama pull llama3.1:8b
#   ollama pull deepseek-r1:8b
#   ollama pull moondream:latest
#   ollama pull llama3.2:3b

supervisor_llm = ChatOllama(model="llama3.1:8b", temperature=0)
coder_llm = ChatOllama(model="llama3.1:8b", temperature=0)
reasoning_llm = ChatOllama(model="deepseek-r1:8b", temperature=0)
vision_llm = ChatOllama(model="moondream:latest", temperature=0)
reviewer_llm = ChatOllama(model="llama3.2:3b", temperature=0)
