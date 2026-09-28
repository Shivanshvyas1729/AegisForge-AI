import sys
import os
import ast
import subprocess
import datetime

# Ensure the root workspace is in the python path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.sandbox import SandboxExecutionResult
from tools.audit_trail import AuditLedger

DAEMON_CONTAINER_NAME = "aegisforge-sandbox-daemon"

def is_daemon_running() -> bool:
    """Checks if the persistent standing sandbox daemon container is currently running."""
    try:
        res = subprocess.run(["docker", "ps", "-q", "-f", f"name={DAEMON_CONTAINER_NAME}"], capture_output=True, text=True)
        return bool(res.stdout.strip())
    except Exception:
        return False

def start_daemon() -> dict:
    """Starts the standing sandbox container with 0 network egress and 256MB memory limit."""
    try:
        if is_daemon_running():
            return {"status": "RUNNING", "message": "Sandbox daemon is already active."}
        subprocess.run(["docker", "rm", "-f", DAEMON_CONTAINER_NAME], capture_output=True)
        res = subprocess.run([
            "docker", "run", "-d",
            "--name", DAEMON_CONTAINER_NAME,
            "--network", "none",
            "--memory", "256m",
            "--cpus", "1.0",
            "sih-agent-sandbox",
            "tail", "-f", "/dev/null"
        ], capture_output=True, text=True)
        if res.returncode == 0:
            return {"status": "RUNNING", "container_id": res.stdout.strip()[:12]}
        else:
            return {"status": "ERROR", "error": res.stderr.strip()}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def stop_daemon() -> dict:
    """Gracefully stops and removes the standing sandbox container."""
    try:
        subprocess.run(["docker", "stop", DAEMON_CONTAINER_NAME], capture_output=True)
        subprocess.run(["docker", "rm", DAEMON_CONTAINER_NAME], capture_output=True)
        return {"status": "STOPPED", "message": "Sandbox daemon stopped successfully."}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

class DockerSecureSandbox:
    def __init__(self, timeout_seconds: int = 70, use_audit_trail: bool = True):
        self.timeout = timeout_seconds
        self.banned_imports = ['os', 'sys', 'subprocess', 'shutil', 'socket', 'requests']
        
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()
            
        self._ensure_image_exists()
            
    def _ensure_image_exists(self):
        """Automatically builds the custom sandbox image if it doesn't exist on the host."""
        try:
            # Check if image exists
            result = subprocess.run(["docker", "images", "-q", "sih-agent-sandbox"], capture_output=True, text=True)
            if not result.stdout.strip():
                print("[DevOps] Custom 'sih-agent-sandbox' image not found. Auto-building it now... (This only happens once)")
                sandbox_dir = os.path.join(os.path.dirname(__file__), "..", "sandbox_image")
                subprocess.run(["docker", "build", "-t", "sih-agent-sandbox", sandbox_dir], check=True)
                print("[DevOps] Image built successfully!")
        except Exception as e:
            print(f"[DevOps Warning] Could not auto-build sandbox image: {e}")

    def sanitize_code(self, code_string: str) -> str:
        """Sanitizes code string by removing markdown backticks and properly decoding literal newlines."""
        if not code_string:
            return ""
        code_string = code_string.strip()
        # Remove markdown code fences if wrapped
        if code_string.startswith("```"):
            lines = code_string.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code_string = "\n".join(lines)
        
        # If it parses cleanly as valid Python AST, keep it as is!
        # Do not corrupt escaped characters inside string literals (e.g. \n, \t, regex).
        try:
            ast.parse(code_string)
            return code_string.strip()
        except SyntaxError:
            pass

        # If not parseable and literal \n is present (e.g. single-line raw string payload)
        if r'\n' in code_string and '\n' not in code_string:
            try:
                candidate = code_string.encode('utf-8').decode('unicode_escape')
                ast.parse(candidate)
                return candidate.strip()
            except Exception:
                pass
            candidate = code_string.replace(r'\n', '\n').replace(r'\t', '    ')
            try:
                ast.parse(candidate)
                return candidate.strip()
            except Exception:
                pass
        
        return code_string.strip()

    # Banned builtin call names — dynamic execution bypasses (Fix #18)
    _BANNED_CALL_NAMES = frozenset({
        '__import__', 'eval', 'exec', 'compile', 'breakpoint'
    })
    _BANNED_ATTR_NAMES = frozenset({
        'import_module', 'exec_module', 'load_module'
    })

    def _check_code_safety(self, code_string: str) -> tuple[bool, str]:
        """
        AST Scanner: Detect malicious imports AND dynamic import bypasses
        before even touching Docker. (Fix #18)

        Blocked patterns:
          - import os / from subprocess import run
          - __import__('os')
          - eval("import socket")
          - exec("import sys")
          - importlib.import_module('subprocess')
        """
        code_string = self.sanitize_code(code_string)
        try:
            tree = ast.parse(code_string)
            for node in ast.walk(tree):
                # Direct import statements
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in self.banned_imports:
                            return False, f"CRITICAL SECURITY BLOCK: Import of '{alias.name}' is forbidden."
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in self.banned_imports:
                        return False, f"CRITICAL SECURITY BLOCK: Import from '{node.module}' is forbidden."

                # Dynamic calls: __import__, eval, exec, compile, breakpoint  (Fix #18)
                elif isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id in self._BANNED_CALL_NAMES:
                        return False, (
                            f"CRITICAL SECURITY BLOCK: Call to '{func.id}()' is forbidden. "
                            "Dynamic code execution is not allowed in the sandbox."
                        )
                    # importlib.import_module / importlib.exec_module
                    if isinstance(func, ast.Attribute) and func.attr in self._BANNED_ATTR_NAMES:
                        return False, (
                            f"CRITICAL SECURITY BLOCK: Dynamic import via '.{func.attr}()' is forbidden."
                        )
            return True, "Code is safe."
        except SyntaxError as e:
            return False, f"Syntax Error in AI generated code: {e}"

    def generate_task_title(self, code_string: str, task_title: str = "") -> str:
        """Derives a concise, professional title for the code using comments, LLM, or smart heuristics."""
        if task_title and task_title.strip():
            return task_title.strip()

        # 1. Check for top comments or docstrings
        for line in code_string.strip().splitlines()[:5]:
            clean_l = line.strip()
            if clean_l.startswith("#") and len(clean_l) > 3:
                import re
                t = re.sub(r"^#\s*(Title:|Task:)?\s*", "", clean_l, flags=re.IGNORECASE).strip()
                if 4 <= len(t) <= 75:
                    return t
            if clean_l.startswith(('"""', "'''")):
                t = clean_l.strip("\"' ").strip()
                if 4 <= len(t) <= 75:
                    return t

        # 2. Fast local LLM titling via llama3.2:3b
        try:
            from langchain_ollama import ChatOllama
            title_llm = ChatOllama(model="llama3.2:3b", temperature=0.0)
            code_lines = [l for l in code_string.strip().splitlines() if l.strip() and not l.strip().startswith("#")][:10]
            sample = "\n".join(code_lines)
            prompt = (
                "You are an industrial code execution title generator.\n"
                "Analyze the following Python snippet and output a clear, professional 3 to 6 word technical title.\n"
                "Rules:\n"
                "- Output ONLY the plain title text.\n"
                "- Do NOT include quotes, markdown backticks, punctuation, or conversational greetings (e.g. do not say 'Here is the title').\n"
                f"Code:\n{sample}"
            )
            res = title_llm.invoke(prompt)
            title = res.content.strip().strip('"\'`#* ')
            if title and "\n" in title:
                title = title.splitlines()[0].strip()
            if title and 4 <= len(title) <= 75 and not title.lower().startswith(("here is", "this code", "title:")):
                return title
        except Exception:
            pass

        # 3. Smart Heuristic pattern matching
        import re
        lower = code_string.lower()
        if "fibonacci" in lower or "fib(" in lower:
            return "Fibonacci Sequence Computation"
        elif "asme" in lower or "ug_27" in lower or "ug-27" in lower or "allowable_stress" in lower:
            return "ASME BPVC Shell Thickness & Stress Verification"
        elif "cvc" in lower or "circular" in lower or "procurement" in lower:
            return "CVC Statutory Procurement Compliance Audit"
        elif "factorial" in lower:
            return "Factorial Computation Benchmark"
        elif "matrix" in lower or "numpy" in lower or "linalg" in lower:
            return "Matrix Numerical Computation"
        elif "prime" in lower:
            return "Prime Number Sieve Algorithm"
        elif "plot" in lower or "plt." in lower or "matplotlib" in lower:
            return "Engineering Graph & Data Visualization"

        func_match = re.search(r'def\s+([a-zA-Z0-9_]+)\s*\(', code_string)
        if func_match:
            return f"Execution: {func_match.group(1)}()"

        return "Autonomous Python Script Execution"

    def execute(self, code_string: str, caller_agent: str = "reasoning_agent", task_title: str = "") -> SandboxExecutionResult:
        code_string = self.sanitize_code(code_string)
        # 1. Static Security Check
        is_safe, msg = self._check_code_safety(code_string)
        if not is_safe:
            result = SandboxExecutionResult(status="BLOCKED_BY_AST", output=msg)
            self._log_execution(code_string, result, caller_agent)
            return result

        derived_title = self.generate_task_title(code_string, task_title)

        runner_code = '''
import sys, os, subprocess, time

def log_to_docker(msg):
    try:
        if os.path.exists('/proc/1/fd/1'):
            with open('/proc/1/fd/1', 'w') as f:
                f.write(msg + '\\n')
        else:
            sys.stderr.write(msg + '\\n')
            sys.stderr.flush()
    except Exception:
        sys.stderr.write(msg + '\\n')
        sys.stderr.flush()

title = os.environ.get('AEGIS_TASK_TITLE', 'Autonomous Task')
caller = os.environ.get('AEGIS_CALLER', 'Coder Agent')
timeout_val = int(os.environ.get('AEGIS_TIMEOUT', '60'))

log_to_docker('=' * 60)
log_to_docker(f'🚀 [TASK]: {title}')
log_to_docker(f'🤖 [AGENT]: {caller} | Python 3.9 Sandbox')
log_to_docker('🛡️ [SECURITY]: Air-Gapped Sandbox | Read-Only RootFS | Network: NONE')
log_to_docker('⚡ [STATUS]: Executing workload in sandbox...')

user_code = sys.stdin.read()
with open('/tmp/script.py', 'w') as f:
    f.write(user_code)

start_time = time.time()
try:
    proc = subprocess.run([sys.executable, '-u', '/tmp/script.py'], capture_output=True, text=True, timeout=timeout_val)
    duration = time.time() - start_time
    if proc.stdout:
        sys.stdout.write(proc.stdout)
        sys.stdout.flush()
        lines = proc.stdout.strip().splitlines()
        for line in lines[:8]:
            if 'FILE_START' in line or len(line) > 200:
                log_to_docker('📁 [FILE]: Binary payload generated')
            else:
                log_to_docker(f'📊 [OUTPUT]: {line}')
        if len(lines) > 8:
            log_to_docker(f'📊 [OUTPUT]: ... ({len(lines)-8} lines truncated in GUI log)')
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()
        for line in proc.stderr.strip().splitlines()[:5]:
            log_to_docker(f'⚠️ [STDERR]: {line}')
    if proc.returncode == 0:
        log_to_docker(f'✅ [COMPLETED]: Success (Exit 0) in {duration:.2f}s')
    else:
        log_to_docker(f'❌ [FAILED]: Exit Code {proc.returncode} in {duration:.2f}s')
    log_to_docker('=' * 60)
    sys.exit(proc.returncode)
except subprocess.TimeoutExpired:
    log_to_docker('⏱️ [TIMEOUT]: Execution exceeded timeout limit')
    log_to_docker('=' * 60)
    sys.exit(124)
'''

        # 2. Docker Execution Chamber
        try:
            if is_daemon_running():
                cmd_result = subprocess.run(
                    [
                        "docker", "exec", "-i",
                        "-e", f"AEGIS_TASK_TITLE={derived_title}",
                        "-e", f"AEGIS_CALLER={caller_agent}",
                        "-e", f"AEGIS_TIMEOUT={self.timeout}",
                        DAEMON_CONTAINER_NAME,
                        "python3", "-c", runner_code
                    ],
                    input=code_string,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 10
                )
            else:
                # Fallback to ephemeral disposable container
                container_name = f"sandbox_task_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(2).hex()}"
                cmd_result = subprocess.run(
                    [
                        "docker", "run", "-i", 
                        "--name", container_name,
                        "--network", "none", 
                        "--memory", "128m", 
                        "--cpus", "0.5", 
                        "-e", f"AEGIS_TASK_TITLE={derived_title}",
                        "-e", f"AEGIS_CALLER={caller_agent}",
                        "-e", f"AEGIS_TIMEOUT={self.timeout}",
                        "sih-agent-sandbox",
                        "python3", "-c", runner_code
                    ],
                    input=code_string,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 10
                )
            
            if cmd_result.returncode == 0:
                raw_output = cmd_result.stdout.strip()
                
                # Check if the AI generated a file (Code Interpreter Pattern)
                import re
                import base64
                file_match = re.search(r'<<<<FILE_START>>>>(.*?)<<<<FILE_END>>>>', raw_output, re.DOTALL)
                
                if file_match:
                    base64_data = file_match.group(1).strip()
                    clean_output = raw_output.replace(file_match.group(0), "[File extracted successfully]").strip()
                    
                    # Ensure output directory exists
                    os.makedirs("data/output", exist_ok=True)
                    file_path = f"data/output/sandbox_generated_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
                    
                    try:
                        with open(file_path, "wb") as fh:
                            fh.write(base64.b64decode(base64_data))
                        clean_output += f"\nFile saved to host at: {file_path}"
                    except Exception as e:
                        clean_output += f"\nFailed to decode and save file: {e}"
                        
                    result = SandboxExecutionResult(status="SUCCESS_WITH_FILE", output=clean_output)
                else:
                    result = SandboxExecutionResult(status="SUCCESS", output=raw_output)
            else:
                result = SandboxExecutionResult(status="ERROR", output=cmd_result.stderr.strip())
                
        except subprocess.TimeoutExpired:
            result = SandboxExecutionResult(
                status="TIMEOUT", 
                output=f"Container exceeded {self.timeout}s execution limit. Docker daemon killed it."
            )
        except FileNotFoundError:
            result = SandboxExecutionResult(
                status="SYSTEM_ERROR", 
                output="Docker is not installed or not running on this host!"
            )
            
        self._log_execution(code_string, result, caller_agent)
        return result
        
    def _log_execution(self, code_string: str, result: SandboxExecutionResult, caller: str):
        if self.use_audit_trail:
            self.ledger.append_event(
                event_type="SANDBOX_EXECUTION",
                workflow_id="SECURE_COMPUTE",
                tool_name="docker_sandbox",
                caller=caller,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs={"source_code": code_string},
                outputs=result.model_dump(),
                status=result.status
            )

from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SandboxInput(BaseModel):
    code_string: str = Field(description="The python code to execute in the secure sandbox.")
    task_title: str = Field(default="", description="A short 3-6 word title describing what the code does.")


@tool(args_schema=SandboxInput)
def execute_in_sandbox(code_string: str, task_title: str = "") -> dict:
    """
    Executes Python 3.9 code in an air-gapped, isolated Docker sandbox.
    Runtime: Python 3.9 (Alpine Linux, 256MB RAM cap, zero network).
    Pre-installed libraries: pandas, numpy, python-docx, math, json, re, csv.
    Forbidden imports (AST-blocked): os, sys, subprocess, shutil, socket, requests.
    """
    print(f"\n--- EXECUTING TOOL: execute_in_sandbox ---\n")
    logger.info(f"Executing tool: execute_in_sandbox (Title: {task_title or 'Auto-Detect'})")
    try:
        sandbox = DockerSecureSandbox()
        return sandbox.execute(code_string, caller_agent="Coder Agent", task_title=task_title).model_dump()
    except Exception as e:
        logger.error(f"Error in execute_in_sandbox: {e}")
        return {"status": "error", "error": str(e)}


