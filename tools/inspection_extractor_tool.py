"""
tools/inspection_extractor_tool.py
Multimodal Field Inspection Document Parameter Extractor & Sanity Validator.
Parses inspection documents (PDF, DOCX, XLSX, CSV, images) via ingestion.multimodal_parser,
extracts structural parameters via domain-specific regular expressions,
applies petrochemical physical sanity bounds, and enforces confidence gating.
"""

import re
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.multimodal_parser import parse_file_multimodal
from tools.file_io import _validate_safe_path
from tools.audit_trail import append_audit_event

# Known refinery metallurgical specifications
KNOWN_ALLOYS = {
    "2.25cr-1mo", "sa-516", "sa-516 gr 70", "sa-106", "sa-106 gr b",
    "sa-387", "sa-335", "ss 304", "ss 316", "ss 347", "347 ss",
    "carbon steel", "cs", "inconel 625", "monel 400", "titanium gr 2"
}

# Physical bounds for petrochemical pressure vessels
MIN_THICKNESS_MM = 0.5
MAX_THICKNESS_MM = 300.0
NORMAL_MAX_CR_MM_YR = 3.0
HARD_MAX_CR_MM_YR = 10.0


def extract_parameters_from_text(text: str) -> Tuple[Dict[str, Any], List[str], float]:
    """
    Applies regex patterns to raw document text, verifies physical bounds,
    and returns (extracted_dict, warnings_list, confidence_score).
    """
    extracted: Dict[str, Any] = {}
    warnings: List[str] = []
    score_parts = 0.0

    # 1. Equipment Tag (e.g. 11-V-102, V-101, C-201)
    tag_match = re.search(r'\b(\d{2}-[A-Z]{1,3}-\d{2,4}[A-Z]?)\b', text, re.IGNORECASE)
    if not tag_match:
        tag_match = re.search(r'\b([A-Z]{1,3}-\d{2,4}[A-Z]?)\b', text)
    if tag_match:
        extracted["equipment_id"] = tag_match.group(1).upper()
        score_parts += 0.25
    else:
        warnings.append("Equipment tag could not be positively identified.")

    # 2. Measured Thickness
    thk_match = re.search(
        r'(?:measured|actual|current|wall|shell|ultrasonic)?\s*(?:thickness|thk|t_act)[\s:=]*([0-9]+\.?[0-9]*)\s*(?:mm)?',
        text, re.IGNORECASE
    )
    if thk_match:
        try:
            thk = float(thk_match.group(1))
            if thk < MIN_THICKNESS_MM:
                warnings.append(f"THICKNESS_OUT_OF_BOUNDS: Extracted thickness {thk} mm is below physical minimum {MIN_THICKNESS_MM} mm.")
            elif thk > MAX_THICKNESS_MM:
                warnings.append(f"THICKNESS_OUT_OF_BOUNDS: Extracted thickness {thk} mm exceeds realistic vessel maximum {MAX_THICKNESS_MM} mm.")
            else:
                extracted["measured_thickness_mm"] = thk
                score_parts += 0.30
        except ValueError:
            warnings.append("Failed to parse numerical value for thickness.")
    else:
        warnings.append("Measured thickness value missing from document.")

    # 3. Corrosion Rate
    cr_match = re.search(
        r'(?:corrosion\s*rate|cr|rate\s*of\s*corrosion)[\s:=]*([0-9]+\.?[0-9]*)\s*(?:mm\/y(?:ea)?r|mm\/a|mpy)?',
        text, re.IGNORECASE
    )
    if cr_match:
        try:
            cr = float(cr_match.group(1))
            if cr < 0.0:
                warnings.append(f"Negative corrosion rate {cr} mm/yr rejected.")
            elif cr > HARD_MAX_CR_MM_YR:
                warnings.append(f"UNREALISTIC_CORROSION_RATE: Extracted CR {cr} mm/yr exceeds hard physical ceiling {HARD_MAX_CR_MM_YR} mm/yr.")
            elif cr > NORMAL_MAX_CR_MM_YR:
                extracted["corrosion_rate_mm_yr"] = cr
                warnings.append(f"HIGH_ANOMALY_CORROSION_RATE: CR {cr} mm/yr exceeds typical refinery threshold {NORMAL_MAX_CR_MM_YR} mm/yr.")
                score_parts += 0.10
            else:
                extracted["corrosion_rate_mm_yr"] = cr
                score_parts += 0.15
        except ValueError:
            pass
    else:
        extracted["corrosion_rate_mm_yr"] = 0.0
        score_parts += 0.05

    # 4. Design Pressure
    p_match = re.search(
        r'(?:design\s*pressure|p_design|pressure)[\s:=]*([0-9]+\.?[0-9]*)\s*(mpa|bar|barg|kg\/cm2)?',
        text, re.IGNORECASE
    )
    if p_match:
        try:
            val = float(p_match.group(1))
            unit = (p_match.group(2) or "mpa").lower()
            if "bar" in unit:
                val = round(val / 10.0, 2)  # Convert bar to MPa
            elif "kg" in unit:
                val = round(val * 0.0980665, 2)
            if 0.1 <= val <= 50.0:
                extracted["design_pressure_mpa"] = val
                score_parts += 0.15
            else:
                warnings.append(f"Design pressure {val} MPa is outside expected range (0.1 - 50.0 MPa).")
        except ValueError:
            pass

    # 5. Metallurgical Material
    mat_match = re.search(
        r'(?:material|spec|metallurgy|shell\s*material)[\s:=]*([A-Za-z0-9\.\-\+ ]{2,30})',
        text, re.IGNORECASE
    )
    if mat_match:
        mat_raw = mat_match.group(1).strip()
        mat_clean = mat_raw.lower()
        matched = any(alloy in mat_clean for alloy in KNOWN_ALLOYS)
        extracted["material"] = mat_raw
        if matched:
            score_parts += 0.15
        else:
            warnings.append(f"UNRECOGNIZED_MATERIAL: Material '{mat_raw}' not found in standard alloy whitelist.")
            score_parts += 0.05

    # 6. Inside Radius
    r_match = re.search(
        r'(?:inside\s*radius|radius|r_inner)[\s:=]*([0-9]+\.?[0-9]*)\s*(?:mm)?',
        text, re.IGNORECASE
    )
    if r_match:
        try:
            extracted["inside_radius_mm"] = float(r_match.group(1))
            score_parts += 0.10
        except ValueError:
            pass

    # 7. Allowable Stress
    s_match = re.search(
        r'(?:allowable\s*stress|stress|s_allow)[\s:=]*([0-9]+\.?[0-9]*)\s*(?:mpa)?',
        text, re.IGNORECASE
    )
    if s_match:
        try:
            extracted["allowable_stress_mpa"] = float(s_match.group(1))
            score_parts += 0.10
        except ValueError:
            pass

    # 8. Joint Efficiency
    e_match = re.search(
        r'(?:joint\s*efficiency|efficiency)[\s:=]*([0-9]+\.?[0-9]*)',
        text, re.IGNORECASE
    )
    if e_match:
        try:
            extracted["joint_efficiency"] = float(e_match.group(1))
        except ValueError:
            pass

    # 9. Corrosion Allowance
    ca_match = re.search(
        r'(?:corrosion\s*allowance|ca)[\s:=]*([0-9]+\.?[0-9]*)\s*(?:mm)?',
        text, re.IGNORECASE
    )
    if ca_match:
        try:
            extracted["corrosion_allowance_mm"] = float(ca_match.group(1))
        except ValueError:
            pass

    # 10. PAC Reference & Validity
    pac_match = re.search(r'\b(PAC-[A-Za-z0-9\-]+)\b', text, re.IGNORECASE)
    if pac_match:
        extracted["pac_certificate_ref"] = pac_match.group(1).upper()

    val_match = re.search(r'(?:valid\s*until|expiry)[\s:=]*(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
    if val_match:
        extracted["pac_valid_until"] = val_match.group(1)

    cost_match = re.search(r'(?:estimated\s*cost\s*inr|cost\s*inr)[\s:=]*([0-9]+\.?[0-9]*)', text, re.IGNORECASE)
    if cost_match:
        try:
            extracted["estimated_cost_inr"] = float(cost_match.group(1))
        except ValueError:
            pass

    confidence_score = round(min(1.0, score_parts), 2)
    return extracted, warnings, confidence_score


def extract_inspection_parameters(
    file_path: Optional[str] = None,
    raw_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parses document multimodal content or raw inspection text, extracts engineering inspection parameters,
    and applies confidence gating.
    """
    if file_path:
        safe_path = _validate_safe_path(file_path)
        parsed_doc = parse_file_multimodal(safe_path)

        # Aggregate all text sources: extracted text chunks and OCR image text
        text_chunks = [item.get("text", "") for item in parsed_doc.get("texts", [])]
        for img_meta in parsed_doc.get("images", []):
            if "ocr_text" in img_meta and img_meta["ocr_text"]:
                text_chunks.append(img_meta["ocr_text"])

        full_text = "\n".join(text_chunks)
        file_name = safe_path.name
    elif raw_text:
        full_text = raw_text
        file_name = "direct_text_query"
    else:
        raise ValueError("Either file_path or raw_text must be provided to extract_inspection_parameters.")

    extracted, warnings, confidence = extract_parameters_from_text(full_text)

    # Mandatory Confidence Gating (< 0.85 requires human review)
    requires_confirmation = (
        confidence < 0.85 
        or any("OUT_OF_BOUNDS" in w or "UNREALISTIC" in w or "ANOMALY" in w for w in warnings)
        or "measured_thickness_mm" not in extracted
    )
    status = "ACTION_REQUIRED_UNVERIFIED_DATA" if requires_confirmation else "VERIFIED_CONFIDENT"

    return {
        "file_name": file_name,
        "extracted_parameters": extracted,
        "confidence_score": confidence,
        "status": status,
        "requires_human_confirmation": requires_confirmation,
        "validation_warnings": warnings,
    }


try:
    from langchain_core.tools import tool

    @tool
    def inspection_extractor_tool(file_path: str) -> str:
        """
        Extracts equipment tag, measured thickness, corrosion rate, design pressure,
        and metallurgy from field inspection reports (PDF, DOCX, XLSX, CSV, images).
        Enforces physical sanity checks and confidence gating (score < 0.85 requires review).
        
        Args:
            file_path: Path to inspection report document or image within workspace [REQUIRED]
        """
        start_time = time.time()
        try:
            res = extract_inspection_parameters(file_path)
            duration_ms = (time.time() - start_time) * 1000

            append_audit_event(
                tool_name="inspection_extractor_tool",
                inputs={"file_path": file_path},
                outputs=res,
                status="SUCCESS",
                duration_ms=duration_ms,
                caller="inspection_extractor_tool"
            )

            params = res["extracted_parameters"]
            warn_str = "\n- Warnings:\n" + "\n".join(f"  * {w}" for w in res["validation_warnings"]) if res["validation_warnings"] else "\n- Warnings: None (Clean physical validation)"

            return (
                f"Inspection Parameter Extraction Summary for {res['file_name']}:\n"
                f"- Pipeline Status: {res['status']}\n"
                f"- Confidence Score: {res['confidence_score']} / 1.0\n"
                f"- Human Confirmation Required: {'YES (Hold pipeline)' if res['requires_human_confirmation'] else 'NO (Safe to proceed)'}\n"
                f"- Extracted Tag: {params.get('equipment_id', 'NOT_FOUND')}\n"
                f"- Measured Thickness: {params.get('measured_thickness_mm', 'NOT_FOUND')} mm\n"
                f"- Corrosion Rate: {params.get('corrosion_rate_mm_yr', 'NOT_FOUND')} mm/yr\n"
                f"- Design Pressure: {params.get('design_pressure_mpa', 'NOT_FOUND')} MPa\n"
                f"- Metallurgy: {params.get('material', 'NOT_FOUND')}"
                f"{warn_str}"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            append_audit_event(
                tool_name="inspection_extractor_tool",
                inputs={"file_path": file_path},
                outputs={"error": str(e)},
                status="FAILURE",
                duration_ms=duration_ms,
                caller="inspection_extractor_tool"
            )
            return f"Extraction Error: {str(e)}"

except ImportError:
    inspection_extractor_tool = None
