import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.file_io import FileIOResult
from tools.audit_trail import AuditLedger


class SecureFileIO:
    """
    Workspace-Confined File Operations with path-traversal protection.

    Resolves canonical paths and raises PermissionError if any agent or script
    attempts to access directories outside the project workspace root.
    This prevents LLM-generated file paths from escaping the sandbox.
    """

    def __init__(self, use_audit_trail: bool = True):
        self.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def _validate_path(self, file_path: str) -> str:
        """
        Resolves the canonical path and checks it is within the workspace root.
        Raises PermissionError if the path escapes the workspace boundary.
        """
        # Resolve to absolute canonical path (resolves ../ and symlinks)
        canonical = os.path.realpath(os.path.join(self.workspace_root, file_path))

        # Use os.path.normcase to handle Windows drive letter casing (C:\ vs c:\)
        norm_canonical = os.path.normcase(canonical)
        norm_workspace = os.path.normcase(self.workspace_root)

        if not norm_canonical.startswith(norm_workspace):
            raise PermissionError(
                f"Security Alert: Path traversal attempt blocked. "
                f"Requested path '{file_path}' resolves to '{canonical}' "
                f"which is outside the workspace root '{self.workspace_root}'."
            )
        return canonical

    def read_file(self, file_path: str, caller_agent: str = "coder_agent") -> FileIOResult:
        """Read a file within the workspace boundary."""
        try:
            canonical = self._validate_path(file_path)
        except PermissionError as e:
            result = FileIOResult(status="BLOCKED", action="read", file_path=file_path, error=str(e))
            return self._log_and_return(result, caller_agent, "BLOCKED_PATH_TRAVERSAL")

        if not os.path.exists(canonical):
            result = FileIOResult(status="ERROR", action="read", file_path=file_path, error=f"File not found: {canonical}")
            return self._log_and_return(result, caller_agent, "FAILED")

        try:
            with open(canonical, 'r', encoding='utf-8') as f:
                content = f.read()
            result = FileIOResult(status="SUCCESS", action="read", file_path=canonical, content=content)
            return self._log_and_return(result, caller_agent, "COMPLETED")
        except Exception as e:
            result = FileIOResult(status="ERROR", action="read", file_path=canonical, error=str(e))
            return self._log_and_return(result, caller_agent, "FAILED")

    def write_file(self, file_path: str, content: str, caller_agent: str = "coder_agent") -> FileIOResult:
        """Write content to a file within the workspace boundary."""
        try:
            canonical = self._validate_path(file_path)
        except PermissionError as e:
            result = FileIOResult(status="BLOCKED", action="write", file_path=file_path, error=str(e))
            return self._log_and_return(result, caller_agent, "BLOCKED_PATH_TRAVERSAL")

        try:
            os.makedirs(os.path.dirname(canonical), exist_ok=True)
            with open(canonical, 'w', encoding='utf-8') as f:
                bytes_written = f.write(content)
            result = FileIOResult(status="SUCCESS", action="write", file_path=canonical, bytes_written=bytes_written)
            return self._log_and_return(result, caller_agent, "COMPLETED")
        except Exception as e:
            result = FileIOResult(status="ERROR", action="write", file_path=canonical, error=str(e))
            return self._log_and_return(result, caller_agent, "FAILED")

    def _log_and_return(self, result: FileIOResult, caller_agent: str, status: str) -> FileIOResult:
        if self.use_audit_trail:
            # Never log file content to audit trail (could be sensitive)
            log_outputs = {"status": result.status, "action": result.action, "file_path": result.file_path}
            if result.error:
                log_outputs["error"] = result.error

            self.ledger.append_event(
                event_type="FILE_OPERATION",
                workflow_id="WORKSPACE_FILE_IO",
                tool_name="file_io",
                caller=caller_agent,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs={"file_path": result.file_path, "action": result.action},
                outputs=log_outputs,
                status=status
            )
        return result

from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ReadFileInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to read")

@tool
def read_scanned_pdf(inp: ReadFileInput) -> dict:
    """Reads a file (text or simulated PDF read)."""
    print(f"\n--- EXECUTING TOOL: read_scanned_pdf ---\n")
    logger.info(f"Executing tool: read_scanned_pdf")
    try:
        io = SecureFileIO()
        return io.read_file(inp.file_path).model_dump()
    except Exception as e:
        logger.error(f"Error in read_scanned_pdf: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test for Secure File IO
    logger.info("Testing read_scanned_pdf...")
    mock_input = ReadFileInput(file_path="data/test_dossiers/ID-9982_UT_Scan.txt")
    result = read_scanned_pdf.invoke({"inp": mock_input})
    logger.info(f"Result: {result}")
