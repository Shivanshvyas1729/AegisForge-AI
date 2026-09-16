"""
tools/sandbox.py
Air-Gapped Sovereign Python Code Execution Sandbox.
Executes mathematical and data-transformation scripts in an isolated subprocess
with strict AST import allowlisting, watchdog memory limits (512 MB),
and hard timeout protection (10 seconds).
"""

import ast
import os
import sys
import time
import psutil
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event

SCRATCH_DIR = PROJECT_ROOT / "data" / "scratch"
MAX_MEMORY_BYTES = 512 * 1024 * 1024  # 512 MB
DEFAULT_TIMEOUT_SECONDS = 10
MAX_OUTPUT_CHARS = 8000

# Strict AST Import Whitelist — ONLY computational & parsing standard modules allowed
ALLOWED_MODULES = {
    "math",
    "statistics",
    "json",
    "re",
    "datetime",
    "decimal",
    "fractions",
    "itertools",
    "csv",
    "collections",
    "random",
}

# Forbidden builtin function calls
FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "__import__",
    "open",
    "compile",
    "type",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
    "input",
    "globals",
    "locals",
}


class SandboxSecurityError(Exception):
    """Raised when submitted code violates sovereign sandbox security policies."""
    pass


def validate_code_ast(code: str) -> None:
    """
    Parses Python code into an Abstract Syntax Tree (AST) and verifies:
    1. Only approved computational modules are imported (strict allowlist).
    2. No access to private or dunder attributes (e.g. __class__, __subclasses__, __bases__).
    3. No invocation of dangerous builtins (eval, exec, type, getattr, open, compile, etc.).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxSecurityError(f"Syntax error in submitted code: {e}")

    for node in ast.walk(tree):
        # 1. Check module imports (import X)
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_root = alias.name.split('.')[0]
                if mod_root not in ALLOWED_MODULES:
                    raise SandboxSecurityError(
                        f"Access denied: Module '{alias.name}' is not in the sovereign sandbox allowlist. "
                        f"Permitted modules: {sorted(list(ALLOWED_MODULES))}"
                    )

        # 2. Check from X import Y
        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                raise SandboxSecurityError("Relative imports are forbidden in the sandbox.")
            mod_root = node.module.split('.')[0]
            if mod_root not in ALLOWED_MODULES:
                raise SandboxSecurityError(
                    f"Access denied: Module '{node.module}' is not in the sovereign sandbox allowlist. "
                    f"Permitted modules: {sorted(list(ALLOWED_MODULES))}"
                )

        # 3. Check attribute accesses (blocks _* and dunders like __subclasses__, __bases__, __globals__)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith('_'):
                raise SandboxSecurityError(
                    f"Access denied: Access to private or dunder attribute '{node.attr}' is strictly prohibited."
                )

        # 4. Check forbidden builtin function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    raise SandboxSecurityError(
                        f"Access denied: Invocation of forbidden function '{node.func.id}' is strictly prohibited."
                    )


def execute_python_code(
    code: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_memory_bytes: int = MAX_MEMORY_BYTES
) -> Dict[str, Any]:
    """
    Executes Python code in an isolated subprocess with watchdog monitoring
    for memory usage (512 MB ceiling) and execution timeout (10 seconds).
    """
    start_time = time.time()

    # Step 1: Pre-execution AST verification
    try:
        validate_code_ast(code)
    except SandboxSecurityError as sec_err:
        duration_ms = (time.time() - start_time) * 1000
        append_audit_event(
            tool_name="sandbox_tool",
            inputs={"code": code[:200]},
            outputs={"error": str(sec_err)},
            status="SECURITY_REJECTED",
            duration_ms=duration_ms,
            caller="sandbox_tool"
        )
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"SandboxSecurityError: {str(sec_err)}",
        }

    # Step 2: Prepare isolated scratch workspace
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.py',
        dir=str(SCRATCH_DIR),
        delete=False,
        encoding='utf-8'
    )
    temp_file.write(code)
    temp_file.close()
    temp_path = Path(temp_file.name)

    # Clean environment variables
    clean_env = {
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }

    proc: Optional[subprocess.Popen] = None
    memory_exceeded = False
    timed_out = False

    try:
        proc = subprocess.Popen(
            [sys.executable, str(temp_path)],
            cwd=str(SCRATCH_DIR),
            env=clean_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Watchdog monitor thread for memory and timeout
        def monitor_process():
            nonlocal memory_exceeded, timed_out
            start_mon = time.time()
            try:
                p = psutil.Process(proc.pid)
                while proc.poll() is None:
                    elapsed = time.time() - start_mon
                    if elapsed > timeout_seconds:
                        timed_out = True
                        proc.kill()
                        break

                    try:
                        mem_info = p.memory_info()
                        if mem_info.rss > max_memory_bytes:
                            memory_exceeded = True
                            proc.kill()
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break

                    time.sleep(0.05)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        monitor_thread = threading.Thread(target=monitor_process, daemon=True)
        monitor_thread.start()

        stdout_data, stderr_data = proc.communicate()
        monitor_thread.join(timeout=1.0)
        duration_ms = (time.time() - start_time) * 1000

        if memory_exceeded:
            err_msg = f"ResourceLimitExceeded: Process exceeded memory limit of {max_memory_bytes // (1024 * 1024)} MB."
            append_audit_event("sandbox_tool", {"code": code[:200]}, {"error": err_msg}, "MEMORY_EXCEEDED", duration_ms)
            return {"success": False, "returncode": -1, "stdout": "", "stderr": err_msg}

        if timed_out:
            err_msg = f"TimeoutExpired: Process exceeded execution timeout of {timeout_seconds} seconds."
            append_audit_event("sandbox_tool", {"code": code[:200]}, {"error": err_msg}, "TIMEOUT", duration_ms)
            return {"success": False, "returncode": -1, "stdout": "", "stderr": err_msg}

        # Truncate output to prevent buffer denial of service
        trunc_stdout = stdout_data[:MAX_OUTPUT_CHARS]
        trunc_stderr = stderr_data[:MAX_OUTPUT_CHARS]

        status = "SUCCESS" if proc.returncode == 0 else "EXECUTION_ERROR"
        append_audit_event(
            tool_name="sandbox_tool",
            inputs={"code": code[:200]},
            outputs={"returncode": proc.returncode, "stdout_len": len(trunc_stdout)},
            status=status,
            duration_ms=duration_ms
        )

        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": trunc_stdout,
            "stderr": trunc_stderr,
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        append_audit_event("sandbox_tool", {"code": code[:200]}, {"error": str(e)}, "FAILURE", duration_ms)
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(e)}

    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


try:
    from langchain_core.tools import tool

    @tool
    def sandbox_tool(code: str) -> str:
        """
        Executes Python code in an isolated subprocess sandbox with strict AST import
        allowlisting, memory ceiling (512 MB), and execution timeout (10 seconds).
        Allowed modules: math, statistics, json, re, datetime, decimal, fractions, itertools, csv, collections, random.
        """
        res = execute_python_code(code)
        if res["success"]:
            return res["stdout"] if res["stdout"] else "Execution succeeded with no standard output."
        return f"Sandbox Error (Return code {res['returncode']}):\n{res['stderr']}"

except ImportError:
    sandbox_tool = None
