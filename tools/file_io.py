import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.file_io import FileIOResult
from tools.audit_trail import AuditLedger


from pathlib import Path

class SecureFileIO:
    """
    Workspace-Confined File Operations with path-traversal protection.

    Resolves canonical paths and raises PermissionError if any agent or script
    attempts to access directories outside the project workspace root.
    This prevents LLM-generated file paths from escaping the sandbox.
    """

    def __init__(self, use_audit_trail: bool = True):
        self.workspace_root = Path(__file__).resolve().parent.parent
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def _validate_path(self, file_path: str) -> str:
        """
        Resolves canonical Path and checks it is strictly confined within workspace_root.
        Handles relative parent navigation from subdirectories like agent_orchestrator/.
        Raises PermissionError if path escapes the workspace root boundary.
        """
        raw_path = Path(file_path)

        if not raw_path.is_absolute():
            # First try direct resolution relative to workspace root
            candidate = (self.workspace_root / raw_path).resolve()
            # If not found and path starts with '..' (e.g. from notebook), strip relative navigation
            if not candidate.exists() and str(file_path).startswith(".."):
                clean_parts = [p for p in raw_path.parts if p not in ("..", ".")]
                alternate = (self.workspace_root / Path(*clean_parts)).resolve()
                if alternate.exists():
                    candidate = alternate
            canonical = candidate
        else:
            canonical = raw_path.resolve()

        # Enforce workspace boundary via Path.relative_to
        try:
            canonical.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Security Alert: Path traversal attempt blocked. "
                f"Requested path '{file_path}' resolves to '{canonical}' "
                f"which is outside the workspace root '{self.workspace_root}'."
            )

        return str(canonical)



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

        if canonical.lower().endswith('.pdf'):
            try:
                try:
                    import pymupdf as fitz
                except ImportError:
                    import fitz
                doc = fitz.open(canonical)
                extracted_pages = []
                for page in doc:
                    text = page.get_text()
                    if text and text.strip():
                        extracted_pages.append(text.strip())
                doc.close()

                if extracted_pages:
                    content = "\n\n".join(extracted_pages)
                    result = FileIOResult(status="SUCCESS", action="read", file_path=canonical, content=content)
                    return self._log_and_return(result, caller_agent, "COMPLETED")
                else:
                    # If digital text extraction is empty, try OCR extractor tool if available
                    try:
                        from tools.inspection_extractor_tool import InspectionExtractorTool
                        extractor = InspectionExtractorTool(use_audit_trail=False)
                        extraction = extractor.extract(canonical, caller_agent=caller_agent)
                        content = extraction.raw_ocr_text or str(extraction.extracted_parameters)
                        result = FileIOResult(status="SUCCESS", action="read", file_path=canonical, content=content)
                        return self._log_and_return(result, caller_agent, "COMPLETED")
                    except Exception as ocr_err:
                        result = FileIOResult(status="ERROR", action="read", file_path=canonical, error=f"PDF has no digital text and OCR failed: {ocr_err}")
                        return self._log_and_return(result, caller_agent, "FAILED")
            except Exception as e:
                result = FileIOResult(status="ERROR", action="read", file_path=canonical, error=f"PDF extraction error: {e}")
                return self._log_and_return(result, caller_agent, "FAILED")

        if canonical.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp')):
            try:
                from tools.inspection_extractor_tool import InspectionExtractorTool
                extractor = InspectionExtractorTool(use_audit_trail=False)
                extraction = extractor.extract(canonical, caller_agent=caller_agent)
                content = f"[OCR EXTRACTION FROM IMAGE: {os.path.basename(canonical)}]\n" + (extraction.raw_ocr_text or str(extraction.extracted_parameters))
                result = FileIOResult(status="SUCCESS", action="read", file_path=canonical, content=content)
                return self._log_and_return(result, caller_agent, "COMPLETED")
            except Exception as ocr_err:
                result = FileIOResult(status="ERROR", action="read", file_path=canonical, error=f"Image OCR failed: {ocr_err}")
                return self._log_and_return(result, caller_agent, "FAILED")

        if canonical.lower().endswith(('.csv', '.xlsx')):
            try:
                from tools.thickness_grid_analyzer import analyze_thickness_grid
                grid_res = analyze_thickness_grid.invoke({"file_path": canonical})
                import json as _json
                content = f"[COORDINATE THICKNESS GRID: {os.path.basename(canonical)}]\n" + _json.dumps(grid_res, indent=2)
                result = FileIOResult(status="SUCCESS", action="read", file_path=canonical, content=content)
                return self._log_and_return(result, caller_agent, "COMPLETED")
            except Exception as grid_err:
                pass

        try:
            with open(canonical, 'r', encoding='utf-8', errors='replace') as f:
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
def read_scanned_pdf(file_path: str) -> dict:
    """Reads a file (text or simulated PDF read)."""
    print(f"\n--- EXECUTING TOOL: read_scanned_pdf ---\n")
    logger.info(f"Executing tool: read_scanned_pdf")
    try:
        io = SecureFileIO()
        return io.read_file(file_path).model_dump()
    except Exception as e:
        logger.error(f"Error in read_scanned_pdf: {e}")
        return {"status": "error", "error": str(e)}


