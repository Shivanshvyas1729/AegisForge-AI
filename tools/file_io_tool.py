from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_project_path(relative_path: str) -> Path:
    """Resolve a user-supplied relative path and ensure it stays within the project root."""
    if not relative_path or not isinstance(relative_path, str):
        raise ValueError("relative_path must be a non-empty string")

    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("Only relative paths are allowed inside the project sandbox")

    normalized = candidate.as_posix()
    if normalized.startswith("../") or normalized == ".." or ".." in candidate.parts:
        raise ValueError("Path traversal is not allowed. Use a path inside the project sandbox workspace.")

    target = (PROJECT_ROOT / candidate).resolve()
    project_root_resolved = PROJECT_ROOT.resolve()

    try:
        target.relative_to(project_root_resolved)
    except ValueError as exc:
        raise ValueError("Path escapes the project workspace sandbox") from exc

    return target


def file_io_tool(action: str, relative_path: str, content: Optional[str] = None) -> Dict[str, Any]:
    """
    Safe file read/write tool sandboxed to the project workspace.

    Expected behavior:
    - action: "read" | "write"
    - relative_path: path relative to project root only
    - content: text content for writing
    - returns {"status": "SUCCESS" | "ERROR", "data": ..., "message": ...}
    """
    try:
        if action not in {"read", "write"}:
            return {"status": "ERROR", "message": "Unsupported action. Use 'read' or 'write'."}

        target_path = _resolve_project_path(relative_path)

        if action == "read":
            if not target_path.exists():
                return {"status": "ERROR", "message": f"File does not exist: {relative_path}"}
            if not target_path.is_file():
                return {"status": "ERROR", "message": f"Not a file: {relative_path}"}

            data = target_path.read_text(encoding="utf-8")
            return {"status": "SUCCESS", "data": data}

        if action == "write":
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content or "", encoding="utf-8")
            return {"status": "SUCCESS", "data": str(target_path), "message": "File written successfully."}

    except Exception as exc:
        return {"status": "ERROR", "message": str(exc)}

    return {"status": "ERROR", "message": "Unexpected file I/O error."}


if __name__ == "__main__":
    print(file_io_tool("write", "sample_data/file_io_tool_demo.txt", "Equipment ID: 11-V-102\nStatus: OK"))
    print(file_io_tool("read", "sample_data/file_io_tool_demo.txt"))
    print(file_io_tool("read", "../outside.txt"))
