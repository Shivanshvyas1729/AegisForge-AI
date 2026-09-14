from langchain_core.tools import tool


@tool
def sandbox(code: str) -> str:
    """
    Execute code in a secure sandbox.
    """
    return "Sandbox execution result"
