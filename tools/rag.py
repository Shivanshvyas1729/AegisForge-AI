from langchain_core.tools import tool


@tool
def rag(query: str) -> str:
    """
    Search the local knowledge base and return relevant information.
    """
    return f"Relevant knowledge for: {query}"
