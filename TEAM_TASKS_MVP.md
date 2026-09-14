# AegisForge-AI: Team Task Division & MVP Execution Plan

> **Team Size:** 5 Members  
> **Strategy:** **MVP First** — Complete one specific end-to-end golden workflow before adding complex features.  
> **Target MVP Workflow:** **Statutory Defect Ingestion → ASME Calculation Verification → Local DeepSeek-R1 Synthesis → Native Word (.docx) Note for Approval Generation → Streamlit UI Demo.**

---

## 🎯 The MVP "Golden Path" (Our Single Focus)

Do **NOT** try to build the entire system at once (skip vector databases, multi-tenancy, and advanced sandboxing for now).  
For the MVP, all 5 members will work toward **one working end-to-end demonstration**:

```mermaid
flowchart LR
    A[Member 5: UI Upload] --> B[Member 2: OCR / Log Parser]
    B --> C[Member 3: ASME Code Calculator]
    C --> D[Member 1: Model Router & Orchestrator]
    D --> E[Member 4: Native .docx Generator]
    E --> F[Member 5: Download & Display]
```

### The Scenario:
1. An operator uploads a field inspection report (`sample_data/06_inspection_reports/field_inspector_raw_ocr_log.txt` or `.md`).
2. The system extracts the thickness reading ($138.20\text{ mm}$ for nozzle BK-01).
3. The deterministic calculation engine checks against ASME Sec VIII Div 1 ($t_{\text{min}} = 138.57\text{ mm}$) and flags a **critical safety breach** (-0.37 mm).
4. Local **DeepSeek-R1** reasons through the regulatory risk and synthesizes an executive justification under CVC & DOP rules.
5. The system generates a formatted, real **Microsoft Word Note for Approval (`.docx`)** ready for executive sign-off.
6. The entire flow runs on **localhost** (zero cloud API calls) and is displayed via an intuitive **Streamlit UI**.

---

## 👥 5-Person Role Allocation for MVP (Phase 1)

Each member has **one clear deliverable** and a defined interface so no one is blocked.

---

### 👤 Member 1: Agent Orchestrator & Local Model Routing
- **Primary Domain:** Core pipeline logic & Ollama integration (`models/router/`, `agent_orchestrator/`)
- **MVP Responsibility:** Connect the steps together into a clean, runnable pipeline.
- **Specific Tasks for MVP:**
  1. Build a simple controller script (`pipeline_mvp.py` or inside `backend/`) that calls Member 2's parser, Member 3's calculator, local Ollama models, and Member 4's docx generator.
  2. Use [`models/router/model_router.py`](file:///c:/Users/rahul/SIH-antigravity-offline/models/router/model_router.py) to dispatch the reasoning prompt to `deepseek-r1:1.5b` (or `llama3.2:3b` as fallback).
  3. Ensure Ollama runs locally without errors and passes the synthesized justification back as structured text.
- **Deliverable:** `run_mvp_pipeline(input_file) -> dict` function that takes raw input and produces the final structured output dictionary.

---

### 👤 Member 2: Ingestion & Data Extraction (OCR / Regex / Text)
- **Primary Domain:** Data ingestion & extraction (`ingestion/`, `models/vision_models/`)
- **MVP Responsibility:** Extract structured inspection parameters from raw text or OCR logs.
- **Specific Tasks for MVP:**
  1. Write an extractor script (`ingestion/extract_inspection_data.py`) that reads `sample_data/06_inspection_reports/field_inspector_raw_ocr_log.txt` (or user input text).
  2. Extract key parameters using regex / simple LLM parser:
     - Equipment ID (e.g. `11-V-102` / `HP Separator`)
     - Material Grade (e.g. `SA-387 Gr 22 Cl 2`)
     - Internal Design Pressure $P$ ($14.5\text{ MPa}$)
     - Inside Radius $R$ ($1200\text{ mm}$)
     - Allowable Stress $S$ ($138.0\text{ MPa}$)
     - Measured Wall Thickness $t_{\text{actual}}$ ($138.20\text{ mm}$)
     - Corrosion Rate ($0.75\text{ mm/year}$)
  3. Provide fallback: If a P&ID or image is uploaded, integrate [`models/vision_models/test_easyocr.py`](file:///c:/Users/rahul/SIH-antigravity-offline/models/vision_models/test_easyocr.py) to extract text tags.
- **Deliverable:** A Python function `parse_inspection_input(file_path_or_text) -> dict` returning clean numeric parameters.

---

### 👤 Member 3: Engineering Calculation Engine (Physics & Code Tool)
- **Primary Domain:** Deterministic engineering math (`tools/`, `sample_data/03_engineering_calculations/`)
- **MVP Responsibility:** Verify safety limits using authentic ASME & API formulas (no LLM hallucinations).
- **Specific Tasks for MVP:**
  1. Create `tools/asme_calculator.py` implementing ASME Section VIII Division 1 UG-27:
     $$t_{\text{req}} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P} + \text{Corrosion Allowance}$$
  2. Calculate:
     - Required thickness $t_{\text{min}}$ ($138.57\text{ mm}$)
     - Margin / Breach ($138.20 - 138.57 = -0.37\text{ mm}$ -> **CRITICAL BREACH**)
     - Remaining life under API 510: $\text{Life} = \frac{t_{\text{actual}} - t_{\text{min}}}{\text{Corrosion Rate}} = -0.49\text{ Years}$
     - Derated Maximum Allowable Working Pressure (MAWP).
  3. Package outputs into a clean JSON dictionary with pass/fail flags and calculation explanations.
- **Deliverable:** `tools/asme_calculator.py` with function `evaluate_vessel_integrity(params: dict) -> dict`.

---

### 👤 Member 4: Deliverable Compiler (Native Word .docx Generator)
- **Primary Domain:** Office deliverable compilation (`output_generation/`, `sample_data/generate_sample_documents.py`)
- **MVP Responsibility:** Turn the AI synthesis and calculation findings into a real Microsoft Word document (`.docx`).
- **Specific Tasks for MVP:**
  1. Adapt `sample_data/generate_sample_documents.py` or use `python-docx` into a reusable module: `output_generation/docx_generator.py`.
  2. Create a clean corporate template for a **PSU Note for Approval (NFA)**:
     - Header: Indian Oil Corporation Ltd / Refinery Division
     - Note Reference No, Date, Security Classification ("RESTRICTED / INTERNAL")
     - Section 1: Background & Defect Identification (from Member 2)
     - Section 2: ASME Code Calculation Proof & Defect Analysis (from Member 3)
     - Section 3: Executive Justification & Emergency Procurement (from Member 1 / DeepSeek-R1)
     - Section 4: Recommended Action & Signature Matrix
  3. Output a valid `.docx` file saved in `data/` or a temporary output folder.
- **Deliverable:** `generate_approval_nfa_docx(data: dict, output_path: str) -> str` returning the file path of the generated Word document.

---

### 👤 Member 5: Frontend Dashboard & Air-Gap Demo Experience
- **Primary Domain:** User Interface & Demo Experience (`frontend/`)
- **MVP Responsibility:** Build a clean Streamlit dashboard to demonstrate the entire workflow visually.
- **Specific Tasks for MVP:**
  1. Build a Streamlit app (`frontend/app.py` or `app.py`):
     - **Upload / Select Box:** Choose a sample document (`field_inspector_raw_ocr_log.txt` or upload custom file).
     - **Execution Button:** "Run Air-Gapped Analysis".
     - **Live Progress Steps:**
       1. ✅ Raw Data Ingestion & OCR
       2. ✅ ASME Sec VIII Mathematical Verification (Highlight Breach in Red)
       3. ✅ Local DeepSeek-R1 Chain-of-Thought Reasoning
       4. ✅ Compilation of Formal Office Deliverable
     - **Deliverable Download:** Download button for the generated `.docx` file.
     - **Air-Gap Badge:** Visual indicator showing "100% On-Premises | Zero External Network Egress".
- **Deliverable:** Launchable Streamlit application (`streamlit run frontend/app.py`) running the complete demo.

---

## 📋 The MVP Data Contract (How the 5 Members Connect)

To ensure no one blocks anyone else, everyone must use this shared data dictionary format:

```json
{
  "equipment_id": "11-V-102",
  "equipment_name": "HP Separator",
  "unit": "Hydrocracker Unit (HCU-11)",
  "material": "SA-387 Gr 22 Cl 2",
  "measured_thickness_mm": 138.20,
  "corrosion_rate_mm_yr": 0.75,
  "calculation_results": {
    "t_min_mm": 138.57,
    "delta_mm": -0.37,
    "is_breach": true,
    "remaining_life_years": -0.49,
    "status": "CRITICAL BREACH - CODE VIOLATION"
  },
  "reasoning_synthesis": {
    "executive_summary": "Nozzle BK-01 has breached the ASME Sec VIII Div 1 code minimum...",
    "regulatory_compliance": "Immediate operating pressure derating required per API 510...",
    "procurement_justification": "Emergency weld overlay restoration under CVC PAC guidelines..."
  },
  "output_docx_path": "data/generated_nfa_11-V-102.docx"
}
```

---

## 🚫 What We are NOT Doing in the MVP (Do NOT Waste Time Here)

To ensure the team finishes the MVP rapidly, deliberately defer the following tasks:

| Deferred Feature | Why It Is Deferred | When We Will Do It |
| :--- | :--- | :--- |
| **Complex Vector DB (Chroma/FAISS RAG)** | We already have exact rules and sample files; RAG is not needed for the first demo. | Phase 2 |
| **User Authentication / Login / Roles** | Unnecessary overhead for the core functional proof-of-concept. | Phase 3 |
| **Full Linux Kernel `unshare -n` sandbox** | Hard to run/test on Windows machines; use process isolation first. | Phase 3 |
| **Multi-tenancy & Database Migrations** | Static JSON and file storage is faster and sufficient for MVP. | Phase 2 |
| **Training / Fine-Tuning Models** | Use existing open-weight GGUF/Ollama models (`deepseek-r1:1.5b`, `llama3.2:3b`). | Post-MVP |

---

## 🗓️ Roadmap: What We Do Next (After MVP is Working)

Once the MVP end-to-end demo is tested and running cleanly:

### Phase 2: Expanding Modalities & Deliverables
- **Member 1:** Enhance Model Router with automatic intent classification and LangGraph fallback nodes.
- **Member 2:** Add P&ID Blueprint visual bounding box overlay using EasyOCR + SVG coordinate mapping.
- **Member 3:** Add Darcy-Weisbach pipe pressure drop and API 520 safety valve relief calculations.
- **Member 4:** Add native PowerPoint presentation generator (`.pptx`) and Excel calculation sheets (`.xlsx`).
- **Member 5:** Add visual comparison tabs (Input Blueprint vs Detected Tags vs Output Document).

### Phase 3: Enterprise Hardening & Air-Gap Attestation
- Implement local ChromaDB vector store over CVC guidelines & ASME standards.
- Package everything into a one-command launch script or Docker Compose setup.
- Add network isolation verification audit (attestation report proving 0 bytes egress).

---

## ⚡ Step-by-Step Execution Plan (Start Right Now)

1. **Step 1:** Member 2 extracts the numbers from `sample_data/06_inspection_reports/field_inspector_raw_ocr_log.txt`.
2. **Step 2:** Member 3 writes the math formulas in `tools/asme_calculator.py` and verifies $t_{\text{min}} = 138.57\text{ mm}$.
3. **Step 3:** Member 4 creates `output_generation/docx_generator.py` to produce a sample `.docx` with dummy data.
4. **Step 4:** Member 1 tests `models/reasoning_models/test_reasoning.py` via Ollama to generate the text recommendation.
5. **Step 5:** Member 1 links steps 1-4 into `pipeline_mvp.py`.
6. **Step 6:** Member 5 wraps `pipeline_mvp.py` inside Streamlit for the live demo!
