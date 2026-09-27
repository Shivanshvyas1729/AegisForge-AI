from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

try:
    import easyocr
except ImportError as exc:  # pragma: no cover
    easyocr = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "model_pool" / "easyocr"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"


@lru_cache(maxsize=1)
def get_reader():
    if easyocr is None:
        raise ImportError(
            "easyocr is required. Install it in the project environment before using this tool."
        ) from _IMPORT_ERROR

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    return easyocr.Reader(["en"], gpu=False, model_storage_directory=str(MODEL_DIR))


def normalize_whitespace(value: Optional[str]) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def fix_ocr_common_errors(value: Optional[str]) -> str:
    if value is None:
        return ""

    value = re.sub(r"(?i)\bCorrcsion\b", "Corrosion", value)
    value = re.sub(r"(?i)\bPate\b", "Rate", value)
    value = re.sub(r"(?i)\bmmyr\b", "mm/yr", value)
    value = re.sub(r"(?i)\bSeSeparator\b", "Separator", value)
    value = re.sub(r"(?i)\bDruM\b", "Drum", value)
    value = re.sub(r"(?i)\bI(?=\d)", "1", value)
    value = re.sub(r"(?i)(?<=\d|[A-Z])I(?=[A-Z])", "1", value)
    value = re.sub(r"(?i)\bL(?=\d)", "1", value)

    return normalize_whitespace(value).strip(" :;,.")


def extract_ocr_text(file_path: str):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    reader = get_reader()
    results = reader.readtext(str(path), detail=1, paragraph=False)

    detections: List[Dict[str, Any]] = []
    lines: List[str] = []

    for item in results:
        text = str(item[1]).strip()
        conf = float(item[2]) if len(item) > 2 else 0.0
        if text:
            detections.append({"text": text, "confidence": conf})
            lines.append(text)

    return {
        "detections": detections,
        "raw_ocr_text": "\n".join(lines),
    }


def extract_equipment_id(text: str):
    match = re.search(
        r"(?is)(?:equipment\s*id|eq\s*id)\s*[:\-]?\s*([A-Z0-9]+(?:[-/][A-Z0-9]+)+)",
        text,
    )
    if not match:
        return None

    value = fix_ocr_common_errors(match.group(1))
    return value if re.search(r"\d", value) else None


def extract_equipment_name(text: str):
    match = re.search(
        r"(?is)(?:equipment\s*name)\s*[:\-]?\s*(.+?)(?=(?:\bmaterial\b|\bdesign\s*pressure\b|\bmeasured\s*thickness\b|\bcorrosion\s*rate\b|$))",
        text,
    )
    if not match:
        return None

    value = fix_ocr_common_errors(match.group(1))
    return value or None


def extract_material(text: str):
    match = re.search(
        r"(?is)(?:material)\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9.\-/ ]+)",
        text,
    )
    if not match:
        return None

    value = fix_ocr_common_errors(match.group(1))
    return value or None


def convert_pressure_to_mpa(value: float, unit: str) -> Optional[float]:
    unit = (unit or "").lower()
    if unit in {"mpa", "mpa."}:
        return value
    if unit == "bar":
        return value * 0.1
    if unit == "psi":
        return value * 0.00689476
    return None


def extract_design_pressure_mpa(text: str):
    match = re.search(
        r"(?is)(?:design\s*pressure|pressure)\s*[:\-]?\s*([-+]?\d+(?:\.\d+)?)\s*(MPa|bar|psi)?",
        text,
    )
    if not match:
        return None

    value = float(match.group(1))
    unit = (match.group(2) or "MPa").lower()
    converted = convert_pressure_to_mpa(value, unit)
    return round(converted, 3) if converted is not None else None


def extract_measured_thickness_mm(text: str):
    match = re.search(
        r"(?is)(?:measured\s*thickness)\s*[:\-]?\s*([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m)?",
        text,
    )
    if not match:
        return None

    value = float(match.group(1))
    unit = (match.group(2) or "mm").lower()
    if unit == "cm":
        value *= 10
    elif unit == "m":
        value *= 1000
    return round(value, 3)


def extract_corrosion_rate_mm_yr(text: str):
    match = re.search(
        r"(?is)(?:corrosion\s*rate|corrcsion\s*pate)\s*[:\-.]?\s*([-+]?\d+(?:\.\d+)?)\s*(?:mm\s*(?:/|per)?\s*yr|mmyr|mm\s*yr|mm/yr)?",
        text,
    )
    if not match:
        return None
    return round(float(match.group(1)), 3)


def validate_output(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    validated = dict(data)

    for key in ["equipment_id", "equipment_name", "material"]:
        if validated.get(key) in ("", "N/A", "None"):
            validated[key] = None

    pressure = validated.get("design_pressure_mpa")
    if pressure is None or not isinstance(pressure, (int, float)) or pressure <= 0:
        validated["design_pressure_mpa"] = None

    thickness = validated.get("measured_thickness_mm")
    if thickness is None or not isinstance(thickness, (int, float)) or thickness <= 0:
        validated["measured_thickness_mm"] = None

    corrosion = validated.get("corrosion_rate_mm_yr")
    if corrosion is None or not isinstance(corrosion, (int, float)) or corrosion < 0:
        validated["corrosion_rate_mm_yr"] = None

    return validated


def calculate_confidence(ocr_results):
    if not ocr_results:
        return 0.0

    scores = [
        float(item.get("confidence", 0.0))
        for item in ocr_results
        if isinstance(item, dict)
    ]
    if not scores:
        return 0.0

    return round(max(0.0, min(1.0, sum(scores) / len(scores))), 2)


def ocr_extractor_tool(file_path: str) -> dict:
    result = {
        "equipment_id": None,
        "equipment_name": None,
        "material": None,
        "design_pressure_mpa": None,
        "measured_thickness_mm": None,
        "corrosion_rate_mm_yr": None,
        "raw_ocr_text": "",
        "confidence_score": 0.0,
    }

    path = Path(file_path)
    if not path.exists():
        result["raw_ocr_text"] = f"File not found: {file_path}"
        return result

    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        result["raw_ocr_text"] = f"Unsupported file type: {path.suffix}"
        return result

    try:
        ocr_output = extract_ocr_text(str(path))
        raw_text = ocr_output.get("raw_ocr_text", "")

        result["raw_ocr_text"] = raw_text
        result["equipment_id"] = extract_equipment_id(raw_text)
        result["equipment_name"] = extract_equipment_name(raw_text)
        result["material"] = extract_material(raw_text)
        result["design_pressure_mpa"] = extract_design_pressure_mpa(raw_text)
        result["measured_thickness_mm"] = extract_measured_thickness_mm(raw_text)
        result["corrosion_rate_mm_yr"] = extract_corrosion_rate_mm_yr(raw_text)

        result = validate_output(result)
        result["confidence_score"] = calculate_confidence(ocr_output.get("detections", []))
        return result
    except Exception as exc:
        result["raw_ocr_text"] = f"OCR processing failed: {exc}"
        return result


def create_synthetic_inspection_image(
    path: str,
    pressure_text: str = "14.5 MPa",
    missing_field: Optional[str] = None,
):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "INSPECTION REPORT",
        "",
        "Equipment ID: 11-V-102",
        "Equipment Name: HP Separator Drum",
        "Material: 2.25Cr-1Mo",
        f"Design Pressure: {pressure_text}",
        "Measured Thickness: 138.2 mm",
        "Corrosion Rate: 0.75 mm/yr",
    ]

    if missing_field:
        lines = [line for line in lines if not line.lower().startswith(missing_field.lower())]

    image = Image.new("RGB", (2000, 1200), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 54)

    y = 60
    for line in lines:
        draw.text((90, y), line, fill="black", font=font, stroke_width=1, stroke_fill="black")
        y += 90

    image.save(path, format="PNG")
    return str(path)


if __name__ == "__main__":
    sample_dir = SAMPLE_DATA_DIR
    normal_image = create_synthetic_inspection_image(sample_dir / "inspection_report_test.png")
    missing_field_image = create_synthetic_inspection_image(
        sample_dir / "inspection_report_missing_field.png",
        missing_field="Equipment Name",
    )
    pressure_bar_image = create_synthetic_inspection_image(
        sample_dir / "inspection_report_pressure_bar.png",
        pressure_text="145 bar",
    )

    print("NORMAL:")
    print(ocr_extractor_tool(normal_image))
    print("\nMISSING:")
    print(ocr_extractor_tool(missing_field_image))
    print("\nBAR:")
    print(ocr_extractor_tool(pressure_bar_image))
