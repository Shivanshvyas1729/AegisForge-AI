# AegisForge-AI: Future Roadmap & Pending Enhancements

> **Problem Statement:** Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs for Confidential Industrial Work  
> **Organization:** Mangalore Refinery and Petrochemicals Limited (MRPL)

This document tracks planned features and enhancements for future development phases.
All Priority 1 and Priority 2 features from the original roadmap are now **fully implemented**.

---

## ✅ Completed (Removed from Roadmap)

| Feature | Status | Implementation |
|---|---|---|
| Multi-Agent Orchestration (LangGraph) | ✅ Done | 4-stage pipeline: Supervisor → Workers → Reviewer → Publisher |
| Knowledge Base & Vector RAG (Qdrant) | ✅ Done | CLIP-aligned Qdrant vector DB with hybrid keyword+semantic search |
| Network Isolation & Sovereign Proof | ✅ Done | Dual-scope passive telemetry auditor (process-tree + host-level) |
| Multimodal Input (OCR + Vision) | ✅ Done | EasyOCR + PyMuPDF + python-docx multimodal parser pipeline |
| DOCX & PDF Output Deliverables | ✅ Done | Native Word & PDF compilers with SHA-256 cryptographic seals |
| Testing & Quality (18/18 Passing) | ✅ Done | 11 toolset unit tests + 7 multi-agent integration tests |
| Dynamic Model Router | ✅ Done | Keyword-heuristic task classifier across 4 local model specializations |
| Streamlit Web Dashboard | ✅ Done | 3-tab workbench with chat, calculator, and model hub |

---

## 🟡 Priority 1: Enhanced Output Deliverables (PPTX, XLSX)

**Problem Requirement:** *"Output should be real deliverables — approval notes, PPT/Word/Excel files, working code, calculations with steps shown."*

### Current State
- DOCX generation works ✅
- PDF generation works ✅

### Planned Enhancements
- [ ] PowerPoint (.pptx) generator for board presentations using `python-pptx`
- [ ] Excel (.xlsx) generator for calculation spreadsheets and UT grid data export
- [ ] Template system: allow users to upload corporate templates with logo/branding
- [ ] Multi-format export: generate all formats (DOCX + PDF + PPTX + XLSX) from a single analysis

---

## 🟡 Priority 2: Model Auto-Selection Enhancement

**Problem Requirement:** *"Support multiple open weight models at once and automatically pick the right one for a given task."*

### Current State
- `models/router/model_router.py` has keyword-based heuristic classification
- 4 models registered: DeepSeek-R1 (reasoning), Qwen2.5-Coder (coding), Llama-3.2 (general), Moondream (vision)

### Planned Enhancements
- [ ] Confidence scoring for route classification with fallback thresholds
- [ ] Model performance benchmarking per task type with latency/quality metrics
- [ ] Config-driven model registry: hot-swap new models without code changes
- [ ] Support larger models when hardware allows (7B, 14B, 70B variants)
- [ ] Model fallback chains: if primary model fails or times out, try backup

---

## 🟡 Priority 3: Advanced RAG Enhancements

### Current State
- Qdrant vector DB with CLIP embeddings (512-d) for text and images ✅
- Hybrid search: dense vector + keyword payload filtering ✅
- Document ingestion: PDF, DOCX, TXT, MD, JSON, PNG ✅

### Planned Enhancements
- [ ] Source attribution: show which document/page/paragraph the answer came from
- [ ] Chunk-level citation highlighting in the Streamlit UI
- [ ] Automatic re-indexing when new documents are uploaded
- [ ] Support for spreadsheet ingestion (XLSX, CSV) with structured cell extraction
- [ ] Cross-document entity linking (e.g., link equipment IDs across inspection reports)

---

## 🟢 Priority 4: Operational Tooling & DevOps

### Planned Enhancements
- [ ] System health monitoring dashboard with GPU utilization, memory, and inference latency
- [ ] Disk space management with automatic cleanup suggestions for model_pool
- [ ] One-click full setup script: Ollama install + model pull + DB seed
- [ ] CI/CD pipeline (GitHub Actions or local pre-commit hooks)
- [ ] `pyproject.toml` with pytest configuration for standardized test execution

---

## 🟢 Priority 5: Security Hardening

### Planned Enhancements
- [ ] Windows Firewall rule auto-configuration to block all outbound from the process tree
- [ ] Real-time network monitoring widget in Streamlit sidebar (live connection count)
- [ ] Periodic automated air-gap verification (background cron-style audit)
- [ ] Role-based access control (RBAC) for multi-user refinery deployments

---

## 📋 Previously Removed Documentation (Reference)

| File | Contents | Status |
|---|---|---|
| `architecture_viewer.html` | Interactive Mermaid architecture diagrams | Regenerate when architecture stabilizes |
| `TEAM_TASKS_MVP.md` | Team task division and ownership map | Superseded by this roadmap |
| `pyproject.toml` | pytest configuration | Re-add when CI/CD pipeline is set up |
