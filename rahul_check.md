# 🛡️ AegisForge-AI: Complete End-to-End Architecture & System Flow Specification
**Document ID:** `rahul_check`  
**Target Audience:** Engineering Leads, Architecture Reviewers, PSU Process Safety Auditors  
**System:** AegisForge-AI — 100% Air-Gapped Sovereign Industrial AI & Engineering Workbench  
**Root Path:** `c:\Users\DELL\Desktop\SIH`  

---

## 1. Executive Summary & Core System Guarantees

AegisForge-AI is an air-gapped, zero-cloud sovereign industrial engineering platform purpose-built for Indian Public Sector Undertakings (IOCL, ONGC, GAIL, NTPC, etc.). It automates statutory asset integrity audits, engineering calculations (ASME Section VIII, API 510), compliance justification (CVC guidelines, DOP Clause 4.2), and tamper-evident official document generation.

### Key Guarantees:
1. **100% Air-Gapped & Sovereign**: Zero telemetry or external API calls. All LLMs, VLMs, and OCR models run on `localhost:11434` or local PyTorch runtimes.
2. **Deterministic Physics Enforcement**: Critical safety equations ($t_{\text{min}}$, safety delta, API 510 remaining service life, derated MAWP) are calculated using pure deterministic Python mathematics rather than probabilistic LLM hallucinations.
3. **Cryptographic Tamper Attestation**: Every generated Microsoft Word (`.docx`) and Adobe PDF (`.pdf`) document is automatically stamped with a SHA-256 cryptographic hash.
4. **Zero Host Pollution**: Storage is strictly encapsulated within the project directory. The model pool uses an NTFS Windows Junction (`model_pool\ollama` ➔ `C:\Users\DELL\.ollama\models`) ensuring portability and clean uninstallation.

---

## 2. End-to-End 7-Layer Structural Hierarchy

AegisForge-AI is structured into 7 distinct, decoupled layers:

```mermaid
graph TD
    classDef l7 fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef l6 fill:#065f46,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef l5 fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef l4 fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;
    classDef l3 fill:#831843,stroke:#ec4899,stroke-width:2px,color:#fff;
    classDef l2 fill:#134e4a,stroke:#14b8a6,stroke-width:2px,color:#fff;
    classDef l1 fill:#1f2937,stroke:#64748b,stroke-width:2px,color:#fff;
    classDef l0 fill:#0f172a,stroke:#475569,stroke-width:2px,color:#fff;

    subgraph L7["Layer 7: Central Operating Gateway & User Interfaces"]
        L7_CLI["CLI & Central Engine<br/>(main.py)"]
        L7_UI["Streamlit 6-Tab Workbench<br/>(frontend/app.py)"]
    end
    class L7,L7_CLI,L7_UI l7;

    subgraph L6["Layer 6: Output Emission & Cryptographic Attestation"]
        L6_DOCX["Word .docx Generator<br/>(output_generation/docx_generator.py)"]
        L6_PDF["PDF .pdf Generator<br/>(output_generation/pdf_generator.py)"]
        L6_HASH["SHA-256 Tamper Attestation"]
    end
    class L6,L6_DOCX,L6_PDF,L6_HASH l6;

    subgraph L5["Layer 5: Routing & Multi-Agent Orchestration"]
        L5_MVP["Golden Path Orchestrator<br/>(agent_orchestrator/orchestrator_mvp.py)"]
        L5_ROUTER["Sovereign Model Router<br/>(models/router/model_router.py)"]
        L5_GRAPH["LangGraph State Machine<br/>(agent_orchestrator/graph.py)"]
    end
    class L5,L5_MVP,L5_ROUTER,L5_GRAPH l5;

    subgraph L4["Layer 4: Sovereign Model Pool & Local Serving"]
        L4_QWEN["Coding Agent: Qwen2.5-Coder:1.5b"]
        L4_R1["Reasoning Agent: DeepSeek-R1:1.5b"]
        L4_LLAMA["Summary Agent: Llama-3.2:3b"]
        L4_VLM["Vision Agent: Moondream / EasyOCR"]
        L4_MGR["Model Hub & Downloader<br/>(models/model_downloader.py)"]
    end
    class L4,L4_QWEN,L4_R1,L4_LLAMA,L4_VLM,L4_MGR l4;

    subgraph L3["Layer 3: Deterministic Physics & Air-Gapped Tools"]
        L3_ASME["ASME Section VIII UG-27 Calculator<br/>(tools/asme_calculator.py)"]
        L3_BOX["Subprocess Python Sandbox<br/>(tools/sandbox.py)"]
        L3_DOC["Unified Doc Tool<br/>(tools/doc_generator.py)"]
        L3_RAG["Local File RAG<br/>(tools/rag.py)"]
        L3_IO["Safe File I/O<br/>(tools/file_io.py)"]
    end
    class L3,L3_ASME,L3_BOX,L3_DOC,L3_RAG,L3_IO l3;

    subgraph L2["Layer 2: Ingestion & Perception Preprocessing"]
        L2_INGEST["OCR Log Ingestion & Regex Extractor<br/>(ingestion/extract_inspection_data.py)"]
        L2_VIS["Multi-Modal Vision Adapter<br/>(models/vision_models/multimodal.py)"]
    end
    class L2,L2_INGEST,L2_VIS l2;

    subgraph L1["Layer 1: Unified Data Contracts & Schemas"]
        L1_PYD["Pydantic State Schemas<br/>(schemas/mvp_schema.py)"]
        L1_STATE["LangGraph AgentState<br/>(agent_orchestrator/state.py)"]
    end
    class L1,L1_PYD,L1_STATE l1;

    subgraph L0["Layer 0: Sovereign Runtime & Isolation"]
        L0_CONF["Root Anchoring & Paths<br/>(config/settings.py)"]
        L0_SCRIPTS["Offline Scripts & Daemons<br/>(scripts/run_ollama_local.bat)"]
        L0_JUNCTION["Windows Junction Storage<br/>(model_pool/ollama -> C:\\Users\\DELL\\.ollama\\models)"]
    end
    class L0,L0_CONF,L0_SCRIPTS,L0_JUNCTION l0;

    L7 --> L6
    L7 --> L5
    L5 --> L4
    L5 --> L3
    L5 --> L2
    L2 & L3 & L4 & L5 & L6 --> L1
    L1 & L2 & L3 & L4 & L5 & L6 & L7 --> L0
```

---

## 3. Complete Component & File-by-File Directory Map

Every folder, module, script, and artifact mapped to its location in the repository:

```mermaid
graph LR
    classDef rootBox fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef modBox fill:#1e293b,stroke:#94a3b8,stroke-width:1px,color:#f8fafc;
    classDef fileBox fill:#334155,stroke:#cbd5e1,stroke-width:1px,color:#f1f5f9;

    Root["c:\\Users\\DELL\\Desktop\\SIH"]:::rootBox

    %% Root Controllers
    Root --> MainPy["main.py (Central Gateway & CLI)"]:::fileBox
    Root --> RunBat["run_app.bat (1-Click UI Launcher)"]:::fileBox
    Root --> ActPs1["activate_project.ps1 (Env Setup)"]:::fileBox

    %% Frontend
    Root --> D_Frontend["frontend/"]:::modBox
    D_Frontend --> AppPy["app.py (Streamlit 6-Tab App)"]:::fileBox

    %% Agent Orchestrator
    Root --> D_Orch["agent_orchestrator/"]:::modBox
    D_Orch --> OrchMVP["orchestrator_mvp.py (Golden Path Pipeline)"]:::fileBox
    D_Orch --> GraphPy["graph.py (LangGraph State Machine)"]:::fileBox
    D_Orch --> RouterPy["router.py (Node Dispatcher)"]:::fileBox
    D_Orch --> StatePy["state.py (AgentState TypedDict)"]:::fileBox
    D_Orch --> ValPy["validator.py (Self-Correction Loop)"]:::fileBox

    %% Models
    Root --> D_Models["models/"]:::modBox
    D_Models --> M_Downloader["model_downloader.py (Pull / Status)"]:::fileBox
    D_Models --> D_ModRouter["router/model_router.py (Task Classifier)"]:::fileBox
    D_Models --> D_Coding["coding_models/coding.py (Qwen-Coder)"]:::fileBox
    D_Models --> D_Reasoning["reasoning_models/reasoning.py (DeepSeek-R1)"]:::fileBox
    D_Models --> D_Summary["summary_models/summary.py (Llama-3.2)"]:::fileBox
    D_Models --> D_Vision["vision_models/multimodal.py (Moondream)"]:::fileBox

    %% Tools
    Root --> D_Tools["tools/"]:::modBox
    D_Tools --> T_ASME["asme_calculator.py (UG-27 Math Engine)"]:::fileBox
    D_Tools --> T_Sandbox["sandbox.py (Subprocess Sandbox)"]:::fileBox
    D_Tools --> T_Doc["doc_generator.py (Doc Tool API)"]:::fileBox
    D_Tools --> T_RAG["rag.py (Air-Gapped Search)"]:::fileBox
    D_Tools --> T_FileIO["file_io.py (Safe JSON/CSV/TXT)"]:::fileBox

    %% Ingestion
    Root --> D_Ingestion["ingestion/"]:::modBox
    D_Ingestion --> ExtrPy["extract_inspection_data.py (Log Parser)"]:::fileBox

    %% Schemas
    Root --> D_Schemas["schemas/"]:::modBox
    D_Schemas --> SchemaMVP["mvp_schema.py (Pydantic Models)"]:::fileBox

    %% Output Generation
    Root --> D_Output["output_generation/"]:::modBox
    D_Output --> DocxGen["docx_generator.py (Native Word Generator)"]:::fileBox
    D_Output --> PdfGen["pdf_generator.py (Native PDF Generator)"]:::fileBox

    %% Config & Scripts & Storage
    Root --> D_Config["config/settings.py (Anchors & Paths)"]:::fileBox
    Root --> D_Scripts["scripts/"]:::modBox
    D_Scripts --> S_RunOllama["run_ollama_local.bat (Ollama Daemon)"]:::fileBox
    D_Scripts --> S_Setup["setup_models.py (Automated Puller)"]:::fileBox
    D_Scripts --> S_Clean["clean_models.bat / .py (Purge)"]:::fileBox
    Root --> D_Pool["model_pool/ (Junction -> .ollama/models)"]:::modBox
    Root --> D_Data["data/ (output/ & uploads/)"]:::modBox
```

---

## 4. Flow 1: Golden Path End-to-End Pipeline (Step-by-Step)

The Golden Path executes the complete pipeline: field inspection log ingestion ➔ ASME UG-27 mathematical verification ➔ DeepSeek-R1 sovereign reasoning ➔ Word and PDF compilation with cryptographic attestation.

```mermaid
sequenceDiagram
    autonumber
    actor Engineer as PSU Inspection Engineer
    participant UI as frontend/app.py (Tab 2)
    participant Orchestrator as agent_orchestrator/orchestrator_mvp.py
    participant Ingestion as ingestion/extract_inspection_data.py
    participant MathEngine as tools/asme_calculator.py
    participant ReasoningLLM as models/reasoning_models/reasoning.py (DeepSeek-R1)
    participant DocEmitter as output_generation/docx_generator.py & pdf_generator.py
    participant FileStorage as data/output/

    Engineer->>UI: Selects sample or uploads field inspector log (.txt)
    Engineer->>UI: Clicks "Run Sovereign Pipeline"
    
    UI->>Orchestrator: run_mvp_pipeline(input_source)
    
    %% Step 1: Ingestion
    Note over Orchestrator,Ingestion: Step 1: Ingestion & Regex Parameter Extraction
    Orchestrator->>Ingestion: parse_inspection_input(raw_log_path)
    Ingestion-->>Orchestrator: InspectionInput(equipment_id="11-V-102", t_act=138.20mm, P=14.5MPa, ...)
    
    %% Step 2: Math
    Note over Orchestrator,MathEngine: Step 2: Deterministic ASME UG-27 Verification
    Orchestrator->>MathEngine: evaluate_vessel_integrity(InspectionInput)
    Note right of MathEngine: t_req = (P*R)/(S*E - 0.6*P) + CA<br/>t_req = 138.57 mm<br/>delta = 138.20 - 138.57 = -0.37 mm<br/>is_breach = True, Remaining Life = -0.49 yrs
    MathEngine-->>Orchestrator: CalculationOutput(t_req_mm=138.57, delta_mm=-0.37, is_breach=True, status="CRITICAL_BREACH")
    
    %% Step 3: Reasoning
    Note over Orchestrator,ReasoningLLM: Step 3: Sovereign CVC & DOP Justification Synthesis
    Orchestrator->>ReasoningLLM: call_local_reasoning_model(InspectionInput, CalculationOutput)
    ReasoningLLM->>ReasoningLLM: Local DeepSeek-R1 (127.0.0.1:11434) formats CVC DOP 4.2 emergency justification
    ReasoningLLM-->>Orchestrator: ReasoningOutput(executive_summary, cvc_guideline_clause, recommended_action, estimated_cost="Rs. 88.0 Lakhs")
    
    %% Step 4: Emission
    Note over Orchestrator,DocEmitter: Step 4: Office Deliverable Compilation & Tamper Attestation
    Orchestrator->>DocEmitter: generate_approval_nfa_docx(...) & generate_approval_nfa_pdf(...)
    DocEmitter->>FileStorage: Writes IOCL_Emergency_Approval_Note.docx & .pdf
    DocEmitter->>DocEmitter: Computes SHA-256 cryptographic hashes
    DocEmitter-->>Orchestrator: File paths + SHA-256 attestation hashes
    
    Orchestrator-->>UI: FinalNFAPayload (Complete Verified State)
    UI->>UI: Displays Telemetry Metrics, Code Breach Badges & LaTeX Formula Proof
    UI-->>Engineer: Renders 1-Click DOCX & PDF Download Buttons with File Integrity Attestation
```

---

## 5. Flow 2: Sovereign Dynamic Model Router & Execution Engine

When a prompt or task is entered in Tab 1 (`frontend/app.py`) or via `main.py route --prompt "..."`:

```mermaid
flowchart TD
    classDef inputNode fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef classNode fill:#065f46,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef modelNode fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef toolNode fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;
    classDef outNode fill:#0f172a,stroke:#475569,stroke-width:2px,color:#fff;

    UserPrompt["User Prompt / File Upload<br/>(UI Tab 1 or main.py route)"]:::inputNode
    Classifier{"Task Classifier<br/>(models/router/model_router.py)"}:::classNode

    UserPrompt --> Classifier

    %% Branches
    Classifier -- "Coding Keywords<br/>(python, def, script, modbus, sql)" --> CodingBranch["Coding Model Node<br/>qwen2.5-coder:1.5b"]:::modelNode
    Classifier -- "Reasoning Keywords<br/>(asme, cvc, breach, t_min, mawp)" --> ReasoningBranch["Reasoning Model Node<br/>deepseek-r1:1.5b"]:::modelNode
    Classifier -- "Summary / General<br/>(summarize, points, safety notes)" --> SummaryBranch["Summary Model Node<br/>llama3.2:3b"]:::modelNode
    Classifier -- "Image / Diagram Uploaded<br/>(png, jpg, svg, P&ID)" --> VisionBranch["Vision VLM Node<br/>moondream / EasyOCR"]:::modelNode

    %% Executions
    CodingBranch --> CodeExtract["Extract ```python Code Block"]:::toolNode
    CodeExtract --> SandboxExec["Air-Gapped Subprocess Sandbox<br/>(tools/sandbox.py)<br/>Timeout: 15s | Isolated Subprocess"]:::toolNode
    SandboxExec --> SandboxResult["Display stdout / stderr & Return Code"]:::outNode

    ReasoningBranch --> IntentCheck{"Prompt Intent Check:<br/>Wants DOCX / PDF?"}:::classNode
    IntentCheck -- "Yes ('need docx', 'need pdf')" --> DocGen["tools/doc_generator.py<br/>Compiles Word / PDF Deliverables"]:::toolNode
    DocGen --> DownloadBtns["1-Click Native DOCX & PDF Download<br/>with SHA-256 Hash"]:::outNode
    IntentCheck -- "No (Pure Text Reasoning)" --> TextOutput["Render Markdown Rationale & Formula Proof"]:::outNode

    SummaryBranch --> SummaryOutput["Render Structured Bulleted Deliverable"]:::outNode
    VisionBranch --> VisionOutput["Render Tag / Visual Inspection Analysis"]:::outNode
```

---

## 6. Flow 3: LangGraph Multi-Agent State Machine Flow

When multi-agent state orchestration is executed (`agent_orchestrator/graph.py`):

```mermaid
stateDiagram-v2
    [*] --> START
    START --> RouterNode : initial_state (user_prompt, files, attempts=0)

    state RouterNode {
        [*] --> ClassifyPrompt
        ClassifyPrompt --> AssignRoute
    }

    RouterNode --> CodingNode : route == 'coding'
    RouterNode --> ReasoningNode : route == 'reasoning'
    RouterNode --> SummaryNode : route == 'summary'
    RouterNode --> MultimodalNode : route == 'multimodal'
    RouterNode --> MultimodalNode : route == 'pipeline' (Sequential Chain)

    state "Sequential Golden Chain (if route == 'pipeline')" as PipelineSeq {
        MultimodalNode --> CodingNode : next_after_multimodal
        CodingNode --> ReasoningNode : next_after_coding
        ReasoningNode --> SummaryNode : next_after_reasoning
    }

    MultimodalNode --> ValidatorNode : route != 'pipeline'
    CodingNode --> ValidatorNode : route != 'pipeline'
    ReasoningNode --> ValidatorNode : route != 'pipeline'
    SummaryNode --> ValidatorNode

    state ValidatorNode {
        [*] --> CheckQuality
        CheckQuality --> AssessAttempts
    }

    ValidatorNode --> CodingNode : retry coding (attempts < 3)
    ValidatorNode --> ReasoningNode : retry reasoning (attempts < 3)
    ValidatorNode --> SummaryNode : retry summary (attempts < 3)
    ValidatorNode --> MultimodalNode : retry multimodal (attempts < 3)
    ValidatorNode --> END : validation_decision == 'end'
    END --> [*]
```

---

## 7. Flow 4: Sovereign Storage & Air-Gapped Windows Junction Model Pool

How model storage, downloads, and inference processes interact with the file system:

```mermaid
flowchart TD
    classDef disk fill:#1e293b,stroke:#475569,stroke-width:2px,color:#fff;
    classDef project fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef proc fill:#065f46,stroke:#10b981,stroke-width:2px,color:#fff;

    subgraph HostSystem["Windows Host Storage"]
        OllamaDefault["C:\\Users\\DELL\\.ollama\\models<br/>(Native Windows Ollama Storage)"]:::disk
    end

    subgraph ProjectWorkspace["Project Root: c:\\Users\\DELL\\Desktop\\SIH\\"]
        ModelPool["model_pool/"]:::project
        Junction["model_pool/ollama<br/>(Windows NTFS Junction Link /J)"]:::project
        EasyOCR_Dir["model_pool/easyocr/<br/>(CRAFT & CRNN .pth weights)"]:::project
        DataDir["data/output/ & data/uploads/"]:::project
    end

    subgraph RuntimeProcesses["Local Subprocesses (Air-Gapped, Localhost Only)"]
        OllamaDaemon["Ollama Local Daemon<br/>(127.0.0.1:11434)<br/>Launched via scripts/run_ollama_local.bat"]:::proc
        StreamlitUI["Streamlit UI (Port 8501)<br/>Launched via run_app.bat"]:::proc
        PythonCLI["Master Gateway (main.py)"]:::proc
    end

    Junction -. "Zero-Copy NTFS Pointer" .-> OllamaDefault
    ModelPool --> Junction
    ModelPool --> EasyOCR_Dir

    OllamaDaemon -->|"Reads/Writes Weights"| OllamaDefault
    StreamlitUI -->|"API Requests (localhost:11434)"| OllamaDaemon
    PythonCLI -->|"API Requests (localhost:11434)"| OllamaDaemon
    StreamlitUI -->|"Writes Output Files"| DataDir
    PythonCLI -->|"Writes Output Files"| DataDir
```

---

## 8. Comprehensive File-by-File Technical Directory & Contract Matrix

| File Path | Layer | Primary Class / Function | Inputs Received | Internal Execution | Outputs Emitted | Downstream Consumers |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `main.py` | **L7** | `AegisForgeCentralEngine`, CLI entry | CLI arguments (`sys.argv`), interactive menu choices | Central coordinator calling all layers (Status, Pipeline, Router, Math, Sandbox, UI) | Console reports, triggers downstream processes | User, Terminal, CI/CD |
| `frontend/app.py` | **L7** | Streamlit Web App (6 Tabs) | User text, uploaded logs/images, slider values | Renders reactive UI, triggers models, compiles downloads, displays math proofs | Interactive DOM, generated `.docx`/`.pdf` download streams | End-user, Refinery Engineers |
| `agent_orchestrator/orchestrator_mvp.py` | **L5** | `run_mvp_pipeline()`, `call_local_reasoning_model()` | `input_source` (path or string), `model_name` | Coordinates Ingestion ➔ Math ➔ DeepSeek-R1 ➔ DOCX/PDF generation | `FinalNFAPayload` (Pydantic model) | `main.py`, `frontend/app.py` (Tab 2) |
| `agent_orchestrator/graph.py` | **L5** | `build_graph()`, routing edge functions | Model handlers (`router_llm`, `coding_llm`, etc.) | Compiles LangGraph `StateGraph(AgentState)` with conditional routing & feedback | Compiled LangGraph runnable graph | `main.py` (`run_langgraph()`), test suites |
| `agent_orchestrator/router.py` | **L5** | `router_node()`, `route_decision()` | `AgentState`, router LLM | Analyzes prompt intent; assigns target route (`coding`, `reasoning`, etc.) | Updated `AgentState["route"]` | LangGraph StateGraph |
| `agent_orchestrator/validator.py` | **L5** | `validator_node()`, `validation_decision()` | `AgentState` | Inspects model outputs for quality/errors; triggers loopback or `END` | Updated `AgentState["is_valid"]`, `AgentState["attempts"]` | LangGraph StateGraph |
| `agent_orchestrator/state.py` | **L1** | `AgentState(TypedDict)` | N/A (Schema definition) | Defines typed dictionary representing multi-agent shared state | Data contract | LangGraph graph, all agent nodes |
| `schemas/mvp_schema.py` | **L1** | `InspectionInput`, `CalculationOutput`, `ReasoningOutput`, `FinalNFAPayload` | Pydantic fields | Defines strict schemas, data validation, and default parameters | Validated Pydantic objects | All pipeline layers (L2, L3, L4, L5, L6, L7) |
| `ingestion/extract_inspection_data.py` | **L2** | `parse_inspection_input()` | Raw inspection report (`.txt` path or raw text) | Robust regex parsing of equipment tags, locations, materials, thicknesses, corrosion rates | `InspectionInput` instance | `orchestrator_mvp.py`, `main.py` |
| `tools/asme_calculator.py` | **L3** | `evaluate_vessel_integrity()` | `InspectionInput` | Computes ASME Sec VIII Div 1 UG-27 ($t_{min}$), delta ($\Delta$), API 510 remaining life, MAWP | `CalculationOutput` instance | `orchestrator_mvp.py`, `frontend/app.py` (Tab 3), `main.py` |
| `tools/sandbox.py` | **L3** | `execute_python_code()` | Python script string, timeout seconds | Spawns isolated subprocess (`sys.executable`), captures stdout/stderr, enforces timeout | Dict (`success`, `stdout`, `stderr`, `returncode`) | `frontend/app.py` (Tab 4 & Tab 1), `main.py` |
| `tools/doc_generator.py` | **L3** | `generate_docx_deliverable()`, `generate_pdf_deliverable()` | `InspectionInput`, `CalculationOutput`, `ReasoningOutput` | Wraps Layer 6 emission into callable tools; computes SHA-256 hashes | Dict (`path`, `sha256`, `size_bytes`, `filename`) | `frontend/app.py` (Tab 1 & Tab 3), agents |
| `tools/rag.py` | **L3** | `search_local_knowledge()` | Query string, max results | Scans local `sample_data/` files without external vectors/APIs | Formatted markdown text with source citations | Multi-agent research, `main.py` |
| `tools/file_io.py` | **L3** | `read_or_write_file()` | Filepath, mode, data, type | Safe air-gapped reader/writer for JSON, CSV, and text files | File contents or boolean success flag | Data persistence, pipeline tools |
| `models/router/model_router.py` | **L5/L4**| `SovereignModelRouter`, `LocalModelHandler` | Prompt string, optional image path, model override | Heuristic keyword classification ➔ Dispatches to local Ollama model | Dict (`task_type`, `model_used`, `response`, `success`) | `main.py`, `frontend/app.py` (Tab 1) |
| `models/model_downloader.py` | **L4** | `pull_ollama_model_stream()`, `install_easyocr_models()`, `is_model_installed()` | Model ID string (e.g. `deepseek-r1:1.5b`) | Communicates with Ollama daemon or PyTorch cache; manages downloads & deletes | Generator yielding download % progress chunks | `frontend/app.py` (Tab 5), `main.py`, `setup_models.py` |
| `models/coding_models/coding.py` | **L4** | `coding_node()` | `AgentState`, coding LLM (`qwen2.5-coder`) | Generates verified Python scripts & SCADA automation logic | Updated `AgentState["messages"]` | LangGraph StateGraph |
| `models/reasoning_models/reasoning.py` | **L4** | `reasoning_node()` | `AgentState`, reasoning LLM (`deepseek-r1`) | Synthesizes regulatory CVC justification & engineering rationale | Updated `AgentState["messages"]` | LangGraph StateGraph |
| `models/summary_models/summary.py` | **L4** | `summary_node()` | `AgentState`, summary LLM (`llama3.2`) | Compiles concise executive summaries & board resolution memos | Updated `AgentState["messages"]` | LangGraph StateGraph |
| `models/vision_models/multimodal.py` | **L4** | `multimodal_node()` | `AgentState`, vision LLM (`moondream`) | Analyzes P&ID drawings, inspection photos, and instrument bubbles | Updated `AgentState["messages"]` | LangGraph StateGraph |
| `output_generation/docx_generator.py` | **L6** | `generate_approval_nfa_docx()`, `compute_file_sha256()` | `InspectionInput`, `CalculationOutput`, `ReasoningOutput`, `output_path` | Generates official styled Word `.docx` with IOCL headers, tables, callout boxes | Emitted `.docx` binary file + SHA-256 hash | `orchestrator_mvp.py`, `tools/doc_generator.py` |
| `output_generation/pdf_generator.py` | **L6** | `generate_approval_nfa_pdf()`, `compute_file_sha256()` | `InspectionInput`, `CalculationOutput`, `ReasoningOutput`, `output_path` | Generates official PDF document with ReportLab styling, metadata, and hash | Emitted `.pdf` binary file + SHA-256 hash | `orchestrator_mvp.py`, `tools/doc_generator.py` |
| `config/settings.py` | **L0** | Path constants, model registry, disk checks | N/A (Configuration file) | Resolves `PROJECT_ROOT`, binds `MODEL_POOL_DIR`, `OLLAMA_HOST`, checks disk space | Environment constants and helper functions | Every module in the system |
| `scripts/run_ollama_local.bat` | **L0** | Local Ollama Daemon Launcher | N/A (Batch script) | Sets `OLLAMA_MODELS=model_pool\ollama` and starts `ollama serve` | Background local LLM API server on port 11434 | All LLM inference |
| `scripts/setup_models.py` | **L0** | Full Model Preflight & Puller | CLI execution | Preflight disk check (6GB min) ➔ Pulls Qwen, DeepSeek, Llama, Moondream, EasyOCR | Initialized local model pool | Developers, automated deployment |
| `scripts/clean_models.bat` | **L0** | Zero-Trace Storage Purge | User confirmation | Safely purges model weights to reclaim 100% disk space | Cleaned workspace | System administrators |
| `run_app.bat` | **L0** | 1-Click Application Launcher | User double-click | Starts Ollama daemon (if stopped) and launches Streamlit dashboard on port 8501 | Active browser UI | End-users |

---

## 9. Quick Verification & Execution Reference

To run or verify any component from terminal:

```powershell
# 1. Check Full System Health & Model Pool Status
python main.py status

# 2. Run the Golden Path Pipeline (Inspect -> Math -> DeepSeek-R1 -> Word/PDF)
python main.py run-golden-path

# 3. Test the Dynamic Model Router with a prompt
python main.py route --prompt "Write a Python parser for Modbus RTU telemetry packets."

# 4. Run ASME Section VIII UG-27 Deterministic Math Check
python main.py calc --p 14.5 --r 1200 --s 138 --t_actual 138.20

# 5. Run Isolated Python Sandbox
python main.py sandbox --code "print('Air-gapped verification success!')"

# 6. Run Complete Automated Test Suite
python main.py test

# 7. Launch Unified Streamlit Workbench
python main.py ui
# or simply double-click run_app.bat
```
