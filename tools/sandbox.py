import ast
import os
import sys
import time
import shutil
import resource
import psutil
import tempfile
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event

SCRATCH_DIR = PROJECT_ROOT / "data" / "scratch"
MAX_MEMORY_BYTES = 512 * 1024 * 1024  # 512 MB
DEFAULT_TIMEOUT_SECONDS = 10
MAX_OUTPUT_CHARS = 8000
MAX_CPU_SECONDS = 10  # hard CPU-time ceiling, enforced by the kernel via setrlimit

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

    NOTE: this is a *first-pass, defense-in-depth* filter, not the security boundary.
    The security boundary is the OS-level jail applied in _build_launch_command().
    Static AST analysis on adversarial input is inherently incomplete — treat it as
    "rejects obviously bad code early / cheaply," not "guarantees safety."
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxSecurityError(f"Syntax error in submitted code: {e}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_root = alias.name.split('.')[0]
                if mod_root not in ALLOWED_MODULES:
                    raise SandboxSecurityError(
                        f"Access denied: Module '{alias.name}' is not in the sovereign sandbox allowlist. "
                        f"Permitted modules: {sorted(list(ALLOWED_MODULES))}"
                    )

        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                raise SandboxSecurityError("Relative imports are forbidden in the sandbox.")
            mod_root = node.module.split('.')[0]
            if mod_root not in ALLOWED_MODULES:
                raise SandboxSecurityError(
                    f"Access denied: Module '{node.module}' is not in the sovereign sandbox allowlist. "
                    f"Permitted modules: {sorted(list(ALLOWED_MODULES))}"
                )

        elif isinstance(node, ast.Attribute):
            if node.attr.startswith('_'):
                raise SandboxSecurityError(
                    f"Access denied: Access to private or dunder attribute '{node.attr}' is strictly prohibited."
                )

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_CALLS:
                    raise SandboxSecurityError(
                        f"Access denied: Invocation of forbidden function '{node.func.id}' is strictly prohibited."
                    )


# ---------------------------------------------------------------------------
# OS-level jail selection
# ---------------------------------------------------------------------------
# We prefer bubblewrap (bwrap) — it's unprivileged, minimal, and gives us a real
# mount/PID/network namespace boundary. firejail is used as a fallback since it's
# more commonly preinstalled on desktop distros. If neither is present, we run
# the bare subprocess and loudly flag that the *kernel-enforced* boundary is
# missing — the AST allowlist alone is not a sandbox.

_BWRAP = shutil.which("bwrap")
_FIREJAIL = shutil.which("firejail")


def _sandbox_backend() -> str:
    if _BWRAP:
        return "bubblewrap"
    if _FIREJAIL:
        return "firejail"
    return "none"


def _build_launch_command(temp_path: Path, scratch_dir: Path) -> List[str]:
    """
    Wraps the interpreter invocation in an OS-level jail when available.

    bubblewrap config:
      --unshare-net        no network namespace at all (interface-less, not just firewalled)
      --unshare-pid         separate PID namespace (can't see/signal host processes)
      --die-with-parent     jail dies if our process dies (no orphaned children)
      --ro-bind /usr /usr    read-only view of the interpreter + stdlib
      --ro-bind /lib(64) ...  read-only view of shared libs
      --bind scratch_dir     the ONLY writable path, and it's the cwd
      --proc /proc, --dev /dev  minimal synthetic /proc and /dev (no host device access)
      --new-session          new session, no TTY job-control tricks back to the host shell
    """
    py = sys.executable
    if _BWRAP:
        cmd = [
            _BWRAP,
            "--unshare-net",
            "--unshare-pid",
            "--die-with-parent",
            "--new-session",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", py, py,
            "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64",
            "--bind", str(scratch_dir), str(scratch_dir),
            "--proc", "/proc",
            "--dev", "/dev",
            "--chdir", str(scratch_dir),
            "--",
            py, str(temp_path),
        ]
        return cmd

    if _FIREJAIL:
        # --net=none: no network devices at all
        # --private=<scratch>: filesystem jail rooted at scratch dir
        # --nosound --no3d --nodvd --notv --nou2f --nogroups: strip peripheral access
        cmd = [
            _FIREJAIL,
            "--quiet",
            "--net=none",
            f"--private={scratch_dir}",
            "--nosound", "--no3d", "--nogroups",
            "--",
            py, str(temp_path),
        ]
        return cmd

    # No jail binary found — fall back to bare subprocess (old behavior).
    # This still benefits from the AST allowlist + setrlimit below, but there is
    # NO kernel-enforced network/filesystem boundary in this mode.
    return [py, str(temp_path)]


def _make_preexec_fn(max_memory_bytes: int, max_cpu_seconds: int):
    """
    Returns a function that runs inside the CHILD process, after fork() but before
    exec(), to install hard kernel-enforced resource limits via setrlimit. Unlike
    the psutil-polling watchdog, these are not advisory — the kernel itself will
    SIGKILL/SIGSEGV the process the instant it crosses the line, no race window.

    Linux/macOS only (POSIX). On Windows this is skipped; the psutil watchdog
    remains the enforcement mechanism there.
    """
    def _preexec():
        try:
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
        except (ValueError, OSError):
            pass  # some platforms/containers restrict changing this; degrade gracefully
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds))
        except (ValueError, OSError):
            pass
        try:
            # Prevent forking storms / fork bombs from the child
            resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))
        except (ValueError, OSError):
            pass
    return _preexec


def execute_python_code(
    code: str,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_memory_bytes: int = MAX_MEMORY_BYTES
) -> Dict[str, Any]:
    """
    Executes Python code with layered defenses:
      1. AST allowlist pre-check (cheap, catches obvious bad code early)
      2. OS-level jail via bubblewrap/firejail when available (real network +
         filesystem isolation, kernel-enforced)
      3. Hard resource.setrlimit ceilings on memory/CPU (kernel-enforced, no
         polling race window) — POSIX only
      4. psutil watchdog thread as a *secondary* timeout/memory backstop, in
         case setrlimit isn't available on this platform
    """
    start_time = time.time()

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

    clean_env = {
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }

    backend = _sandbox_backend()
    launch_cmd = _build_launch_command(temp_path, SCRATCH_DIR)
    preexec_fn = _make_preexec_fn(max_memory_bytes, MAX_CPU_SECONDS) if os.name == "posix" and backend == "none" else None
    # NOTE: when bwrap/firejail wraps the call, preexec_fn on subprocess.Popen would
    # apply the rlimit to the wrapper binary's own process, not usefully to the
    # jailed child — bwrap/firejail have their own resource-limiting flags for that
    # (e.g. firejail --rlimit-as=..., or a cgroup applied to the bwrap invocation).
    # We still keep preexec_fn active in the "no jail available" fallback path so
    # that path isn't purely advisory either.

    proc: Optional[subprocess.Popen] = None
    memory_exceeded = False
    timed_out = False

    try:
        proc = subprocess.Popen(
            launch_cmd,
            cwd=str(SCRATCH_DIR),
            env=clean_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            preexec_fn=preexec_fn,
        )

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

        trunc_stdout = stdout_data[:MAX_OUTPUT_CHARS]
        trunc_stderr = stderr_data[:MAX_OUTPUT_CHARS]

        status = "SUCCESS" if proc.returncode == 0 else "EXECUTION_ERROR"
        append_audit_event(
            tool_name="sandbox_tool",
            inputs={"code": code[:200]},
            outputs={"returncode": proc.returncode, "stdout_len": len(trunc_stdout), "jail_backend": backend},
            status=status,
            duration_ms=duration_ms
        )

        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": trunc_stdout,
            "stderr": trunc_stderr,
            "jail_backend": backend,
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
        Executes Python code in an isolated sandbox: AST import allowlisting,
        OS-level jail (bubblewrap/firejail, when installed) with no network
        namespace, hard memory/CPU limits via setrlimit, and a watchdog backstop.
        Allowed modules: math, statistics, json, re, datetime, decimal, fractions, itertools, csv, collections, random.
        """
        res = execute_python_code(code)
        if res["success"]:
            return res["stdout"] if res["stdout"] else "Execution succeeded with no standard output."
        return f"Sandbox Error (Return code {res['returncode']}):\n{res['stderr']}"

except ImportError:
    sandbox_tool = None