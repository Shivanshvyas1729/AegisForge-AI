# Supervisor Agent Routing & Template Registry

## Overview
This rule defines how the Supervisor Agent (the cognitive dispatcher of the AegisForge-AI Workbench) decides between generating documents deterministically versus using the Code Interpreter Sandbox.

## The Dual-Strategy Document Pipeline

### 1. The Template Registry (Deterministic Approach)
The Supervisor Agent MUST maintain a strict registry of formal templates. These templates are used for statutory reporting that requires rigid formatting and cryptographic Audit Ledger seals.

**Available Templates in Registry:**
- `NFA_Emergency_Procurement` (Note for Approval)
- `ASME_Inspection_Report`

**Routing Rule:** 
If the user's prompt requests an official document, statutory report, or audit finding that maps to the Template Registry, the Supervisor Agent MUST route the request to `tools/doc_generator.py`. It must pass the exact template name from the registry as an argument.

### 2. The Code Interpreter Sandbox (Agentic Approach)
If the user's prompt requests an ad-hoc summary, a custom formatted Word Document, or a data aggregation that DOES NOT match any official template in the registry, the Supervisor Agent MUST route the request to the Coder Agent.

**Routing Rule:**
The Coder Agent will write a custom Python script using `python-docx` or `pandas` to generate the file dynamically. The Supervisor Agent MUST then route this script to `tools/docker_sandbox.py` for safe, air-gapped execution.

## System Prompt Implementation
The Supervisor Agent's system prompt must include the following logic:
> "You have access to a Template Registry containing: [NFA_Emergency_Procurement, ASME_Inspection_Report]. If the user asks for a document matching these, call `doc_generator`. If the user asks for ANY other custom document, DO NOT use `doc_generator`. Instead, write a custom python-docx script and execute it via `docker_sandbox`."
