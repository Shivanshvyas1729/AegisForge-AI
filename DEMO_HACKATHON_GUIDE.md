# 🏆 AegisForge-AI — College Hackathon Demonstration Blueprint
**Self-Hosted, Air-Gapped Multi-Agent Industrial Copilot for PSUs & Critical Infrastructure**

---

## 🎯 High-Level Pitch & Core Analogy for Judges

> **The Core Analogy:**
> *"Imagine an Intensive Care Unit (ICU), but instead of a human patient, the patient is a 200-ton Hydrocracker Reactor running at 150 bar pressure and 450°C in an oil refinery. A 0.5 millimeter wall-thinning breach could cause a catastrophic explosion.*
>
> *Today, plant engineers must decipher faded inspection sheets, perform ASME differential equations by hand, and cross-reference 400 pages of Central Vigilance Commission (CVC) anti-corruption rules to approve emergency repairs — taking 4 to 6 weeks.*
>
> *Worse, **they cannot use ChatGPT, Claude, or Azure** because uploading refinery schematics and telemetry violates India's **Digital Personal Data Protection (DPDP) Act 2023** and National Security data sovereignty guidelines.*
>
> *AegisForge-AI is the **Sovereign Industrial AI ICU Team**. Running 100% locally on a single workstation GPU without any internet connection, a team of specialized AI agents analyzes drawings, calculates deterministic ASME physics equations, audits vigilance compliance, and generates a tamper-evident, cryptographically signed executive deliverable in **under 15 seconds**."*

---

## 👥 The Specialist Multi-Agent Team (Who Does What?)

```
                     ┌────────────────────────────────┐
                     │   👤 End User (Plant Engineer) │
                     └───────────────┬────────────────┘
                                     │
                                     ▼
                     ┌────────────────────────────────┐
                     │   🧠 Supervisor Orchestrator   │ (Llama 3.1 8B)
                     │   Decomposes goals, routes     │
                     └───────────────┬────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  👁️ Vision Agent │       │  💻 Coder Agent  │       │⚖️ Reasoning Agent│
│  (EasyOCR/Fitz)  │       │(Qwen 2.5 Coder)  │       │ (DeepSeek / Llama│
│  Extracts PDFs & │       │ASME Math & Docker│       │CVC Circulars, GFR│
│  Drawings/Grids  │       │Sandbox Execution │       │2017 & DoP Limits │
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                                    ▼
                     ┌────────────────────────────────┐
                     │   🛡️ Chief Reviewer (Gate)    │ (Llama 3.1 8B)
                     │   Forensic sign-off & verdict  │ Loops back if error
                     └───────────────┬────────────────┘
                                     │ APPROVED
                                     ▼
                     ┌────────────────────────────────┐
                     │   📑 Deliverable Publisher     │ Generates .docx
                     │   SHA-256 Audit Seal & Ledger  │ & zero-egress check
                     └────────────────────────────────┘
```

---

# 🚀 5 Complete Demonstration Scenarios

---

## 🎬 DEMO 1: The Emergency Breach & Official Deliverable (The "Golden Path")

### 1. The Analogy
> **"The Emergency Room Trauma Protocol"**:
> A critical pressure vessel has suffered severe wall loss. Instead of waiting weeks for paperwork while the plant risks rupture, the AI trauma team instantly reads the inspection dossier, detects the safety breach, identifies the statutory emergency clause (GFR 2017 Rule 194), and prints a sealed, legally audit-proof executive document for the General Manager to sign.

### 2. User Input
* **Where:** Tab 2: **🏭 Dossier Studio (Golden Path)**
* **Action:**
  1. Statutory Framework: Select `CVC Circular 02/02/2004 Clause 4.2 / GFR 2017 Rule 194 Emergency Exception`.
  2. Click the large blue button: **"🚀 Run Sovereign Industrial Pipeline"**.

### 3. Internal Working (What Happens Under the Hood)
1. **Ingestion:** `dossier_service.py` reads `sample_data/IOCL_Turnaround_Dossier_11-V-102.pdf` using PyMuPDF and regex parameter parsers.
2. **Parameter Extraction:** Identifies Vessel `11-V-102`, Design Pressure $P = 14.5$ MPa, Radius $R = 1200$ mm, Material SA-387 Gr 22, Measured Wall Thickness $t_{actual} = 138.20$ mm, Corrosion Rate $CR = 0.75$ mm/yr.
3. **Deterministic Math:** Calls `calculate_asme_stresses`. Evaluates UG-27 minimum thickness:
   $$t_{req} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P} + CA = \frac{14.5 \cdot 1200}{138 \cdot 1.0 - 0.6 \cdot 14.5} + 4.0 = 138.57\text{ mm}$$
4. **Integrity Evaluation:** Safety Margin $\Delta = 138.20 - 138.57 = -0.37$ mm. Status flagged as **`CRITICAL_BREACH`**. Remaining Service Life evaluated as $-0.49$ years.
5. **Statutory Vigilance Audit:** `compliance_auditor.py` verifies justification against CVC anti-corruption mandates:
   - GFR 2017 Rule 194 permits single-source OEM procurement without open tender when life-safety failure is imminent.
   - Delegation of Power (DoP) validates that expenditure exceeding ₹15 Lakhs requires General Manager (Technical Services) sanction.
6. **Executive Compilation:** `doc_generator.py` populates official executive template `IOCL_Emergency_Approval_Note.docx`.
7. **Cryptographic Seal:** `audit_trail.py` hashes the document with SHA-256 and commits an immutable event to SQLite ledger `data/audit_ledger.db`.

### 4. Expected Output
* Status Card: `CRITICAL_BREACH (Safety Margin: -0.37 mm)`
* Derated MAWP: `144.6 bar` (Derated from 145.0 bar design)
* Statutory Sanction: `Statutorily Compliant under GFR 2017 Rule 194 (Single-Source OEM)`
* Live Deliverable Button: **`📥 Download Certified Deliverable (IOCL_Emergency_Approval_Note.docx)`**
* SHA-256 Hash Seal displayed in UI.

---

## 🎬 DEMO 2: Deterministic ASME Section VIII & API 510 Engineering Math

### 1. The Analogy
> **"The High-Precision Digital Caliper vs Guesswork"**:
> If you ask a standard chatbot "What is the required thickness of a pressure vessel?", it will hallucinate a random number. AegisForge connects the conversational agent to a **certified ASME Section VIII Div 1 engineering calculator**, ensuring mathematical perfection every time.

### 2. User Input
* **Where:** Tab 1: **Sovereign Copilot (AI Workbench)**
* **Prompt:**
  ```text
  Calculate ASME Section VIII Div 1 UG-27 required wall thickness for design pressure 14.5 MPa, inside radius 1200 mm, allowable stress 138 MPa, CA 4 mm, actual thickness 138.2 mm.
  ```

### 3. Internal Working
1. `route_question` routes prompt to `supervisor_node`.
2. Supervisor (`llama3.1:8b`) reads prompt, determines task is deterministic engineering physics, decomposes intent, and issues instruction to `coder_agent`.
3. `coder_agent` (`qwen2.5-coder:7b`) calls tool `calculate_asme_stresses`.
4. The tool executes exact closed-form ASME equations:
   - UG-27 formula: $t_{req} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P} + CA$
   - Derated MAWP formula: $MAWP = \frac{S \cdot E \cdot (t_{act} - CA)}{R + 0.6 \cdot (t_{act} - CA)}$
   - API 510 Remaining Service Life: $RSL = \frac{t_{act} - t_{min}}{CR}$
5. Result returned to `chief_reviewer`, who verifies numerical ranges, stamps `VERDICT: APPROVED`, and releases output.

### 4. Expected Output
```markdown
### ASME Section VIII Div 1 UG-27 Evaluation
• Formula: t = (P * R) / (S * E - 0.6 * P) + CA
• Design Pressure (P): 14.5 MPa (145.0 bar)
• Inside Radius (R): 1200.0 mm
• Maximum Allowable Stress (S): 138.0 MPa
• Corrosion Allowance (CA): 4.0 mm
• Required Wall Thickness (t_req): 138.57 mm
• Measured Wall Thickness (t_actual): 138.20 mm
• Safety Margin (Delta): -0.37 mm [CRITICAL_BREACH]
• Derated MAWP: 144.6 bar
• API 510 Remaining Service Life (RSL): -0.49 Years
```

---

## 🎬 DEMO 3: Air-Gapped Docker Sandbox with AST Scanning & Self-Healing

### 1. The Analogy
> **"The Bomb Disposal Blast Chamber with a Self-Repairing Robot"**:
> If an AI writes software code on your computer, it could accidentally delete files or run a virus. AegisForge runs code inside an **air-gapped blast chamber (Docker container)** with **no network cable attached**. If the code fails or has a bug, the AI robot diagnoses the error and repairs the code itself before showing you the result.

### 2. User Input
* **Where:** Tab 1: **Sovereign Copilot**
* **Prompt:**
  ```text
  Write a Python script in the Docker sandbox to compute the first 10 Fibonacci numbers and print them.
  ```

### 3. Internal Working
1. Supervisor routes to `coder_agent`.
2. `coder_agent` generates Python script and invokes `execute_in_sandbox`.
3. **Layer 1 AST Security Scan:** `docker_sandbox.py` parses Python Abstract Syntax Tree before execution. Scans for forbidden imports (`os`, `sys`, `subprocess`, `socket`, `requests`).
4. **Layer 2 Container Execution:** Dispatches to standing container `aegisforge-sandbox-daemon`:
   - Network: `--network none` (Physical socket disconnection)
   - Memory Cap: `256 MB`
   - CPU Cap: `1.0 vCPU`
5. **Layer 3 Autonomous Self-Healing:** If Python emits a `SyntaxError` or runtime exception, the error traceback is intercepted and passed back to `qwen2.5-coder:7b`. The LLM writes a corrected patch and re-executes automatically in the container.
6. `chief_reviewer` confirms output is clean and provides final review.

### 4. Expected Output
```json
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```
```markdown
🛡️ Chief Reviewer Verdict: APPROVED
Executive Summary: The Python Fibonacci script executed cleanly inside the air-gapped Docker sandbox with 0 security exceptions.
```

---

## 🎬 DEMO 4: Autonomous Context Awareness & Follow-Ups (Zero Hardcoding)

### 1. The Analogy
> **"The Chief Engineer with Eidetic Memory"**:
> You don't have to re-explain yourself to a smart colleague. If you say "redo it" or "try again", they know exactly what you were working on. AegisForge does not rely on static if-else keyword rules; the AI supervisor uses LangGraph state memory to resolve follow-ups naturally.

### 2. User Input
* **Where:** Tab 1: **Sovereign Copilot**
* **Prompt (Right after Demo 3):**
  ```text
  redo it
  ```

### 3. Internal Working
1. The message `"redo it"` is ingested into `state.messages`.
2. `supervisor_node` (`llama3.1:8b`) receives the full conversation history.
3. System prompt instructs the model:
   *"If the user's latest message is a follow-up, retry, or referral, resolve the context dynamically from previous turns to determine the exact substantive task to execute. Do NOT invent unrelated tasks."*
4. The LLM identifies the prior Fibonacci task, generates routing directive:
   ```json
   {
     "user_intent": "Compute Fibonacci numbers up to 10 and execute in Docker sandbox",
     "next": "coder_agent",
     "instruction": "Execute the Fibonacci script in the Docker container."
   }
   ```
5. `coder_agent` re-runs the code in the container, and `chief_reviewer` finalizes.

### 4. Expected Output
* Re-runs the exact Fibonacci computation cleanly.
* **No hallucination** of unrequested pressure vessels.
* **No repetition** of `"redo it"` under multiple agents.

---

## 🎬 DEMO 5: Multimodal Drawing & Ultrasonic Grid Ingestion

### 1. The Analogy
> **"The Industrial Radiologist & Ultrasound Specialist"**:
> Ultrasonic thickness gauges produce grids of hundreds of coordinate measurements across a steel pipe. AegisForge ingests the raw coordinate grid (or P&ID drawing image) and pinpoints the exact coordinates of internal pitting corrosion.

### 2. User Input
* **Where:** Tab 1: **Sovereign Copilot**
* **Action:**
  1. Click **"Attach Industrial File"** drag-and-drop zone.
  2. Upload any sample grid or drawing (e.g., from `data/` or any `.csv`/`.xlsx` or `.png`/`.jpg`).
  3. Prompt:
     ```text
     Analyze the attached thickness data for localized pitting corrosion and report structural compliance.
     ```

### 3. Internal Working
1. `frontend/app.py` saves file to `data/uploads/`.
2. `backend/app_backend.py` calls `SecureFileIO.read_file`:
   - If image (`.png`, `.jpg`, `.tiff`): Dispatches to `InspectionExtractorTool` with **EasyOCR** on local GPU.
   - If spreadsheet (`.csv`, `.xlsx`): Dispatches to `thickness_grid_analyzer.py`.
3. Matrix statistical analysis computes:
   - Minimum thickness $t_{min}$
   - Mean thickness and standard deviation
   - Worst-case pitting coordinates (Row $X$, Column $Y$)
4. `vision_agent` summarizes coordinate anomalies and hands off to `asme_calculator` to check if minimum thickness violates safety thresholds.

### 4. Expected Output
```markdown
📊 Coordinate Thickness Matrix Analysis
• File Ingested: thickness_grid.csv
• Total Inspection Points: 100 coordinates
• Mean Wall Thickness: 139.84 mm
• Critical Localized Thinning Detected: Point (Row 4, Col 7) = 137.90 mm
• Safety Alert: Localized spot is below t_req (138.57 mm) by 0.67 mm. Level 1 FFS Assessment Recommended.
```

---

## 🏅 Why This Wins the Hackathon (Key Talking Points)

| Feature | AegisForge-AI | Typical Student Hackathon Project |
| :--- | :--- | :--- |
| **Data Privacy** | 100% Air-Gapped, Zero Cloud Egress, Local GPU Execution | Wrapper around OpenAI / Claude API keys |
| **Physics Grounding** | Deterministic ASME Section VIII & API 510 math engines | Prompting ChatGPT to guess calculations |
| **Security & Safety** | AST scanning + `--network none` Docker sandbox container | `eval()` or `exec()` directly on host laptop |
| **Governance** | Indian PSU CVC Directives, GFR 2017 & DoP matrix integration | Generic text generation |
| **Auditability** | Cryptographic SHA-256 chained ledger & verified Word/PDFs | Ephemeral chatbot text |
| **Multi-Agent Flow** | LangGraph orchestration with Reviewer feedback loop | Single LLM prompt chain |
