import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.vision import InspectionExtractionResult
from tools.audit_trail import AuditLedger

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    import pymupdf as fitz  # PyMuPDF (formerly fitz) for PDF page-to-image conversion
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None



class InspectionExtractorTool:
    """
    Multi-engine OCR & parameter extraction pipeline for degraded field inspection
    reports, P&ID schematics, and handwritten inspector notes.

    Supports: .pdf, .png, .jpg, .tiff
    Uses: EasyOCR (on-device, air-gapped) + regex heuristic parsers.
    """

    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

        # Initialize EasyOCR reader (runs entirely on local GPU/CPU)
        if easyocr is not None:
            self.reader = easyocr.Reader(['en'], gpu=True)
        else:
            self.reader = None

        # Regex patterns for common refinery inspection parameters
        self.patterns = {
            "equipment_id": re.compile(r'(?:Equipment\s*(?:ID|No|Tag)[:\s]*|Tag[:\s]*)([A-Z0-9\-]+)', re.IGNORECASE),
            "design_pressure": re.compile(r'(?:Design\s*Pressure)[:\s]*([\d.]+)\s*(?:MPa|mpa|bar)', re.IGNORECASE),
            "measured_thickness": re.compile(r'(?:Measured\s*Thickness|Actual\s*Thickness|Min\.?\s*Thickness)[:\s]*([\d.]+)\s*(?:mm)?', re.IGNORECASE),
            "inside_radius": re.compile(r'(?:Inside\s*Radius|Internal\s*Radius|I\.?D\.?\s*/?\s*2)[:\s]*([\d.]+)\s*(?:mm)?', re.IGNORECASE),
            "corrosion_rate": re.compile(r'(?:Corrosion\s*Rate)[:\s]*([\d.]+)\s*(?:mm/yr|mm/year)?', re.IGNORECASE),
            "material": re.compile(r'(?:Material|MOC|Material\s*of\s*Construction)[:\s]*([A-Za-z0-9\-\+\s\.]+?)(?:\n|$)', re.IGNORECASE),
        }

    def _pdf_to_images(self, pdf_path: str) -> list:
        """Convert PDF pages to PIL images using PyMuPDF."""
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is required for PDF processing. Install: pip install pymupdf")
        
        images = []
        doc = fitz.open(pdf_path)
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_path = os.path.join(os.path.dirname(pdf_path), f"_temp_page_{page.number}.png")
            pix.save(img_path)
            images.append(img_path)
        doc.close()
        return images

    def _run_ocr(self, file_path: str) -> tuple:
        """Run EasyOCR on image or PDF and return (raw_text, confidence)."""
        if self.reader is None:
            raise RuntimeError("EasyOCR is not installed. Install: pip install easyocr")

        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            image_paths = self._pdf_to_images(file_path)
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
            image_paths = [file_path]
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        all_text = []
        all_confidences = []

        for img_path in image_paths:
            results = self.reader.readtext(img_path)
            for (bbox, text, confidence) in results:
                all_text.append(text)
                all_confidences.append(confidence)

        # Clean up temp files
        if ext == '.pdf':
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except OSError:
                    pass

        raw_text = "\n".join(all_text)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        return raw_text, round(avg_confidence, 3)

    def _extract_parameters(self, raw_text: str) -> dict:
        """Apply regex patterns to extract structured parameters from OCR text."""
        extracted = {}
        for key, pattern in self.patterns.items():
            match = pattern.search(raw_text)
            if match:
                value = match.group(1).strip()
                # Attempt numeric conversion for known numeric fields
                if key in ["design_pressure", "measured_thickness", "inside_radius", "corrosion_rate"]:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                extracted[key] = value
        return extracted

    def extract(self, file_path: str, caller_agent: str = "vision_agent") -> InspectionExtractionResult:
        """
        Main entry point. Takes a file path to a scanned document and returns
        structured inspection parameters with confidence metrics.
        """
        if not os.path.exists(file_path):
            result = InspectionExtractionResult(
                status="ERROR",
                confidence_score=0.0,
                requires_human_confirmation=True,
                error=f"File not found: {file_path}"
            )
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        try:
            raw_text, confidence = self._run_ocr(file_path)
        except RuntimeError as e:
            result = InspectionExtractionResult(
                status="ERROR",
                confidence_score=0.0,
                requires_human_confirmation=True,
                error=str(e)
            )
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        extracted = self._extract_parameters(raw_text)

        # If confidence is below threshold, flag for human review
        requires_human = confidence < 0.85

        if requires_human:
            status = "MARGINAL_CONFIDENCE"
        elif len(extracted) == 0:
            status = "NO_PARAMETERS_FOUND"
            requires_human = True
        else:
            status = "VALIDATED"

        result = InspectionExtractionResult(
            status=status,
            confidence_score=confidence,
            requires_human_confirmation=requires_human,
            extracted_parameters=extracted,
            raw_ocr_text=raw_text
        )
        return self._log_and_return(result, file_path, caller_agent, "COMPLETED")

    def _log_and_return(self, result: InspectionExtractionResult, file_path: str, caller_agent: str, status: str) -> InspectionExtractionResult:
        if self.use_audit_trail:
            # Hash the source document for provenance
            file_hash = AuditLedger.hash_artifact(file_path) or "FILE_NOT_FOUND"
            self.ledger.append_event(
                event_type="DOCUMENT_INGESTION",
                workflow_id="INSPECTION_OCR_EXTRACTION",
                tool_name="inspection_extractor_tool",
                caller=caller_agent,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs={"file_path": file_path, "file_hash": file_hash},
                outputs=result.model_dump(),
                status=status
            )
        return result

from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FileInput(BaseModel):
    file_path: str = Field(..., description="Path to the PDF file")

@tool
def extract_inspection_data(file_path: str) -> dict:
    """Extracts inspection parameters from a scanned PDF."""
    print(f"\n--- EXECUTING TOOL: extract_inspection_data ---\n")
    logger.info(f"Executing tool: extract_inspection_data")
    try:
        extractor = InspectionExtractorTool()
        return extractor.extract(file_path).model_dump()
    except Exception as e:
        logger.error(f"Error in extract_inspection_data: {e}")
        return {"status": "error", "error": str(e)}
