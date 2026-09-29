"""
Geological Extractor Tool for CMPDI / Coal India Limited (CIL)
=============================================================
Multi-engine extraction pipeline for scanned borehole lithology logs, core sample records,
strata charts, and geological mine reports.

Supports: .pdf, .png, .jpg, .jpeg, .tiff
Engines: PyMuPDF (digital vector extraction) + EasyOCR (local GPU/CPU, 100% air-gapped)
         + Regex heuristic parsers for mining and geological parameters.
"""

import sys
import os
import re
import logging
from typing import Optional, Tuple, Dict, Any, List

# Ensure workspace root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.mining import GeologicalExtractionResult
from tools.audit_trail import AuditLedger

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    import pymupdf as fitz  # PyMuPDF
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GeologicalExtractorTool:
    """
    Multi-engine OCR & geological parameter extraction pipeline for borehole logs,
    lithology profiles, seam core analyses, and CMPDI exploration dossiers.
    """

    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

        # Initialize EasyOCR reader (runs entirely offline on local GPU/CPU)
        if easyocr is not None:
            try:
                self.reader = easyocr.Reader(['en'], gpu=True)
            except Exception:
                self.reader = easyocr.Reader(['en'], gpu=False)
        else:
            self.reader = None

        # Regex patterns tailored for CMPDI borehole logs, coal seams, and strata lithology
        self.patterns = {
            "borehole_id": re.compile(
                r'(?:Borehole\s*(?:ID|No\.?|Number)|BH\s*(?:No\.?|#)|Drillhole\s*No\.?)[:\s]*([A-Za-z0-9\-_/]+)',
                re.IGNORECASE
            ),
            "depth_m": re.compile(
                r'(?:Total\s*Depth|Borehole\s*Depth|Depth\s*to\s*Bottom|Depth)[:\s]*([\d.]+)\s*(?:m|mtr|meters|metres)?',
                re.IGNORECASE
            ),
            "seam_name": re.compile(
                r'(?:Coal\s*Seam|Seam\s*(?:Name|No\.?|Designation)?|Seam)[:\s]*([A-Za-z0-9\-\(\)\sIVXLCDM]+?)(?:\n|,|;|$)',
                re.IGNORECASE
            ),
            "coal_thickness_m": re.compile(
                r'(?:Coal\s*Thickness|Seam\s*Thickness|Clean\s*Coal\s*Thickness)[:\s]*([\d.]+)\s*(?:m|mtr|meters|metres)?',
                re.IGNORECASE
            ),
            "overburden_thickness_m": re.compile(
                r'(?:Overburden\s*(?:Thickness|Depth)|Parting\s*(?:Thickness)?|OB\s*Thickness)[:\s]*([\d.]+)\s*(?:m|mtr|meters|metres)?',
                re.IGNORECASE
            ),
            "ash_content_percentage": re.compile(
                r'Ash(?:\s*Content|\s*Percentage|\s*%)?(?:\s*\(adb\))?[:\s]*([\d.]+)',
                re.IGNORECASE
            ),
            "moisture_percentage": re.compile(
                r'(?:Inherent\s*)?Moisture(?:\s*Content|\s*Percentage|\s*%)?[:\s]*([\d.]+)',
                re.IGNORECASE
            ),
            "gcv_kcal_kg": re.compile(
                r'(?:Gross\s*Calorific\s*Value(?:\s*\(GCV\))?|GCV)[:\s=]*([\d.]+)',
                re.IGNORECASE
            ),

            "formation": re.compile(
                r'(?:Geological\s*Formation|Stratigraphic\s*Horizon|Formation)[:\s]*([A-Za-z0-9\-\s]+?(?:Formation|Group|Series|Horizon))',
                re.IGNORECASE
            ),
            "subsidiary": re.compile(
                r'\b(CMPDI|ECL|BCCL|CCL|WCL|SECL|MCL|NCL|CIL)\b',
                re.IGNORECASE
            ),
            "mine_block": re.compile(
                r'(?:Mine\s*Block|Coal\s*Block|Block\s*Name|Coalfield|Colliery)[:\s]*([A-Za-z0-9\-\s\(\)]+?)(?:\n|,|;|$)',
                re.IGNORECASE
            )
        }

        # Known geological formations in Indian coalfields for fallback semantic matching
        self.known_formations = [
            "Barakar Formation",
            "Raniganj Formation",
            "Karharbari Formation",
            "Talchir Formation",
            "Damuda Group",
            "Panchet Formation",
            "Kamthi Formation"
        ]

    def _pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF pages to image files using PyMuPDF for local OCR processing."""
        if fitz is None:
            raise RuntimeError("PyMuPDF (fitz) is required for PDF processing. Install: pip install pymupdf")

        import tempfile
        images = []
        doc = fitz.open(pdf_path)
        tmpdir = tempfile.mkdtemp(prefix="aegis_geo_ocr_")
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_path = os.path.join(tmpdir, f"page_{page.number}.png")
            pix.save(img_path)
            images.append(img_path)
        doc.close()
        return images

    def _extract_text_direct(self, file_path: str) -> Optional[str]:
        """Attempt direct text extraction for native digital PDFs before falling back to OCR."""
        if fitz is None or not file_path.lower().endswith('.pdf'):
            return None
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            # If significant text is extracted (not just blank pages or images)
            if len(text.strip()) > 80:
                return text.strip()
        except Exception as e:
            logger.warning(f"Direct PDF text extraction failed: {e}")
        return None

    def _run_ocr(self, file_path: str) -> Tuple[str, float]:
        """Run OCR on image or scanned PDF and return (raw_text, confidence)."""
        # First try direct text extraction if digital PDF
        direct_text = self._extract_text_direct(file_path)
        if direct_text:
            return direct_text, 0.98

        if self.reader is None:
            raise RuntimeError("EasyOCR is not installed. Install: pip install easyocr")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.txt', '.md', '.log', '.json']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return content, 0.99
        elif ext == '.pdf':
            image_paths = self._pdf_to_images(file_path)
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.tif']:
            image_paths = [file_path]
        else:
            raise ValueError(f"Unsupported file type for geological extraction: {ext}")


        all_text = []
        all_confidences = []

        for img_path in image_paths:
            results = self.reader.readtext(img_path)
            for (bbox, text, confidence) in results:
                all_text.append(text)
                all_confidences.append(confidence)

        # Cleanup temporary files
        if ext == '.pdf':
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except OSError:
                    pass

        raw_text = "\n".join(all_text)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        return raw_text, round(avg_confidence, 3)

    def _extract_parameters(self, raw_text: str) -> Dict[str, Any]:
        """Apply regex patterns and geological heuristics to extract structured parameters."""
        extracted: Dict[str, Any] = {}

        for key, pattern in self.patterns.items():
            match = pattern.search(raw_text)
            if match:
                value = match.group(1).strip()
                # Parse numeric values for quantitative geological fields
                if key in ["depth_m", "coal_thickness_m", "overburden_thickness_m",
                            "ash_content_percentage", "moisture_percentage", "gcv_kcal_kg"]:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                extracted[key] = value

        # Secondary heuristic check for known geological formations
        if "formation" not in extracted or not extracted["formation"]:
            for formation in self.known_formations:
                if formation.lower() in raw_text.lower():
                    extracted["formation"] = formation
                    break

        # Check for CIL subsidiary mention if not explicitly keyed
        if "subsidiary" not in extracted or not extracted["subsidiary"]:
            for sub in ["CMPDI", "ECL", "BCCL", "CCL", "WCL", "SECL", "MCL", "NCL", "CIL"]:
                if re.search(r'\b' + re.escape(sub) + r'\b', raw_text, re.IGNORECASE):
                    extracted["subsidiary"] = sub.upper()
                    break

        return extracted

    def extract(self, file_path: str, caller_agent: str = "vision_agent") -> GeologicalExtractionResult:
        """
        Main entry point for geological extraction. Takes a path to a scanned
        borehole log or lithology report and returns structured mining parameters.
        """
        if not os.path.exists(file_path):
            result = GeologicalExtractionResult(
                status="ERROR",
                confidence_score=0.0,
                requires_human_confirmation=True,
                error=f"File not found: {file_path}"
            )
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        try:
            raw_text, confidence = self._run_ocr(file_path)
        except Exception as e:
            result = GeologicalExtractionResult(
                status="ERROR",
                confidence_score=0.0,
                requires_human_confirmation=True,
                error=str(e)
            )
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        extracted = self._extract_parameters(raw_text)

        # Flag for human sign-off if confidence is marginal or critical fields are missing
        has_critical = bool(extracted.get("seam_name") or extracted.get("coal_thickness_m") or extracted.get("depth_m"))
        requires_human = confidence < 0.80 or not has_critical

        if not has_critical:
            status = "NO_PARAMETERS_FOUND"
        elif requires_human:
            status = "MARGINAL_CONFIDENCE"
        else:
            status = "VALIDATED"

        result = GeologicalExtractionResult(
            status=status,
            confidence_score=confidence,
            requires_human_confirmation=requires_human,
            borehole_id=extracted.get("borehole_id"),
            mine_block=extracted.get("mine_block"),
            subsidiary=extracted.get("subsidiary"),
            formation=extracted.get("formation"),
            seam_name=extracted.get("seam_name"),
            coal_thickness_m=extracted.get("coal_thickness_m"),
            depth_m=extracted.get("depth_m"),
            overburden_thickness_m=extracted.get("overburden_thickness_m"),
            ash_content_percentage=extracted.get("ash_content_percentage"),
            moisture_percentage=extracted.get("moisture_percentage"),
            gcv_kcal_kg=extracted.get("gcv_kcal_kg"),
            extracted_parameters=extracted,
            raw_ocr_text=raw_text
        )

        return self._log_and_return(result, file_path, caller_agent, "COMPLETED")

    def _log_and_return(self, result: GeologicalExtractionResult, file_path: str, caller_agent: str, status: str) -> GeologicalExtractionResult:
        if self.use_audit_trail:
            file_hash = AuditLedger.hash_artifact(file_path) or "FILE_NOT_FOUND"
            self.ledger.append_event(
                event_type="DOCUMENT_INGESTION",
                workflow_id="GEOLOGICAL_LOG_EXTRACTION",
                tool_name="geological_extractor_tool",
                caller=caller_agent,
                agent_version="2.0.0",
                tool_version="2.0.0",
                inputs={"file_path": file_path, "file_hash": file_hash},
                outputs=result.model_dump(),
                status=status
            )
        return result


# Backward compatibility alias
InspectionExtractorTool = GeologicalExtractorTool


# =============================================================================
# LangChain Tool Wrappers
# =============================================================================

from langchain_core.tools import tool
from pydantic import BaseModel, Field

class FileInput(BaseModel):
    file_path: str = Field(..., description="Path to the scanned borehole log or geological PDF/image file")


@tool(args_schema=FileInput)
def extract_geological_data(file_path: str) -> dict:
    """Extracts geological and borehole log parameters (depth, seam, thickness, ash %, formation) from documents."""
    logger.info(f"Executing tool: extract_geological_data on {file_path}")
    try:
        extractor = GeologicalExtractorTool()
        return extractor.extract(file_path).model_dump()
    except Exception as e:
        logger.error(f"Error in extract_geological_data: {e}")
        return {"status": "error", "error": str(e)}


# Backward compatibility LangChain tool for legacy agent nodes
@tool(args_schema=FileInput)
def extract_inspection_data(file_path: str) -> dict:
    """Extracts parameters from a document (Geological / Borehole extraction)."""
    return extract_geological_data.invoke({"file_path": file_path})
