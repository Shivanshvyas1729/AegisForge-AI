# AegisForge-AI: Future Roadmap & Pending Features

> **Problem Statement:** Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work  
> **Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL)

This document tracks features that were removed during project cleanup for future re-implementation.
Each section maps back to specific requirements from the SIH problem statement.

---

## 🔴 Priority 1: Multi-Agent Orchestration (LangGraph)

**Problem Requirement:** *"The assistant needs to actually act like an agent. Plan out multi-step work, call local tools, and iterate on a task instead of answering once and stopping."*

### What Was Removed
- `agent_orchestrator/graph.py` — LangGraph state machine with multi-model chaining
- `agent_orchestrator/router.py` — Intent classifier routing to coding/reasoning/summary/multimodal nodes
- `agent_orchestrator/state.py` — AgentState TypedDict for state machine
- `agent_orchestrator/validator.py` — Output validation with retry logic
- `models/coding_models/coding.py` — Qwen2.5-Coder LangGraph node wrapper
- `models/reasoning_models/reasoning.py` — DeepSeek-R1 LangGraph node wrapper
- `models/summary_models/summary.py` — Llama-3.2 LangGraph node wrapper
- `models/vision_models/multimodal.py` — Moondream VLM LangGraph node wrapper

### What Needs to Be Built
- [ ] Restore LangGraph pipeline with proper tool-calling agent
- [ ] Add ReAct agent pattern: the agent should plan → execute tool → observe → repeat
- [ ] Integrate tools (ASME calculator, file I/O, code sandbox, RAG, doc generator) as callable tools
- [ ] Add multi-step task execution with visible step-by-step progress in Streamlit
- [ ] Support iterative refinement — agent tries, evaluates, retries if output is insufficient
- [ ] Sequential pipeline mode: Vision → Code → Reasoning → Summary for complex tasks

---

## 🔴 Priority 2: Knowledge Base & Vector RAG

**Problem Requirement:** *"It needs to ground itself in the organization's own manuals, SOPs and past correspondence through a local knowledge base connector, again with nothing going external."*

### What Was Removed
- `knowledge_base/` — Empty directory placeholder for vector storage
- `data/vector_storage/` — Empty directory for ChromaDB/FAISS indices

### Current State
- `tools/rag.py` exists but uses naive keyword matching on `sample_data/` files
- No vector embeddings, no semantic search

### What Needs to Be Built
- [ ] Local embedding model (e.g., `nomic-embed-text` via Ollama or `sentence-transformers`)
- [ ] ChromaDB or FAISS vector store stored in `data/vector_storage/`
- [ ] Document ingestion pipeline: PDF, DOCX, TXT → chunks → embeddings → vector DB
- [ ] Upload interface in Streamlit for organization manuals, SOPs, past correspondence
- [ ] RAG retrieval: embed user query → find relevant chunks → inject into LLM prompt
- [ ] Source attribution: show which document/page the answer came from

---

## 🟡 Priority 3: Network Isolation & Sovereign Proof

**Problem Requirement:** *"The system should also show, through logs or a visible network monitor, that no external calls are made at any point. That's the actual proof of the sovereign claim."*

### What Was Removed
- `network_isolation/` — Empty directory placeholder

### What Needs to Be Built
- [ ] Network traffic monitor using `psutil` or Windows firewall rules
- [ ] Real-time dashboard widget showing active connections
- [ ] Log all outbound connection attempts with timestamps
- [ ] Visual proof panel in Streamlit: "0 external connections in last 24h"
- [ ] Optional: Windows Firewall rule to block all outbound from the process

---

## 🟡 Priority 4: Multimodal Input (OCR + Vision)

**Problem Requirement:** *"It needs to handle more than text: scanned PDFs, handwritten notes, engineering drawings, photographs, read through on-device OCR and vision models."*

### What Was Removed
- `models/vision_models/convert_svg.py` — SVG to PNG converter
- `models/vision_models/test_easyocr.py` — EasyOCR test harness
- `models/vision_models/test_vision_vlm.py` — Moondream VLM test
- `models/vision_models/test_summary.md` — Vision test results

### Current State
- EasyOCR model weights exist in `model_pool/easyocr/`
- Moondream VLM is available via Ollama
- Basic image upload exists in Streamlit (router tab)

### What Needs to Be Built
- [ ] Scanned PDF → page images → EasyOCR text extraction pipeline
- [ ] Handwritten note recognition (EasyOCR already supports this)
- [ ] P&ID drawing analysis: extract valve tags, instrument bubbles, line numbers
- [ ] Combine OCR output with VLM analysis for comprehensive understanding
- [ ] Support multi-page document processing with progress tracking

---

## 🟡 Priority 5: Output Deliverables (PPTX, XLSX)

**Problem Requirement:** *"Output should be real deliverables — approval notes, PPT/Word/Excel files, working code, calculations with steps shown."*

### Current State
- DOCX generation works ✅
- PDF generation works ✅

### What Needs to Be Built
- [ ] PowerPoint (.pptx) generator for board presentations
- [ ] Excel (.xlsx) generator for calculation spreadsheets
- [ ] Template system: allow users to upload corporate templates
- [ ] Multi-format export: generate all formats from a single analysis

---

## 🟢 Priority 6: Testing & Quality

### What Was Removed
- `tests/test_graph.py` — LangGraph state machine tests
- `tests/test_mvp_pipeline.py` — End-to-end MVP integration tests
- `tests/test_pipeline.py` — Pipeline flow tests
- `tests/test_router.py` — Router classification tests
- `tests/test_routing.py` — Routing decision tests
- `tests/test_tools_and_downloads.py` — Tool and model download tests
- `models/reasoning_models/test_reasoning.py` — Reasoning model tests

### What Needs to Be Built
- [ ] Restore and update test suite once features stabilize
- [ ] Add pytest fixtures for common test data
- [ ] CI/CD pipeline (GitHub Actions or local pre-commit hooks)

---

## 🟢 Priority 7: Model Auto-Selection Enhancement

**Problem Requirement:** *"Support multiple open weight models at once and automatically pick the right one for a given task based on what that task needs."*

### Current State
- `models/router/model_router.py` has keyword-based classification
- 4 models registered: DeepSeek-R1 (reasoning), Qwen2.5-Coder (coding), Llama-3.2 (general), Moondream (vision)

### What Needs to Be Built
- [ ] Confidence scoring for route classification
- [ ] Model performance benchmarking per task type
- [ ] Hot-swap new models without code changes (config-driven model registry)
- [ ] Support larger models when hardware allows (7B, 14B, 70B variants)
- [ ] Model fallback chains: if primary model fails, try backup

---

## 🟢 Priority 8: Operational Scripts

### What Was Removed
- `scripts/setup_models.py` — Bulk model setup with safety checks
- `scripts/clean_models.bat` — One-click model purge
- `scripts/install_ollama.bat` — Ollama installer
- `scripts/run_ollama_local.bat` — Ollama launcher with custom model dir
- `scripts/uninstall_all.bat` — Full teardown

### What Needs to Be Built
- [ ] Integrate setup/cleanup into the Streamlit admin panel
- [ ] Add system health monitoring dashboard
- [ ] Disk space management with automatic cleanup suggestions

---

## 📋 Removed Documentation Files

These files contained useful information but were not part of the running application:

| File | Contents | Action |
|---|---|---|
| `architecture_viewer.html` (107KB) | Interactive Mermaid architecture diagrams | Regenerate when architecture stabilizes |
| `TEAM_TASKS_MVP.md` (16KB) | Team task division and ownership map | Superseded by this roadmap |
| `rahul_check.md` (28KB) | Full architecture specification with Mermaid diagrams | Key sections absorbed into this document |
| `task_summary.md` | One-off task log for file_io.py creation | No longer needed |
| `HOW_TO_DOWNLOAD_ALL_MODELS_WITH_OLLAMA.md` | Ollama model download instructions | Available in Model Hub UI |
| `pyproject.toml` | pytest configuration only | Re-add when tests are restored |

---

## Development Order (Recommended)

1. **Now**: Clean core input → output pipeline (✅ this cleanup)
2. **Next**: Enhance Streamlit UI with chat-like interaction
3. **Next**: Add multimodal input (scanned PDF → OCR → analysis)
4. **Next**: Build proper RAG with vector embeddings
5. **Next**: Restore and enhance LangGraph multi-agent system
6. **Next**: Add network isolation monitoring
7. **Next**: Add PPTX/XLSX output generation
8. **Later**: Test suite, CI/CD, model benchmarking
