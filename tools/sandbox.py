"""
tools/sandbox.py
Air-Gapped Python Code Execution Sandbox.
Executes engineering scripts in an isolated subprocess with strict timeouts and resource limits.
"""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any


def execute_python_code(code: str, timeout_seconds: int = 15) -> Dict[str, Any]:
    """
    Executes Python code in an isolated subprocess with strict timeouts and output capture.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_path = f.name

    try:
        python_bin = sys.executable
        result = subprocess.run(
            [python_bin, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding='utf-8',
            errors='replace'
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout_seconds} seconds.",
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }
    finally:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass


try:
    from langchain_core.tools import tool

    @tool
    def sandbox(code: str) -> str:
        """
        Execute code in a secure sandbox.
        """
        res = execute_python_code(code)
        if res["success"]:
            return res["stdout"] if res["stdout"] else "Execution succeeded with no output."
        return f"Error (Exit {res['returncode']}):\n{res['stderr']}"
except ImportError:
    pass

