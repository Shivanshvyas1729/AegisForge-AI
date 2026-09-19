import sys
import os
import ast
import subprocess
import datetime

# Ensure the root workspace is in the python path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.sandbox import SandboxExecutionResult
from tools.audit_trail import AuditLedger

class DockerSecureSandbox:
    def __init__(self, timeout_seconds: int = 15, use_audit_trail: bool = True):
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

    def _check_code_safety(self, code_string: str) -> tuple[bool, str]:
        """AST Scanner: Detect malicious imports before even touching Docker."""
        try:
            tree = ast.parse(code_string)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in self.banned_imports:
                            return False, f"CRITICAL SECURITY BLOCK: Import of '{alias.name}' is forbidden."
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in self.banned_imports:
                        return False, f"CRITICAL SECURITY BLOCK: Import from '{node.module}' is forbidden."
            return True, "Code is safe."
        except SyntaxError as e:
            return False, f"Syntax Error in AI generated code: {e}"

    def execute(self, code_string: str, caller_agent: str = "reasoning_agent") -> SandboxExecutionResult:
        # 1. Static Security Check
        is_safe, msg = self._check_code_safety(code_string)
        if not is_safe:
            result = SandboxExecutionResult(status="BLOCKED_BY_AST", output=msg)
            self._log_execution(code_string, result, caller_agent)
            return result

        # 2. Docker Execution Chamber
        try:
            cmd_result = subprocess.run(
                [
                    "docker", "run", "--rm", "-i", 
                    "--network", "none", 
                    "--memory", "128m", 
                    "--cpus", "0.5", 
                    "sih-agent-sandbox", "python", "-"
                ],
                input=code_string,
                capture_output=True,
                text=True,
                timeout=self.timeout
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
