# AegisForge-AI: Production-Grade Architecture & Flow Analysis

This document outlines the **fully production-grade system architecture** of AegisForge-AI. Based on advanced design requirements, this architecture incorporates:
1. **Master Supervisor Routing:** All intents (Coding, Summary, Reasoning, etc.) are now managed by a central Master Supervisor Agent.
2. **LangGraph Short-Term Memory:** Implemented across the pipeline to give agents context of previous turns and intermediate states.
3. **Retrieval-Augmented Generation (RAG):** Added a dedicated RAG Agent and a Vector Database (e.g., Milvus/ChromaDB) for semantic search over historical manuals and guidelines.

---

## 1. System Components

- **Short-Term Memory (LangGraph Checkpointer):** Acts as the brain of the workflow. The Master Supervisor and all child workers read/write to this memory state, enabling multi-step contextual awareness.
- **Data Layer (Vector & Relational DBs):** 
  - **Vector DB:** Stores embeddings of API manuals, CVC guidelines, and past inspection reports for the RAG Agent.
  - **Relational DB (PostgreSQL):** Stores historical ERP and maintenance logs.
- **Master Supervisor Agent:** Dispatches tasks to specific specialist agents (Coding Agent, Summary Agent, RAG Agent, etc.) based on the classifier's intent.
- **Deterministic Tools (ASME Calculator):** Provides calculation-based answers directly from the formula logic without secondary LLM verification to ensure purely deterministic outputs.

---

## 2. Production-Grade Architecture Map

Below is the highly scalable, production-ready architecture demonstrating the flow between Memory, Data, Agents, and Tools.

```mermaid
graph TD
    %% Styling
    classDef default fill:#1e293b,stroke:#475569,stroke-width:2px,color:#f8fafc;
    classDef ui fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:#fff;
    classDef router fill:#8b5cf6,stroke:#7c3aed,stroke-width:2px,color:#fff;
    classDef memory fill:#ec4899,stroke:#db2777,stroke-width:2px,color:#fff;
    classDef db fill:#059669,stroke:#047857,stroke-width:2px,color:#fff;
    classDef agent fill:#0f766e,stroke:#14b8a6,stroke-width:2px,color:#fff;
    classDef tools fill:#4b5563,stroke:#374151,stroke-width:2px,color:#fff;
    classDef models fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:#fff;

    %% FRONTEND LAYER
    subgraph Frontend [UI Layer: Streamlit Dashboard]
        User([Operator / Engineer]) --> Workbench[💬 Workbench Tab]:::ui
        User --> CalcUI[🧮 Calculator Tab]:::ui
        User --> ModelHub[📦 Model Hub Tab]:::ui
    end

    %% DISPATCH & MEMORY LAYER
    subgraph Core_Orchestration [Central Orchestration & State]
        Workbench --> Classifier[AI Intent Classifier]:::router
        Classifier --> MasterSupervisor[Master Supervisor Agent]:::router
        
        %% Short Term Memory
        Memory[(LangGraph Short-Term Memory<br/>Checkpointer / Redis)]:::memory
        MasterSupervisor <-->|Read/Write State| Memory
    end

    %% PRODUCTION DATA LAYER
    subgraph Data_Layer [Production Databases]
        VectorDB[(Vector Database<br/>Milvus / ChromaDB)]:::db
        SQLDB[(Relational DB / ERP<br/>PostgreSQL)]:::db
    end

    %% INFRASTRUCTURE LAYER
    subgraph Infrastructure [Independent Tools & Models]
        Calculator[ASME UG-27 Calculator Engine]:::tools
        Sandbox[Air-Gapped Python Sandbox]:::tools
        DocGen[DOCX / PDF Document Generator]:::tools
        Ollama[(Local Ollama Model Pool)]:::models
    end

    %% UI CALCULATOR (Direct Output)
    CalcUI --> Calculator
    Calculator -->|Direct Math Output| User

    %% PARALLEL AGENTIC DISPATCH
    subgraph LangGraph_Workers [Parallel Specialist Agents]
        MasterSupervisor -->|Software Tasks| CodingAgent[Coding Agent]:::agent
        MasterSupervisor -->|Summarization| SummaryAgent[Summary Agent]:::agent
        MasterSupervisor -->|Semantic Search| RAGAgent[RAG Retrieval Agent]:::agent
        MasterSupervisor -->|Text / OCR| InspectionWorker[Inspection Worker]:::agent
        MasterSupervisor -->|Blueprints| VisionWorker[Vision Worker]:::agent
    end
    
    %% AGENT TOOL & DB CONNECTIONS
    CodingAgent --> Sandbox
    RAGAgent <--> VectorDB
    InspectionWorker <--> SQLDB

    %% MEMORY LINKING (All agents share context)
    CodingAgent -.- Memory
    SummaryAgent -.- Memory
    RAGAgent -.- Memory
    InspectionWorker -.- Memory
    VisionWorker -.- Memory

    %% SEQUENTIAL ENGINEERING CORE
    subgraph Engineering_Core [Strict Sequential Engineering Pipeline]
        InspectionWorker --> SyncGate{Data Sync Gate}
        VisionWorker --> SyncGate
        RAGAgent --> SyncGate
        
        SyncGate --> MathWorker[Math Worker]:::agent
        MathWorker --> Calculator
        
        %% Direct Hand-off to Compliance
        MathWorker -->|Calculated Breach Data| ComplianceWorker[Compliance Worker]:::agent
    end

    %% FINAL REVIEW & EMISSION
    ComplianceWorker --> ChiefReviewer[Chief Reviewer Agent]:::agent
    CodingAgent --> ChiefReviewer
    SummaryAgent --> ChiefReviewer

    ChiefReviewer -->|Approved| DocGen
    ChiefReviewer -->|Rejected / Error| HaltNode([Halt Pipeline])
    
    DocGen --> Output([Final Tamper-Proof Document Delivery])

    %% BACKGROUND MODEL DEPENDENCIES
    MasterSupervisor -.->|Inference| Ollama
    CodingAgent -.->|Inference| Ollama
    RAGAgent -.->|Inference| Ollama
```

## 3. Key Upgrades Explained

### A. The Master Supervisor & Unified Workflow
Instead of the classifier sending tasks out of the LangGraph ecosystem, **everything** is now managed by a LangGraph `Master Supervisor Agent`. If the user asks for code, the Supervisor hands it to the `Coding Agent`. If the user asks a general question, it hands it to the `Summary Agent`. 

### B. Short-Term Memory (LangGraph Checkpointer)
The pink **Memory** module represents LangGraph's `checkpointer` (often backed by SQLite or Redis in production). 
- **How it connects:** The Supervisor and all worker agents read from and write to this shared state. If the user refers to "that vessel from my last message", the Supervisor queries the Short-Term Memory to provide the exact context to the workers.

### C. RAG and Vector Databases
A new **RAG Retrieval Agent** is connected directly to a **Vector Database** (green). 
- **Usage:** When the `Compliance Worker` or `Summary Agent` needs to know the exact text of "OISD Standard 116", the Supervisor asks the RAG Agent to perform a semantic similarity search in the Vector DB. The RAG Agent retrieves the chunks and places them into the Short-Term Memory for the other agents to use.

### D. Purely Deterministic Calculator Output
The ASME calculation engine outputs its answers purely based on its internal mathematical logic. When the `Math Worker` or the `Calc UI Tab` interfaces with it, it returns the raw calculated minimum thickness parameters directly without subjecting the numbers to secondary LLM verification, preserving mathematical determinism.
