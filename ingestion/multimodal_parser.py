"""
ingestion/multimodal_parser.py
Universal Multimodal Ingestion & Document Parser for AegisForge-AI.
Extracts structured text chunks and embedded images/diagrams from:
- PDF (.pdf) using PyMuPDF (fitz)
- Word (.docx) using python-docx
- Plain Text & Markdown (.txt, .md, .json)
- Standalone Images (.png, .jpg, .jpeg, .tiff, .bmp)

Enriches every extracted item with domain-specific keyword tags (ASME, CVC, equipment tags,
defect types, materials) and OCR text for optimized Qdrant payload retrieval.
"""

import os
import re
import sys
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
from PIL import Image

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import EXTRACTED_IMAGES_DIR, logger


# Domain regex patterns for automatic keyword tagging
KEYWORD_PATTERNS = {
    "equipment_id": re.compile(r"\b(?:\d{1,3}-[A-Z]{1,3}-\d{2,4}[A-Z]?|[A-Z]{1,3}-\d{3,4})\b", re.IGNORECASE),
    "codes_standards": re.compile(r"\b(?:ASME(?:\s+(?:Sec(?:tion)?\s+VIII|Div\s+1|UG-27))?|API\s+510|CVC(?:\s+Circular(?:\s+No\.?)?\s+\d+/\d+/\d+)?|DOP(?:\s+Clause)?\s+\d+\.?\d*|OISD|IBR|ASTM)\b", re.IGNORECASE),
    "defect_and_mechanics": re.compile(r"\b(?:corrosion(?:-erosion)?|wall\s+thinning|pitting|crack(?:ing)?|hydrogen\s+blistering|knuckle|bottom\s+head|shell|nozzle|weld\s+overlay|derated|breach|t_min|remaining\s+life|flaw)\b", re.IGNORECASE),
    "ndt_methods": re.compile(r"\b(?:ultrasonic|UT|NDT|A-scan|C-scan|radiography|eddy\s+current|magnetic\s+particle|visual\s+inspection|dye\s+penetrant)\b", re.IGNORECASE),
    "materials_and_pressure": re.compile(r"\b(?:347\s*SS|SA-516|carbon\s+steel|stainless\s+steel|hydrocracker|sour\s+service|MAWP|design\s+pressure|barg|MPa|mm/year|mm/yr)\b", re.IGNORECASE),
}


def extract_keywords_from_text(text: str, custom_keywords: Optional[List[str]] = None) -> List[str]:
    """
    Scans text for industrial domain keywords, equipment tags, and standards,
    returning a deduplicated list of lowercase keyword tags.
    """
    if not text:
        return custom_keywords or []

    found = set()
    if custom_keywords:
        for k in custom_keywords:
            if k and isinstance(k, str):
                found.add(k.strip().lower())

    for category, pattern in KEYWORD_PATTERNS.items():
        matches = pattern.findall(text)
        for m in matches:
            cleaned = re.sub(r"\s+", " ", m.strip()).lower()
            if len(cleaned) >= 2:
                found.add(cleaned)

    # Basic token filtering
    normalized = sorted(list(found))
    return normalized


def extract_ocr_from_image(image_path: Path) -> str:
    """
    Attempts to run local EasyOCR on an image to extract text or labels (e.g. gauge readings,
    schematic tags). Returns an empty string if OCR fails or finds nothing.
    """
    try:
        import easyocr
        from config.settings import EASYOCR_DIR
        # Run CPU OCR
        reader = easyocr.Reader(['en'], gpu=False, model_storage_directory=str(EASYOCR_DIR), verbose=False)
        results = reader.readtext(str(image_path), detail=0)
        return " ".join(results).strip()
    except Exception as e:
        logger.debug(f"EasyOCR skipped or unavailable for {image_path.name}: {e}")
        return ""


def extract_from_pdf(
    pdf_path: Path,
    output_image_dir: Path = EXTRACTED_IMAGES_DIR,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts text chunks and embedded images from a PDF file using PyMuPDF (fitz).
    Returns (text_chunks, image_items).
    """
    import fitz  # PyMuPDF

    output_image_dir.mkdir(parents=True, exist_ok=True)
    text_chunks = []
    image_items = []

    doc = fitz.open(pdf_path)
    file_stem = pdf_path.stem

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_num = page_idx + 1

        # 1. Extract digital text
        text = page.get_text("text").strip()
        if text:
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
            if not paragraphs:
                paragraphs = [text]

            for chunk_idx, para in enumerate(paragraphs, 1):
                keywords = extract_keywords_from_text(para)
                text_chunks.append({
                    "id": f"{file_stem}_p{page_num}_c{chunk_idx}",
                    "content_type": "text",
                    "text": para,
                    "keywords": keywords,
                    "source": pdf_path.name,
                    "page": page_num,
                    "chunk_index": chunk_idx,
                })
        else:
            # Scanned page fallback: render page to image and extract OCR text
            pix = page.get_pixmap(dpi=150)
            scanned_img_name = f"{file_stem}_p{page_num}_scanned.png"
            scanned_img_path = output_image_dir / scanned_img_name
            pix.save(str(scanned_img_path))
            
            ocr_text = extract_ocr_from_image(scanned_img_path)
            keywords = extract_keywords_from_text(ocr_text)
            
            if ocr_text:
                text_chunks.append({
                    "id": f"{file_stem}_p{page_num}_ocr",
                    "content_type": "text",
                    "text": ocr_text,
                    "keywords": keywords,
                    "source": pdf_path.name,
                    "page": page_num,
                    "chunk_index": 1,
                    "is_ocr": True,
                })
            
            image_items.append({
                "id": f"{file_stem}_p{page_num}_img_scanned",
                "content_type": "image",
                "image_path": str(scanned_img_path),
                "ocr_text": ocr_text,
                "keywords": keywords,
                "source": pdf_path.name,
                "page": page_num,
                "caption": f"Scanned page {page_num} of {pdf_path.name}",
            })

        # 2. Extract embedded images from this page
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list, 1):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            # Filter out tiny icon artifacts (less than 64x64)
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)
            if width < 64 or height < 64:
                continue

            saved_img_name = f"{file_stem}_p{page_num}_img{img_idx}.{image_ext}"
            saved_img_path = output_image_dir / saved_img_name
            with open(saved_img_path, "wb") as f:
                f.write(image_bytes)

            # Extract any text on this image
            img_ocr = extract_ocr_from_image(saved_img_path)
            # Combine page keywords with image OCR keywords
            img_keywords = extract_keywords_from_text(f"{text} {img_ocr}")

            image_items.append({
                "id": f"{file_stem}_p{page_num}_img{img_idx}",
                "content_type": "image",
                "image_path": str(saved_img_path),
                "ocr_text": img_ocr,
                "keywords": img_keywords,
                "source": pdf_path.name,
                "page": page_num,
                "caption": f"Figure {img_idx} on page {page_num} of {pdf_path.name}",
            })

    doc.close()
    return text_chunks, image_items


def extract_from_docx(
    docx_path: Path,
    output_image_dir: Path = EXTRACTED_IMAGES_DIR,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extracts text paragraphs, tables, and embedded images from a .docx file.
    """
    import docx

    output_image_dir.mkdir(parents=True, exist_ok=True)
    text_chunks = []
    image_items = []
    file_stem = docx_path.stem

    try:
        doc = docx.Document(docx_path)

        # 1. Paragraphs & Tables
        chunk_counter = 1
        for p in doc.paragraphs:
            p_text = p.text.strip()
            if len(p_text) > 30:
                keywords = extract_keywords_from_text(p_text)
                text_chunks.append({
                    "id": f"{file_stem}_c{chunk_counter}",
                    "content_type": "text",
                    "text": p_text,
                    "keywords": keywords,
                    "source": docx_path.name,
                    "page": 1,
                    "chunk_index": chunk_counter,
                })
                chunk_counter += 1

        for tbl_idx, table in enumerate(doc.tables, 1):
            rows_data = []
            for row in table.rows:
                row_vals = [cell.text.strip() for cell in row.cells]
                rows_data.append(" | ".join(row_vals))
            table_str = "\n".join(rows_data).strip()
            if len(table_str) > 20:
                keywords = extract_keywords_from_text(table_str)
                text_chunks.append({
                    "id": f"{file_stem}_tbl{tbl_idx}",
                    "content_type": "text",
                    "text": table_str,
                    "keywords": keywords,
                    "source": docx_path.name,
                    "page": 1,
                    "chunk_index": chunk_counter,
                    "is_table": True,
                })
                chunk_counter += 1

        # 2. Extract embedded images from docx relationship parts
        img_counter = 1
        for rel in doc.part.related_parts.values():
            if "image" in rel.content_type:
                try:
                    ext = rel.content_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"
                    img_name = f"{file_stem}_img{img_counter}.{ext}"
                    img_path = output_image_dir / img_name
                    with open(img_path, "wb") as f:
                        f.write(rel.blob)

                    with Image.open(img_path) as im:
                        w, h = im.size
                    if w < 64 or h < 64:
                        if img_path.exists():
                            img_path.unlink()
                        continue

                    ocr_text = extract_ocr_from_image(img_path)
                    keywords = extract_keywords_from_text(f"{docx_path.name} {ocr_text}")

                    image_items.append({
                        "id": f"{file_stem}_img{img_counter}",
                        "content_type": "image",
                        "image_path": str(img_path),
                        "ocr_text": ocr_text,
                        "keywords": keywords,
                        "source": docx_path.name,
                        "page": 1,
                        "caption": f"Embedded figure in {docx_path.name}",
                    })
                    img_counter += 1
                except Exception as e:
                    logger.debug(f"Could not extract docx image part: {e}")

    except Exception as docx_err:
        logger.warning(f"Standard python-docx parser encountered error ({docx_err}). Using raw zip XML fallback for {docx_path.name}")
        # Fallback: unzip and parse raw text and images directly
        import zipfile
        try:
            with zipfile.ZipFile(docx_path, 'r') as z:
                # Extract text from word/document.xml
                if 'word/document.xml' in z.namelist():
                    raw_xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
                    # Match all text inside <w:t> tags
                    paragraphs_xml = re.findall(r'<w:p[\s>].*?</w:p>', raw_xml, flags=re.DOTALL)
                    chunk_counter = 1
                    for p_xml in paragraphs_xml:
                        texts_in_p = re.findall(r'<w:t[^>]*>(.*?)</w:t>', p_xml, flags=re.DOTALL)
                        clean_p = " ".join(texts_in_p).strip()
                        if len(clean_p) > 30:
                            keywords = extract_keywords_from_text(clean_p)
                            text_chunks.append({
                                "id": f"{file_stem}_c{chunk_counter}",
                                "content_type": "text",
                                "text": clean_p,
                                "keywords": keywords,
                                "source": docx_path.name,
                                "page": 1,
                                "chunk_index": chunk_counter,
                            })
                            chunk_counter += 1

                # Extract images from word/media/
                img_counter = 1
                for fname in z.namelist():
                    if fname.startswith("word/media/"):
                        img_data = z.read(fname)
                        ext = Path(fname).suffix.lower()
                        img_name = f"{file_stem}_img{img_counter}{ext}"
                        img_path = output_image_dir / img_name
                        with open(img_path, "wb") as f:
                            f.write(img_data)
                        ocr_text = extract_ocr_from_image(img_path)
                        keywords = extract_keywords_from_text(f"{docx_path.name} {ocr_text}")
                        image_items.append({
                            "id": f"{file_stem}_img{img_counter}",
                            "content_type": "image",
                            "image_path": str(img_path),
                            "ocr_text": ocr_text,
                            "keywords": keywords,
                            "source": docx_path.name,
                            "page": 1,
                            "caption": f"Embedded figure in {docx_path.name}",
                        })
                        img_counter += 1
        except Exception as zip_err:
            logger.error(f"Failed zip XML fallback for {docx_path.name}: {zip_err}")

    return text_chunks, image_items


def extract_from_image_file(
    image_path: Path,
    custom_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Extracts metadata, runs OCR, and extracts keyword tags for a standalone image file
    (e.g., P&ID diagram, corrosion photo, ultrasonic scan).
    """
    ocr_text = extract_ocr_from_image(image_path)
    combined_text = f"{image_path.stem} {ocr_text}"
    keywords = extract_keywords_from_text(combined_text, custom_keywords=custom_keywords)

    return {
        "id": f"img_{image_path.stem}_{uuid.uuid4().hex[:6]}",
        "content_type": "image",
        "image_path": str(image_path),
        "ocr_text": ocr_text,
        "keywords": keywords,
        "source": image_path.name,
        "page": 1,
        "caption": f"Industrial visual asset: {image_path.name}",
    }


def extract_from_text_file(
    file_path: Path,
) -> List[Dict[str, Any]]:
    """
    Extracts coherent text chunks from .txt, .md, or .json files.
    """
    text_chunks = []
    file_stem = file_path.stem
    content = file_path.read_text(encoding="utf-8", errors="replace").strip()

    if file_path.suffix.lower() == ".json":
        try:
            data = json.loads(content)
            # Pretty print JSON structure into coherent readable sections
            if isinstance(data, list):
                for idx, item in enumerate(data, 1):
                    item_str = json.dumps(item, indent=2)
                    keywords = extract_keywords_from_text(item_str)
                    text_chunks.append({
                        "id": f"{file_stem}_item{idx}",
                        "content_type": "text",
                        "text": item_str,
                        "keywords": keywords,
                        "source": file_path.name,
                        "page": 1,
                        "chunk_index": idx,
                    })
            elif isinstance(data, dict):
                for k, v in data.items():
                    sec_str = f"[{k}]\n{json.dumps(v, indent=2)}"
                    keywords = extract_keywords_from_text(sec_str)
                    text_chunks.append({
                        "id": f"{file_stem}_{k[:20]}",
                        "content_type": "text",
                        "text": sec_str,
                        "keywords": keywords,
                        "source": file_path.name,
                        "page": 1,
                        "chunk_index": 1,
                    })
            return text_chunks
        except Exception:
            pass

    # For markdown or txt, split by double newlines or headers
    paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
    if not paragraphs:
        paragraphs = [content]

    for idx, para in enumerate(paragraphs, 1):
        keywords = extract_keywords_from_text(para)
        text_chunks.append({
            "id": f"{file_stem}_c{idx}",
            "content_type": "text",
            "text": para,
            "keywords": keywords,
            "source": file_path.name,
            "page": 1,
            "chunk_index": idx,
        })

    return text_chunks


def extract_from_csv(
    csv_path: Path,
    rows_per_chunk: int = 10,
) -> List[Dict[str, Any]]:
    """
    Parses a CSV file preserving tabular column headers and structured row values.
    Groups rows into semantically coherent tabular chunks for vector indexing.
    """
    import csv

    text_chunks = []
    file_stem = csv_path.stem

    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            rows = [r for r in reader if any(cell.strip() for cell in r)]

        if not rows:
            return []

        header = rows[0]
        data_rows = rows[1:]

        if not data_rows:
            # Single row or header only
            header_str = " | ".join(header)
            return [{
                "id": f"{file_stem}_header",
                "content_type": "text",
                "text": f"Table Columns in {csv_path.name}: {header_str}",
                "keywords": extract_keywords_from_text(header_str),
                "source": csv_path.name,
                "page": 1,
                "chunk_index": 1,
                "is_table": True,
            }]

        chunk_counter = 1
        for i in range(0, len(data_rows), rows_per_chunk):
            batch = data_rows[i : i + rows_per_chunk]
            lines = [f"[Spreadsheet Table: {csv_path.name} | Rows {i+1}-{i+len(batch)}]"]
            for row_idx, r in enumerate(batch, start=i + 1):
                paired = [f"{h.strip()}: {val.strip()}" for h, val in zip(header, r) if h.strip() and val.strip()]
                lines.append(f"Row {row_idx}: " + " | ".join(paired))

            chunk_text = "\n".join(lines)
            keywords = extract_keywords_from_text(chunk_text)

            text_chunks.append({
                "id": f"{file_stem}_chunk{chunk_counter}",
                "content_type": "text",
                "text": chunk_text,
                "keywords": keywords,
                "source": csv_path.name,
                "page": 1,
                "chunk_index": chunk_counter,
                "is_table": True,
            })
            chunk_counter += 1

    except Exception as e:
        logger.error(f"Error extracting CSV from {csv_path.name}: {e}")

    return text_chunks


def extract_from_excel(
    excel_path: Path,
    output_image_dir: Path = EXTRACTED_IMAGES_DIR,
    rows_per_chunk: int = 10,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses multi-sheet Excel workbooks (.xlsx, .xls) extracting structured rows
    with column headers, and saves any embedded charts or images.
    """
    import openpyxl

    output_image_dir.mkdir(parents=True, exist_ok=True)
    text_chunks = []
    image_items = []
    file_stem = excel_path.stem

    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
    except Exception as e:
        logger.error(f"Failed to load Excel workbook {excel_path.name}: {e}")
        return [], []

    chunk_counter = 1
    for sheet_idx, sheet_name in enumerate(wb.sheetnames, 1):
        ws = wb[sheet_name]
        all_rows = list(ws.iter_rows(values_only=True))

        # Filter empty rows
        non_empty_rows = [r for r in all_rows if any(cell is not None and str(cell).strip() != "" for cell in r)]
        if not non_empty_rows:
            continue

        # Header detection: first non-empty row
        raw_header = non_empty_rows[0]
        headers = [str(c).strip() if c is not None else f"Col_{i+1}" for i, c in enumerate(raw_header)]
        data_rows = non_empty_rows[1:]

        if not data_rows:
            header_str = f"[Excel Sheet: {sheet_name} in {excel_path.name}]\nColumns: " + " | ".join(headers)
            text_chunks.append({
                "id": f"{file_stem}_s{sheet_idx}_h",
                "content_type": "text",
                "text": header_str,
                "keywords": extract_keywords_from_text(header_str),
                "source": excel_path.name,
                "page": sheet_idx,
                "chunk_index": chunk_counter,
                "is_table": True,
            })
            chunk_counter += 1
            continue

        # Chunk rows in batches
        for i in range(0, len(data_rows), rows_per_chunk):
            batch = data_rows[i : i + rows_per_chunk]
            lines = [f"[Excel Workbook: {excel_path.name} | Sheet: '{sheet_name}' | Rows {i+1}-{i+len(batch)}]"]
            for row_num, r in enumerate(batch, start=i + 1):
                paired = [f"{h}: {str(val).strip()}" for h, val in zip(headers, r) if val is not None and str(val).strip() != ""]
                if paired:
                    lines.append(f"Row {row_num}: " + " | ".join(paired))

            chunk_text = "\n".join(lines)
            keywords = extract_keywords_from_text(chunk_text)

            text_chunks.append({
                "id": f"{file_stem}_s{sheet_idx}_c{chunk_counter}",
                "content_type": "text",
                "text": chunk_text,
                "keywords": keywords,
                "source": excel_path.name,
                "page": sheet_idx,
                "chunk_index": chunk_counter,
                "is_table": True,
            })
            chunk_counter += 1

        # Extract embedded images/drawings from sheet if any
        if hasattr(ws, "_images"):
            img_idx = 1
            for img in getattr(ws, "_images", []):
                try:
                    img_name = f"{file_stem}_s{sheet_idx}_img{img_idx}.png"
                    img_path = output_image_dir / img_name
                    with open(img_path, "wb") as f:
                        f.write(img._data())

                    ocr_text = extract_ocr_from_image(img_path)
                    keywords = extract_keywords_from_text(f"{excel_path.name} {sheet_name} {ocr_text}")

                    image_items.append({
                        "id": f"{file_stem}_s{sheet_idx}_img{img_idx}",
                        "content_type": "image",
                        "image_path": str(img_path),
                        "ocr_text": ocr_text,
                        "keywords": keywords,
                        "source": excel_path.name,
                        "page": sheet_idx,
                        "caption": f"Embedded chart/image in sheet '{sheet_name}' of {excel_path.name}",
                    })
                    img_idx += 1
                except Exception as img_err:
                    logger.debug(f"Could not extract excel image: {img_err}")

    wb.close()
    return text_chunks, image_items


def parse_file_multimodal(
    file_path: Union[str, Path],
    output_image_dir: Path = EXTRACTED_IMAGES_DIR,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Universal dispatcher that parses any file format into structured texts and images.
    Supports:
    - PDF (.pdf)
    - Word (.docx, .doc)
    - Excel Workbooks (.xlsx, .xls)
    - CSV Tables (.csv)
    - Images (.png, .jpg, .jpeg, .bmp, .tiff, .webp)
    - Text & Data (.txt, .md, .json, .py)
    Returns: {"texts": [...], "images": [...]}
    """
    path = Path(file_path).resolve()
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return {"texts": [], "images": []}

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        texts, images = extract_from_pdf(path, output_image_dir)
        return {"texts": texts, "images": images}
    elif suffix in [".docx", ".doc"]:
        texts, images = extract_from_docx(path, output_image_dir)
        return {"texts": texts, "images": images}
    elif suffix in [".xlsx", ".xls"]:
        texts, images = extract_from_excel(path, output_image_dir)
        return {"texts": texts, "images": images}
    elif suffix == ".csv":
        texts = extract_from_csv(path)
        return {"texts": texts, "images": []}
    elif suffix in [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]:
        img_item = extract_from_image_file(path)
        return {"texts": [], "images": [img_item]}
    elif suffix in [".txt", ".md", ".json", ".py"]:
        texts = extract_from_text_file(path)
        return {"texts": texts, "images": []}
    else:
        logger.info(f"Unsupported extension {suffix} for {path.name}, attempting plain text read.")
        texts = extract_from_text_file(path)
        return {"texts": texts, "images": []}

