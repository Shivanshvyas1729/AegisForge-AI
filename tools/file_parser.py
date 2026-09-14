from langchain_core.tools import tool


@tool
def file_parser(file_path: str) -> str:
    """
    Parse a file and extract its text/content.
    """
    return f"Parsed content from {file_path}"
