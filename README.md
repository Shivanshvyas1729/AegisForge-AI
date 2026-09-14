# AegisForge-AI: Sovereign Air-Gapped AI Workbench for PSUs & Critical Infrastructure

> **Self-hosted, air-gapped agentic AI workbench running entirely on on-premises GPU infrastructure with zero data leakage.**

---

## Executive Summary
Refineries, Public Sector Undertakings (PSUs), defence-linked manufacturing units, and government departments handle highly confidential knowledge work daily:
- **Approval notes & Note for Board**
- **Board presentations & Capex strategies**
- **Engineering calculations (ASME, API, TEMA codes)**
- **Internal automation scripts & SCADA tools**
- **Review of scanned drawings (P&ID blueprints, isometrics)**
- **Statutory inspection reports (NDT, ultrasonic thickness surveys)**

None of this sensitive IP can be routed through public cloud AI models (Claude, OpenAI, Codex). **AegisForge-AI** provides an industrial-grade, self-hosted, multi-model AI workbench that dynamically routes requests across specialized open-weight models (reasoning, coding, vision, generalist) and executes agentic tasks with full on-premises data residency.

---

## Repository Structure

```
AegisForge-AI/
├── backend/                  # Core Python backend, API routes, and agent orchestrators
│   ├── experiments/          # Interactive setup notebooks (basic_setup1.ipynb)
│   ├── main.py               # Entry point
│   ├── pyproject.toml        # Build configuration
│   └── requirements.txt      # Python dependencies
│
├── sample_data/              # Domain-curated industrial benchmark & test datasets
│   ├── 01_approval_notes/    # PSU Note for Approval (NFA) formats (.md, .json, .docx)
│   ├── 02_board_presentations/# Executive board deck scripts & metadata (.md, .json, .pptx)
│   ├── 03_engineering_calculations/# ASME Sec VIII & Darcy-Weisbach calculations (.py, .csv, .md, .xlsx)
│   ├── 04_internal_tools_code/# SCADA Modbus parser, airgap runner & SQL schema (.py, .sh, .sql, .json)
│   ├── 05_scanned_drawings_pid/# Vector P&ID and isometric blueprints (.svg, .json, .md)
│   ├── 06_inspection_reports/# Ultrasonic NDT surveys & raw field OCR logs (.md, .txt, .json, .docx)
│   ├── generate_sample_documents.py # Pure Python Office OpenXML generator (.docx, .xlsx, .pptx)
│   ├── build_samples.bat     # One-click generator script
│   └── README.md             # Detailed dataset taxonomy and test matrix
│
└── README.md                 # Project root documentation
```

---

## Key Capabilities & Benchmark Scenarios

1. **Dynamic Open-Weight Model Selection:** Automatically detects task modality and routes coding to coder models (e.g. Qwen-2.5-Coder), calculations to reasoning models (e.g. DeepSeek-R1), and P&ID drawings to vision models (e.g. Qwen2-VL).
2. **Real Deliverable Generation:** Directly produces native Office OpenXML deliverables (`.docx` approval notes, `.xlsx` calculation workbooks, `.pptx` presentations) rather than plain text chat answers.
3. **End-to-End Agentic Task:** Ingests raw noisy OCR field inspection reports (`field_inspector_raw_ocr_log.txt`), performs defect analysis, checks code minimum thickness ($t_{\text{min}}$), and drafts an emergency PSU approval note sheet.
4. **Verifiable Air-Gap Isolation:** Executes code inside isolated network namespaces (`unshare -n`) with audit attestation proving 0 bytes egress.

---

## Quick Start: Generating Native Office Documents
To compile native `.docx`, `.xlsx`, and `.pptx` files into the `sample_data/` directory:
```bash
python sample_data/generate_sample_documents.py
```
Or double-click `sample_data/build_samples.bat`.