# AegisForge-AI: Sovereign Air-Gapped AI Workbench for PSUs & Critical Infrastructure

> **Self-hosted, air-gapped agentic AI workbench running entirely on on-premises GPU infrastructure with zero data leakage.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![CUDA](https://img.shields.io/badge/CUDA-12.4%20(RTX%203050)-green.svg)](https://developer.nvidia.com/cuda-toolkit)
[![Ollama](https://img.shields.io/badge/Local%20Serving-Ollama-black.svg)](https://ollama.com/)
[![Deliverables](https://img.shields.io/badge/Deliverables-.DOCX%20%7C%20.PDF-orange.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Executive Summary

Public Sector Undertakings (PSUs), defence manufacturing units, refineries (IOCL, ONGC, BPCL, HPCL), power utilities (NTPC), and government institutions handle mission-critical, highly confidential knowledge work daily. None of this sensitive IP can ever be transmitted to public cloud LLMs due to strict national data residency regulations and air-gap network mandates.

**AegisForge-AI** provides an industrial-grade, self-hosted, multi-model AI workbench that dynamically routes requests across specialized open-weight models and executes engineering workflows (like ASME Section VIII code compliance and statutory Note for Approval generation) with complete on-premises data residency, hardware-level air-gap isolation, and direct compilation of native Microsoft Office deliverables.

---

## Complete Architecture & File Catalog

The project is structured around a streamlined Input → Math Verification → Document Generation pipeline. Below is the exhaustive catalog of every file and folder, including their purpose, expected inputs, and generated outputs.

### Root Level Files
| File | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| `main.py` | Central CLI Operating Gateway. | CLI arguments/flags | Routes to sub-commands, launches UI, executes pipeline |
| `requirements.txt` | Python dependencies. | `pip install` command | Python environment setup |
| `FUTURE_ROADMAP.md` | Tracks planned features and removed components. | N/A | N/A |
| `README.md` | Primary project documentation. | N/A | N/A |
| `.gitignore` | Defines files ignored by Git. | Git commands | Cleaner repository |

---

### Configuration & Schemas
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`config/`** | **Configuration directory.** | | |
| └ `settings.py` | Centralizes project paths and model registry. | Environment variables | Constant variables for imports |
| **`schemas/`** | **Data contracts directory.** | | |
| └ `mvp_schema.py` | Pydantic schemas validating data between pipeline stages. | Raw data dictionaries | Validated Pydantic objects (`InspectionInput`, etc.) |

---

### Data Ingestion
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`ingestion/`** | **Input parsing directory.** | | |
| └ `extract_inspection_data.py` | Extracts structured equipment parameters from messy OCR logs. | Raw `.txt` files or strings | Populated `InspectionInput` schema |

---

### Engineering & Utility Tools
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`tools/`** | **Deterministic tools directory.** | | |
| ├ `asme_calculator.py` | Deterministic ASME UG-27 pressure vessel math engine. | `InspectionInput` | `CalculationOutput` (t_min, delta, breach status) |
| ├ `sandbox.py` | Isolated Python code execution environment. | Raw Python code string | Execution stdout, stderr, and exit code |
| ├ `file_io.py` | Local text and JSON file reader/writer. | File paths, content strings | Read content or boolean success |
| ├ `rag.py` | Local knowledge search across PSU manuals. | Query string | Context string matching keywords |
| └ `doc_generator.py` | Unified wrapper for Word and PDF generation. | `InspectionInput`, `CalculationOutput`, `ReasoningOutput` | File paths and SHA-256 hashes |

---

### Document Generation
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`output_generation/`** | **Native document compilers.** | | |
| ├ `docx_generator.py` | Compiles native Microsoft Word `.docx` Approval Notes. | Pipeline data objects | Binary `.docx` file |
| └ `pdf_generator.py` | Compiles native Adobe `.pdf` Approval Notes using ReportLab. | Pipeline data objects | Binary `.pdf` file |

---

### Artificial Intelligence Models
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`models/`** | **AI engines and routers.** | | |
| ├ `model_downloader.py` | Download manager for Ollama and EasyOCR models. | Model identifiers | Model weights saved to disk |
| └ **`router/`** | | | |
| &nbsp;&nbsp;└ `model_router.py` | Heuristic task classifier and Ollama client dispatcher. | Text prompts, images | Text responses from AI |

---

### Pipeline Orchestration
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`agent_orchestrator/`** | **Pipeline controllers.** | | |
| └ `orchestrator_mvp.py` | Ties all stages together: Ingestion → Math → AI → Output | Target file path | Final generated document paths |

---

### Frontend
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`frontend/`** | **Web UI directory.** | | |
| └ `app.py` | Clean Streamlit Dashboard with 3 tabs (Workbench, Math, Models). | User UI interactions | Web interface |

---

### Data Storage & Assets
| File/Folder | Purpose | Inputs | Outputs |
| :--- | :--- | :--- | :--- |
| **`sample_data/`** | **Test fixtures.** | | |
| └ `06_inspection_reports/` | Contains raw noisy OCR logs for the MVP pipeline. | N/A | Mock inspection data |
| **`model_pool/`** | **Local weight storage.** | | |
| └ `easyocr/` | Contains downloaded `.pth` weights for EasyOCR models. | Download streams | `.pth` weight files |
| **`data/`** | **Runtime data directory.** | | |
| ├ `uploads/` | Stores files and images uploaded by the user via the UI. | User uploads | Saved files |
| └ `output/` | Destination folder for all generated reports and deliverables. | Generators | Final `.docx` / `.pdf` |

---

## The Golden Path Workflow

AegisForge-AI orchestrates an end-to-end "Golden Path" to automate statutory processes:

1. **Ingestion**: Parses a noisy field inspector's ultrasonic thickness reading log.
2. **Deterministic Math Verification**: Uses the `asme_calculator` to execute the ASME Section VIII Div 1 UG-27 formula to calculate the absolute minimum safe wall thickness ($t_{min}$) required for the vessel, entirely bypassing probabilistic LLM math hallucination.
3. **AI Synthesis**: Routes the breach data to `deepseek-r1:1.5b` (or another model) to synthesize the CVC procurement justification, DOP compliance, and executive summary.
4. **Document Generation**: Compiles the inspection data, math results, and AI reasoning into a native, cryptographically hashed Microsoft Word `.docx` and Adobe `.pdf` Note for Approval.

---

## Quick Start Guide

### 1. Environment Setup

Clone the repository and set up a Python environment (3.11+):

```bash
git clone https://github.com/Shivanshvyas1729/AegisForge-AI.git
cd AegisForge-AI
pip install -r requirements.txt
```

### 2. Configure Local Models with Ollama

Ensure [Ollama](https://ollama.com/) is installed and running. You can manage models directly from the UI, or pull them via CLI:

```bash
ollama pull deepseek-r1:1.5b
ollama pull qwen2.5-coder:1.5b
ollama pull llama3.2:3b
```

### 3. Launch the Application

AegisForge-AI features a centralized CLI via `main.py`. 

**To launch the modern Streamlit Web Dashboard:**
```bash
python main.py ui
```
*This opens a 3-tab workbench featuring the AI chat, the ASME calculator, and the Model Hub.*

**To run the Golden Path pipeline directly via CLI:**
```bash
python main.py run-golden-path
```

**To view the interactive CLI menu and system health:**
```bash
python main.py
```

---

## Dynamic Model Routing

The `SovereignModelRouter` dynamically evaluates tasks and routes them to the optimal local model:

| Task Modality | Local Model | Primary Hardware | VRAM / RAM Required | Key Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Coding & SCADA** | `qwen2.5-coder:1.5b` | Local GPU (RTX 3050) | ~1.8 GB VRAM | Python automation, Modbus CRC-16 parsers. |
| **Deep Reasoning** | `deepseek-r1:1.5b` | Local GPU (RTX 3050) | ~1.8 GB VRAM | ASME calculations, CVC compliance, math reasoning. |
| **Generalist Tasks** | `llama3.2:3b` | Local GPU (RTX 3050) | ~2.2 GB VRAM | Executive summaries, report drafting. |

---

## Target Industry Sectors

- **Oil & Gas Refineries**: Indian Oil Corporation Ltd (IOCL), ONGC, BPCL, HPCL, GAIL
- **Defence & Aerospace**: DRDO, Bharat Electronics Ltd (BEL), Hindustan Aeronautics Ltd (HAL)
- **Power & Heavy Engineering**: NTPC, BHEL, Power Grid Corporation of India
- **Statutory & Regulatory Bodies**: Petroleum and Explosives Safety Organization (PESO), Oil Industry Safety Directorate (OISD), Central Vigilance Commission (CVC)

---

## License

This project is licensed under the [MIT License](LICENSE).