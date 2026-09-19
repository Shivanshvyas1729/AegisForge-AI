Here is your **complete blueprint** for rebuilding your workbench from scratch.

It provides a clean, production-grade separation:
* **Tools:** Deterministic Python functions (math, sandbox, file I/O, OCR, network checks). No hallucinations, strict inputs/outputs.
* **Agents:** LLM cognitive entities (planning, vision reasoning, code generation, audit deductions, executive synthesis).

---

# Part 1: The Pure Tools (Deterministic Execution Layer)

```
tools/
├── vision/
│   └── ocr_extractor_tool.py
├── engineering/
│   ├── asme_ug27_tool.py
│   ├── material_db_tool.py
│   └── api_579_ffs_tool.py
├── data/
│   ├── spreadsheet_analyzer_tool.py
│   └── file_io_tool.py
├── compliance/
│   ├── cvc_auditor_tool.py
│   └── local_rag_tool.py
├── security/
│   ├── sandbox_tool.py
│   ├── network_verifier_tool.py
│   └── audit_trail_tool.py
└── publishing/
    └── deliverable_publisher_tool.py
```

---

### 1. `ocr_extractor_tool`
* **Responsibility:** Ingests scanned PDFs, handwritten forms, or inspection photos using local OCR (EasyOCR/Tesseract) and regex to extract structured equipment parameters without hallucination.
* **Inputs:** `file_path: str` (path to image/PDF).
* **Outputs:** 
  ```json
  {
    "equipment_id": "11-V-102",
    "equipment_name": "HP Separator Drum",
    "material": "2.25Cr-1Mo",
    "design_pressure_mpa": 14.5,
    "measured_thickness_mm": 138.2,
    "corrosion_rate_mm_yr": 0.75,
    "raw_ocr_text": "...",
    "confidence_score": 0.94
  }
  ```
* **Priority:** **MVP (Urgent)**

---

### 2. `spreadsheet_analyzer_tool`
* **Responsibility:** Parses ultrasonic thickness (UT) gauge matrix files (`.xlsx`/`.csv`), computes average wall loss, identifies the absolute minimum spot, and locates Localized Thin Areas (LTA).
* **Inputs:** `file_path: str`, `grid_id: Optional[str]`.
* **Outputs:** 
  ```json
  {
    "total_inspection_points": 144,
    "nominal_thickness_mm": 142.0,
    "min_measured_thickness_mm": 138.2,
    "critical_point_location": "Grid B-4 (Bottom Knuckle)",
    "mean_thickness_mm": 140.1,
    "localized_thin_areas": [{"location": "B-4", "thickness": 138.2}]
  }
  ```
* **Priority:** **MVP (Urgent)**

---

### 3. `asme_ug27_tool`
* **Responsibility:** Strictly deterministic implementation of ASME Section VIII Div 1 UG-27 formula ($t_{\text{req}} = \frac{P \cdot R}{S \cdot E - 0.6P} + CA$) and API 510 remaining safe service life. All calculation steps are explicitly returned.
* **Inputs:**
  * `P_mpa: float` (Design Pressure)
  * `R_mm: float` (Inside Radius)
  * `S_mpa: float` (Allowable Stress)
  * `E: float` (Joint Efficiency, e.g. 1.0)
  * `CA_mm: float` (Corrosion Allowance)
  * `t_actual_mm: float` (Measured Thickness)
  * `corrosion_rate_mm_yr: float`
* **Outputs:**
  ```json
  {
    "t_req_mm": 138.57,
    "delta_margin_mm": -0.37,
    "is_breach": true,
    "status": "CRITICAL_BREACH",
    "remaining_life_years": -0.49,
    "derated_mawp_bar": 118.0,
    "formula_steps": [
      "t_req = (14.5 * 1200) / (138 * 1.0 - 0.6 * 14.5) = 138.57 mm",
      "delta = 138.20 - 138.57 = -0.37 mm (Code Violation)"
    ]
  }
  ```
* **Priority:** **MVP (Urgent)**

---

### 4. `material_db_tool`
* **Responsibility:** Embedded lookup table (ASME Section II Part D) mapping standard refinery metallurgy to maximum allowable stress ($S$) at temperature. Prevents the LLM from inventing material properties.
* **Inputs:** `material_grade: str`, `design_temp_c: float`.
* **Outputs:**
  ```json
  {
    "material": "2.25Cr-1Mo (SA-387 Gr 22)",
    "allowable_stress_mpa": 138.0,
    "yield_strength_mpa": 310.0,
    "tensile_strength_mpa": 515.0
  }
  ```
* **Priority:** **MVP (Urgent)**

---

### 5. `api_579_ffs_tool` (Fitness-For-Service)
* **Responsibility:** Evaluates Level 1 Fitness-For-Service when wall thickness breaches UG-27 to see if derating pressure allows continued operation without immediate emergency shutdown.
* **Inputs:** `t_actual: float`, `t_req: float`, `flaw_length_mm: float`, `inside_radius_mm: float`.
* **Outputs:**
  ```json
  {
    "rsf": 0.88,
    "allowable_rsf": 0.90,
    "is_acceptable_as_is": false,
    "recommendation": "Pressure derating mandatory; weld overlay required within 30 days."
  }
  ```
* **Priority:** **Future / Phase 2** (Nice-to-have for hackathon bonus points).

---

### 6. `sandbox_tool`
* **Responsibility:** Executes agent-generated Python code in a restricted, isolated subprocess with timeouts (10s max), memory caps (512MB), and OS network sockets completely blocked.
* **Inputs:** `code_string: str`.
* **Outputs:**
  ```json
  {
    "exit_code": 0,
    "stdout": "...",
    "stderr": "",
    "execution_time_ms": 142,
    "is_sandboxed": true
  }
  ```
* **Priority:** **MVP (Urgent)** *(Explicitly named in MRPL problem statement)*

---

### 7. `local_rag_tool`
* **Responsibility:** Purely local vector search (ChromaDB + `bge-small-en` or `nomic-embed-text`) querying internal MRPL SOPs, OISD standards, and CVC circulars. Completely offline.
* **Inputs:** `query: str`, `top_k: int = 3`.
* **Outputs:**
  ```json
  {
    "results": [
      {
        "document": "CVC Circular 02/02/2004",
        "snippet": "Single-source procurement permissible only in verified emergency...",
        "similarity_score": 0.89
      }
    ]
  }
  ```
* **Priority:** **MVP (Urgent)**

---

### 8. `cvc_auditor_tool`
* **Responsibility:** Deterministic rules engine checking compliance with Central Vigilance Commission guidelines, Proprietary Article Certificate (PAC) rules, and Delegation of Powers (DOP) spending limits.
* **Inputs:** `equipment_id: str`, `estimated_cost_inr: float`, `is_single_source: bool`, `has_pac: bool`, `is_emergency: bool`.
* **Outputs:**
  ```json
  {
    "is_compliant": true,
    "applicable_clause": "CVC Circular 02/02/2004 Clause 4.2 (Single-Source Emergency)",
    "sanction_authority": "Director (Refineries) & Competent Financial Authority",
    "violations": []
  }
  ```
* **Priority:** **MVP (Urgent)**

---

### 9. `network_verifier_tool`
* **Responsibility:** Inspects active OS sockets and process trees during the run to verify that **zero external outbound IP packets** are transmitted.
* **Inputs:** `scope: str = "process"`.
* **Outputs:**
  ```json
  {
    "is_air_gap_intact": true,
    "external_ips_contacted": [],
    "verdict": "VERIFIED_ZERO_EGRESS_AIR_GAPPED"
  }
  ```
* **Priority:** **MVP (Urgent)** *(Explicitly required as the "actual proof of the sovereign claim")*

---

### 10. `audit_trail_tool`
* **Responsibility:** Writes an append-only JSON ledger where every entry is chained with a SHA-256 cryptographic hash (blockchain-style tamper-evident log).
* **Inputs:** `tool_name: str`, `inputs: dict`, `outputs: dict`, `caller: str`.
* **Outputs:** `entry_hash: str` (SHA-256).
* **Priority:** **MVP (Urgent)**

---

### 11. `file_io_tool`
* **Responsibility:** Safe file read/write operations strictly sandboxed within the project workspace directory (prevents directory traversal `../../`).
* **Inputs:** `action: "read" | "write"`, `relative_path: str`, `content: Optional[str]`.
* **Outputs:** `{"status": "SUCCESS", "data": "..."}`.
* **Priority:** **MVP (Urgent)**

---

### 12. `deliverable_publisher_tool`
* **Responsibility:** Compiles formal PSU Word (`.docx`) Notes for Approval (NFA) and PDF deliverables with classification headers, calculation tables, CVC clauses, and SHA-256 integrity seal.
* **Inputs:** `inspection_data: dict`, `calculation_data: dict`, `compliance_data: dict`, `executive_summary: str`.
* **Outputs:**
  ```json
  {
    "docx_path": "data/output/11-V-102_Approval_Note.docx",
    "pdf_path": "data/output/11-V-102_Approval_Note.pdf",
    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
  ```
* **Priority:** **MVP (Urgent)**

---

# Part 2: The Core Agents (LLM Cognitive Layer)

```
agent_orchestrator/
├── supervisor_agent.py   (Hub: Dynamic Planner & Model Router)
├── vision_agent.py       (Vision Specialist: OCR & Drawing Ingestion)
├── coder_agent.py        (Code & Math Specialist: ASME & Sandbox Runner)
├── reasoning_agent.py    (Compliance Specialist: CVC Audit & Legal Logic)
└── reviewer_agent.py     (Chief Reviewer: Quality Gate & Report Synthesizer)
```

---

### 1. `Supervisor Agent` (The Hub)
* **Model Recommended (6 GB GPU):** **`qwen2.5:3b`** (Unmatched JSON formatting & task decomposition).
* **Responsibility:**
  1. Inspects the user query and uploaded attachments.
  2. Dynamically plans a task queue (e.g., Step 1: Vision $\rightarrow$ Step 2: Math $\rightarrow$ Step 3: Compliance $\rightarrow$ Step 4: Review).
  3. **Auto-selects the right open-weight model** based on task domain.
  4. Evaluates completed tasks: if an agent fails, it retries (up to 3 times) or pauses for human intervention.
* **State Inputs:** `user_query`, `uploaded_file_path`, `task_queue`, `current_task`, `retry_count`.
* **State Outputs:** `task_queue`, `current_task`, `next_node`.
* **Tools Called:** None (delegates all work to worker agents).
* **Priority:** **MVP (Urgent)**

---

### 2. `Vision Agent` (Multimodal Ingestion)
* **Model Recommended (6 GB GPU):** **EasyOCR + `moondream2` / `minicpm-v:8b`** (or rule-based OCR extractor).
* **Responsibility:** Inspects scanned inspection PDFs, handwritten reports, or P&ID drawings. Extracts equipment tags, metallurgy, and critical wall thickness numbers.
* **State Inputs:** `uploaded_file_path`, `current_task`.
* **State Outputs:** `inspection_data: dict`, `current_task["output"]`.
* **Tools Called:** `ocr_extractor_tool`, `spreadsheet_analyzer_tool`.
* **Priority:** **MVP (Urgent)**

---

### 3. `Coder Agent` (Engineering & Sandbox Execution)
* **Model Recommended (6 GB GPU):** **`qwen2.5-coder:1.5b`** or **`qwen2.5:3b`**.
* **Responsibility:** Executes deterministic engineering calculations (ASME UG-27, material lookups) or generates and executes Python code in the sandbox to verify calculations.
* **State Inputs:** `inspection_data`, `current_task`.
* **State Outputs:** `calculation_data: dict`, `current_task["output"]`.
* **Tools Called:** `asme_ug27_tool`, `material_db_tool`, `sandbox_tool`, `api_579_ffs_tool`.
* **Priority:** **MVP (Urgent)**

---

### 4. `Reasoning Agent` (Statutory Compliance & Deduction)
* **Model Recommended (6 GB GPU):** **`deepseek-r1:1.5b`** (High chain-of-thought logic).
* **Responsibility:** Examines the calculation outcome (e.g., critical wall thickness breach) and deduces statutory procurement clauses (CVC guidelines, emergency single-source justification, RBI inspection intervals).
* **State Inputs:** `inspection_data`, `calculation_data`, `current_task`.
* **State Outputs:** `compliance_data: dict`, `current_task["output"]`.
* **Tools Called:** `cvc_auditor_tool`, `local_rag_tool`.
* **Priority:** **MVP (Urgent)**

---

### 5. `Chief Reviewer Agent` (Gatekeeper & Executive Synthesizer)
* **Model Recommended (6 GB GPU):** **`llama3.2:3b`** or **`qwen2.5:3b`**.
* **Responsibility:** Acts as the Chief Technical Reviewer. Verifies that math is sound, statutory clauses are valid, and air-gap telemetry is clean. If approved, synthesizes the final professional Executive Summary for the approval note.
* **State Inputs:** `inspection_data`, `calculation_data`, `compliance_data`.
* **State Outputs:** `review_verdict: dict`, `executive_summary: str`.
* **Tools Called:** `network_verifier_tool`, `audit_trail_tool`.
* **Priority:** **MVP (Urgent)**

*(Followed by the deterministic `deliverable_publisher_tool` compiling the `.docx` and `.pdf` files).*

---

# Part 3: Roadmap Matrix (MVP vs Future)

| Layer | Component | Status | Why |
| :--- | :--- | :---: | :--- |
| **Agent** | `Supervisor Agent` | **MVP** | Required for multi-model auto-selection and planning. |
| **Agent** | `Vision Agent` | **MVP** | Required for scanned PDF and drawing ingestion. |
| **Agent** | `Coder Agent` | **MVP** | Required for verified sandbox execution and ASME calculations. |
| **Agent** | `Reasoning Agent` | **MVP** | Required for CVC procurement compliance. |
| **Agent** | `Chief Reviewer Agent` | **MVP** | Required for quality gatekeeping & executive summary. |
| **Tool** | `asme_ug27_tool` | **MVP** | Core domain math with steps shown. |
| **Tool** | `material_db_tool` | **MVP** | Grounded ASME stress lookup (zero hallucinations). |
| **Tool** | `ocr_extractor_tool` | **MVP** | On-device scanned document reader. |
| **Tool** | `spreadsheet_analyzer`| **MVP** | Ultrasonic thickness gauge matrix parsing. |
| **Tool** | `sandbox_tool` | **MVP** | Explicit requirement in problem statement. |
| **Tool** | `network_verifier` | **MVP** | Explicit requirement: proof of air-gap sovereignty. |
| **Tool** | `audit_trail_tool` | **MVP** | Tamper-proof cryptographic execution log. |
| **Tool** | `deliverable_publisher`| **MVP** | Delivers real Word (.docx) & PDF deliverables. |
| **Tool** | `local_rag_tool` | **MVP** | On-prem knowledge base search for refinery SOPs. |
| **Tool** | `cvc_auditor_tool` | **MVP** | PSU procurement compliance rules. |
| **Tool** | `api_579_ffs_tool` | **Future (v2)** | Advanced localized thinning analysis (nice-to-have). |
| **Feature**| Interactive CAD/DXF Parser | **Future (v2)** | Parsing native AutoCAD `.dwg`/`.dxf` piping files. |
| **Feature**| Distributed GPU Cluster | **Future (v2)** | Multi-GPU pooling across enterprise server racks. |
| **Feature**| SAP PM / ERP Connector | **Future (v2)** | Automatically creating maintenance work orders in SAP. |

Ran command: `uv run main.py`
Ran command: `cls`