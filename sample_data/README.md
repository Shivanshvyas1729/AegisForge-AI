# AegisForge-AI: Industrial Knowledge Work Benchmark & Sample Datasets

This repository contains authentic, domain-curated test fixtures representing sensitive industrial and PSU operational workflows across **Refineries, Defence Manufacturing, Power Utilities, and Government Offices**.

These datasets are specifically structured to benchmark and demonstrate **AegisForge-AI** — an on-premises, air-gapped sovereign AI workbench running on local GPU hardware with zero external cloud transmission.

---

## Directory & File Taxonomy

```
sample_data/
│
├── 01_approval_notes/                       # Category 1: PSU Executive & Technical Approvals
│   ├── IOCL_Refinery_Pump_Overhaul_Note.md  # PSU Note for Approval (NFA) - CVC & DOP compliance
│   ├── IOCL_Refinery_Pump_Overhaul_Note.json# Structured NFA metadata (Capex/Opex, Budget codes)
│   ├── IOCL_Refinery_Pump_Overhaul_Note.docx# Native Word doc (generated via build_samples.bat)
│   └── Defence_Emergency_Procurement_Note.md# Single-source Rad-Hard FPGA procurement under GFR-194
│
├── 02_board_presentations/                  # Category 2: Board & Executive Presentations
│   ├── Q3_Refinery_Modernization_Deck.md    # 6-slide strategic deck (Capex, ESG, Risk matrix)
│   ├── Board_Resolution_Capex_Strategy.json # Board agenda metadata and voting resolution draft
│   └── Q3_Refinery_Modernization_Deck.pptx  # Native PowerPoint deck (generated via build_samples.bat)
│
├── 03_engineering_calculations/             # Category 3: Engineering Math & Standard Code Physics
│   ├── ASME_Pressure_Vessel_Thickness_Calc.xlsx # ASME Sec VIII Div 1 wall thickness spreadsheet
│   ├── pipe_pressure_drop_darcy.py          # Verified Darcy-Weisbach & Colebrook hydraulic script
│   ├── crude_distillation_relief_valve_api520.csv # API 520 / 521 Pressure Safety Valve (PSV) dataset
│   └── engineering_design_basis_memo.md     # ASME Sec VIII Div 1 & API 510 mathematical proofs
│
├── 04_internal_tools_code/                  # Category 4: Internal Tooling & Sandbox Code
│   ├── scada_modbus_telemetry_parser.py     # DCS Modbus-RTU parser with CRC-16 & alarm detection
│   ├── airgap_safety_sandbox_runner.sh      # Network-isolated sandbox runner (unshare -n & cgroups)
│   ├── asset_maintenance_schema.sql         # PostgreSQL schema for equipment records & NDT logs
│   └── telemetry_register_mapping.json      # Modbus register map to physical engineering units
│
├── 05_scanned_drawings_pid/                 # Category 5: Scanned Drawings & P&ID Vision Analysis
│   ├── cdu_feed_preheat_train_pid.svg       # High-res vector P&ID (instruments, valves, tanks)
│   ├── pump_station_isometric_drawing.svg   # Piping isometric drawing with elevation & weld tags
│   ├── pid_legend_and_instrument_tags.json  # Ground-truth tag dictionary for Vision-Language Models
│   └── drawing_review_checklist.md          # 9-point HAZOP/P&ID verification benchmark protocol
│
├── 06_inspection_reports/                   # Category 6: Inspection, QA/QC & Corrosion Audits
│   ├── hydrocracker_reactor_ndt_ultrasonic_report.md # API 510 Ultrasonic thickness survey
│   ├── hydrocracker_reactor_ndt_ultrasonic_report.docx# Native Word doc report (via build_samples.bat)
│   ├── field_inspector_raw_ocr_log.txt      # Noisy field clipboard OCR stream with handwritten note
│   └── equipment_corrosion_audit_registry.json # Structured C-Scan defect registry with remaining life
│
├── generate_sample_documents.py             # Pure Python standard-library OpenXML generator
├── build_samples.bat                        # Double-click script to compile .docx, .pptx, .xlsx
└── README.md                                # This documentation
```

---

## Benchmark Scenarios & Agentic Task Mapping

| Category | Benchmark Scenario | Models Targeted | Expected Agent Deliverable |
| :--- | :--- | :--- | :--- |
| **01. Approval Notes** | Automated NFA Drafting from raw incident logs | Reasoning LLMs (e.g. DeepSeek-R1, Qwen-2.5) | Formal PSU Note for Approval adhering to CVC guidelines and DOP clauses (`.docx`, `.md`). |
| **02. Board Presentations** | Summarizing complex ₹14,250 Cr capex proposal into executive slides | Generalist LLMs (e.g. Llama-3.3, Mistral) | Structured 6-slide executive deck with IRR tables, funding split, and risk mitigations (`.pptx`, `.md`). |
| **03. Calculations** | ASME Sec VIII pressure vessel wall thickness & Darcy-Weisbach flow | Math / Reasoning Models | Complete step-by-step mathematical substitution, MAWP check, and hydrostatic test pressure (`.xlsx`, `.py`). |
| **04. Internal Tools** | Industrial SCADA telemetry parsing & safe execution | Coding Models (e.g. Qwen-2.5-Coder) | Python tool execution inside an air-gapped network namespace with zero internet socket egress. |
| **05. Scanned P&ID** | Visual extraction of instrumentation bubbles and bypass loops | Vision-Language Models (e.g. Qwen2-VL) | Identification of equipment (`11-P-101A`, `11-V-101`), instrument tags (`PT-101`, `PSV-101`), and safety bypasses. |
| **06. Inspection QA** | End-to-end agentic workflow: OCR scan → defect analysis → approval note | Multimodal Agent Pipeline | Extraction of critical thickness breach ($138.20\text{ mm} < 138.57\text{ mm}$) and automatic draft of emergency repair NFA. |

---

## Generating Native Office Formats (`.docx`, `.pptx`, `.xlsx`)

To generate the binary Microsoft Office files on your local workstation:
1. Double-click **`build_samples.bat`**, OR
2. In your terminal, run:
   ```bash
   python sample_data/generate_sample_documents.py
   ```
*(Requires **zero** third-party pip packages; uses Python's standard `zipfile` module).*
