"""
tools/file_io.py
Secure Sovereign File I/O Engine with Path Traversal Protection.
Restricts read/write operations strictly within the project workspace directory
and prevents arbitrary filesystem escape.
"""

import os
import sys
import csv
import json
import time
from pathlib import Path
from typing import Any, Optional, Dict, Union

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event


def _validate_safe_path(file_path: str) -> Path:
    """
    Validates that the resolved file path resides strictly within the project root.
    Raises PermissionError if path traversal is detected.
    """
    raw_path = Path(file_path)
    if not raw_path.is_absolute():
        resolved_path = (PROJECT_ROOT / raw_path).resolve()
    else:
        resolved_path = raw_path.resolve()

    try:
        # Python 3.9+ is_relative_to
        if not resolved_path.is_relative_to(PROJECT_ROOT):
            raise PermissionError(
                f"Security Alert: Path traversal attempt blocked. Path '{file_path}' "
                f"resolves outside project workspace: {resolved_path}"
            )
    except AttributeError:
        # Fallback for older python
        if not str(resolved_path).startswith(str(PROJECT_ROOT)):
            raise PermissionError(
                f"Security Alert: Path traversal attempt blocked: {resolved_path}"
            )

    return resolved_path


def read_or_write_file(
    file_path: str,
    mode: str = 'r',
    data: Any = None,
    file_type: Optional[str] = None
) -> Any:
    """
    Safely reads from or writes to a file within the project workspace.
    Explicitly handles .json, .csv, and text formats without ambiguous content sniffing.
    """
    target_path = _validate_safe_path(file_path)

    if not file_type:
        ext = target_path.suffix.lower().strip('.')
        file_type = ext if ext in ('json', 'csv') else 'txt'

    if mode in ('w', 'a'):
        if data is None:
            raise ValueError("Data must be provided for write or append operations.")

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if file_type == 'json':
            # Handle structured data or JSON string
            if isinstance(data, (dict, list)):
                payload = data
            elif isinstance(data, str):
                try:
                    payload = json.loads(data)
                except Exception:
                    payload = {"content": data}
            else:
                payload = {"data": str(data)}

            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return True

        elif file_type == 'csv':
            with open(target_path, 'w' if mode == 'w' else 'a', newline='', encoding='utf-8') as f:
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
                    if mode == 'w':
                        writer.writeheader()
                    writer.writerows(data)
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    writer = csv.writer(f)
                    writer.writerows(data)
                else:
                    f.write(str(data) + "\n")
            return True

        else:
            with open(target_path, mode, encoding='utf-8') as f:
                f.write(str(data))
            return True

    elif mode in ('r', 'rb'):
        if not target_path.exists():
            raise FileNotFoundError(f"Target file does not exist: {target_path}")

        if file_type == 'json':
            with open(target_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif file_type == 'csv':
            with open(target_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        else:
            with open(target_path, 'r', encoding='utf-8') as f:
                return f.read()

    else:
        raise ValueError(f"Invalid mode '{mode}'. Supported modes are 'r', 'w', 'a'.")


try:
    from langchain_core.tools import tool

    @tool
    def file_io_tool(file_path: str, mode: str = "r", data: str = "") -> str:
        """
        Safely reads or writes text, CSV, or JSON files strictly within the project workspace.
        Enforces strict path-traversal protection against unauthorized filesystem access.
        
        Args:
            file_path: Relative or workspace path to target file (e.g. 'data/scratch/calc.json')
            mode: 'r' to read, 'w' to write, 'a' to append
            data: Content to write (for 'w' or 'a' modes)
        """
        start_time = time.time()
        try:
            if mode in ("w", "a"):
                read_or_write_file(file_path, mode=mode, data=data)
                duration_ms = (time.time() - start_time) * 1000
                append_audit_event(
                    tool_name="file_io_tool",
                    inputs={"file_path": file_path, "mode": mode, "data_len": len(data)},
                    outputs={"status": "SUCCESS"},
                    status="SUCCESS",
                    duration_ms=duration_ms,
                    caller="file_io_tool"
                )
                return f"Successfully wrote {len(data)} characters to {file_path} in mode '{mode}'."
            else:
                content = read_or_write_file(file_path, mode="r")
                duration_ms = (time.time() - start_time) * 1000
                res_str = str(content)
                append_audit_event(
                    tool_name="file_io_tool",
                    inputs={"file_path": file_path, "mode": mode},
                    outputs={"read_bytes": len(res_str)},
                    status="SUCCESS",
                    duration_ms=duration_ms,
                    caller="file_io_tool"
                )
                return res_str
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            append_audit_event(
                tool_name="file_io_tool",
                inputs={"file_path": file_path, "mode": mode},
                outputs={"error": str(e)},
                status="FAILURE",
                duration_ms=duration_ms,
                caller="file_io_tool"
            )
            return f"File I/O Error: {str(e)}"

except ImportError:
    file_io_tool = None
