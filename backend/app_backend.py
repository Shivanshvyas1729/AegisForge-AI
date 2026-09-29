"""
AegisForge-AI: Unified Backend Engine Facade
===========================================
Primary service gateway connecting UI layers (Streamlit, Web APIs) and CLI runtimes
to sovereign air-gapped domain services and multi-agent pipelines.
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Union, Dict, Any

from .services.dossier_service import DossierService
from .services.engineering_service import EngineeringService
from .services.compliance_service import ComplianceService
from .services.telemetry_service import TelemetryService
from .services.sandbox_service import SandboxService
from .services.audit_service import AuditService
from .services.langfuse_service import LangfuseService


class AegisForgeBackend:
    """
    Unified Backend Gateway for AegisForge-AI.

    Provides cohesive, decoupled access to:
    - Dossier Ingestion & Autonomous Golden Path (`backend.dossier`)
    - ASME BPVC & API 579 Engineering Math (`backend.engineering`)
    - CVC & GFR 2017 Statutory Procurement Auditor (`backend.compliance`)
    - Hardware Telemetry & Air-Gap Verification (`backend.telemetry`)
    - Secure Docker Sandbox Daemon Lifecycle (`backend.sandbox`)
    - Tamper-Proof Cryptographic Audit Ledger (`backend.audit`)
    - Langfuse Container & Observability Lifecycle (`backend.langfuse`)
    """

    _instance: Optional["AegisForgeBackend"] = None

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            self.workspace_root = Path(__file__).resolve().parent.parent
        else:
            self.workspace_root = Path(workspace_root)

        # Initialize core decoupled services
        self.dossier = DossierService(self.workspace_root)
        self.engineering = EngineeringService()
        self.compliance = ComplianceService()
        self.telemetry = TelemetryService(self.workspace_root)
        self.sandbox = SandboxService()
        self.audit = AuditService()
        self.langfuse = LangfuseService(self.workspace_root)


    @classmethod
    def get_instance(cls, workspace_root: Optional[Path] = None) -> "AegisForgeBackend":
        """Singleton accessor for efficient state sharing across Streamlit reruns."""
        if cls._instance is None:
            cls._instance = cls(workspace_root)
        return cls._instance

    # -------------------------------------------------------------------------
    # Output Sanitization
    # -------------------------------------------------------------------------
    def sanitize_output(self, text: str) -> str:
        """Strip internal debug/status tags from agent output before rendering."""
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        # Remove [STATUS: ...] blocks emitted by nodes for internal signalling
        text = re.sub(r"\[STATUS:[^\]]*\]", "", text, flags=re.IGNORECASE)
        # Remove any leftover XML-style internal tags like <think>, <reasoning>
        text = re.sub(r"<(?:think|reasoning|internal)[^>]*>.*?</(?:think|reasoning|internal)>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Normalize Windows paths to Unix style for display cleanliness
        text = re.sub(r"([A-Za-z]):\\\\", r"/", text)
        # Collapse excessive blank lines (3+ → 2)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # -------------------------------------------------------------------------
    # High-Level Delegated Convenience APIs
    # -------------------------------------------------------------------------
    def get_system_status(self) -> Dict[str, Any]:
        """Returns local Ollama health, GPU hardware, disk space, and models."""
        return self.telemetry.get_system_status()

    def run_golden_path(
        self,
        input_source: Optional[Union[str, Path]] = None,
        output_name: str = "IOCL_Emergency_Approval_Note.docx",
        model_name: str = "llama3.2:3b",
        statutory_framework: str = "CVC Circular 02/02/2004 Clause 4.2 / GFR 2017 Rule 194 Emergency Exception",
    ) -> Dict[str, Any]:
        """Executes the full automated NDT dossier to signed NFA workflow."""
        return self.dossier.run_pipeline(
            input_source=input_source,
            statutory_framework=statutory_framework,
            template_name="NFA_Emergency_Procurement.docx"
        )

    def calculate_asme(
        self,
        p: float = 14.5,
        r: float = 1200.0,
        s: float = 138.0,
        e: float = 1.0,
        ca: float = 4.0,
        t_actual: float = 138.20,
        cr: float = 0.75,
        equipment_id: str = "VESSEL-001",
    ) -> Dict[str, Any]:
        """Runs ASME Section VIII Div 1 UG-27 wall thickness calculation."""
        calc = self.engineering.calculate_asme_ug27(
            design_pressure_mpa=p,
            inside_radius_mm=r,
            allowable_stress_mpa=s,
            joint_efficiency=e,
            corrosion_allowance_mm=ca,
            measured_thickness_mm=t_actual,
            corrosion_rate_mm_yr=cr,
            equipment_id=equipment_id
        )
        return {
            "formula": "t = (P*R)/(S*E - 0.6*P) + CA [ASME UG-27]",
            "t_req_mm": calc.get("t_req_mm", 0.0),
            "measured_thickness_mm": t_actual,
            "delta_mm": calc.get("delta_mm", 0.0),
            "is_breach": calc.get("is_breach", False),
            "remaining_life_years": calc.get("remaining_life_years", 0.0),
            "derated_mawp_bar": calc.get("derated_mawp_mpa", 0.0) * 10.0,
            "design_pressure_bar": p * 10.0,
            "status": calc.get("status", "UNKNOWN"),
        }

    def audit_compliance(
        self,
        request_id: str,
        equipment_id: str,
        estimated_cost_lakhs: float,
        is_single_source: bool = True,
        has_pac: bool = False,
        is_emergency: bool = True,
        dop_authority: str = "General Manager",
        applicable_clause: str = "CVC Circular 02/02/2004 Clause 4.2 / GFR 2017 Rule 194 Emergency Exception",
    ) -> Dict[str, Any]:
        """Audits procurement against statutory anti-corruption rules."""
        return self.compliance.audit_procurement(
            request_id=request_id,
            equipment_id=equipment_id,
            estimated_cost_lakhs=estimated_cost_lakhs,
            is_single_source=is_single_source,
            has_pac=has_pac,
            is_emergency=is_emergency,
            dop_authority=dop_authority,
            applicable_clause=applicable_clause
        )

    def run_sandbox_code(self, code: str, task_title: Optional[str] = None) -> Dict[str, Any]:
        """Executes code in the Docker sandbox daemon or fallback runner."""
        if self.sandbox.is_daemon_active():
            return self.sandbox.run_code_in_docker(code, task_title=task_title)
        return self.sandbox.run_code_subprocess(code)

    def route_query(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Classifies and routes query through the local model router."""
        from models.router.model_router import SovereignModelRouter
        router = SovereignModelRouter()
        return router.route_and_execute(
            prompt=prompt,
            image_path=image_path,
            override_model=override_model
        )

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def sanitize_output(self, content: str) -> str:
        """Cleans internal execution flags, delimiters, and container paths for clean human presentation."""
        if not content:
            return ""
        text = str(content)
        # Strip internal status tokens
        tokens_to_remove = [
            r'\[STATUS:\s*CALCULATION_COMPLETED\]',
            r'\[STATUS:\s*COMPLIANCE_COMPLETED\]',
            r'\[STATUS:\s*SUCCESS\]',
            r'\[STATUS:\s*COMPLETED\]',
            r'\[STATUS:\s*ERROR\]',
            r'\[DOCKER_SANDBOX_OUTPUT\]:\s*',
            r'\[TOOL_ERROR\]:\s*',
            r'<<<<FILE_START>>>>.*?<<<<FILE_END>>>>',
        ]
        for pat in tokens_to_remove:
            text = re.sub(pat, '', text, flags=re.DOTALL)

        # Normalize internal Linux container path /output/ to data/output/
        text = re.sub(r'/output/([a-zA-Z0-9_\-\.]+)', r'data/output/\1', text)

        # Clean excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

    def _find_file_by_ext(self, content: str, ext: str) -> Optional[str]:
        """Extracts and validates an absolute file path with given extension from agent output content."""
        if not content:
            return None

        output_dir = (self.workspace_root / "data" / "output").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        pattern = rf'([A-Za-z]:[^\s\n\'"`]+?\.{ext}|(?:/output/|data/output/|output/)[^\s\n\'"`]+?\.{ext}|[\w\-.]+\.{ext})'
        matches = re.findall(pattern, content, re.IGNORECASE)

        # 1. Direct check in output directory and candidate paths
        for m in matches:
            clean = m.strip("`'\",.:;)\n\r\t ")
            fname = Path(clean).name

            candidate_paths = [
                output_dir / fname,
                (self.workspace_root / clean).resolve(),
            ]
            if Path(clean).is_absolute():
                candidate_paths.insert(0, Path(clean).resolve())

            for cp in candidate_paths:
                if cp and cp.exists() and cp.is_file():
                    return str(cp)

        # 2. If not found on host, try auto-copy from docker container into host data/output
        try:
            import subprocess
            from tools.docker_sandbox import DAEMON_CONTAINER_NAME, is_daemon_running
            c_name = DAEMON_CONTAINER_NAME if is_daemon_running() else "aegisforge-sandbox-daemon"
            subprocess.run(["docker", "cp", f"{c_name}:/output/.", str(output_dir)], capture_output=True, timeout=5)

            for m in matches:
                clean = m.strip("`'\",.:;)\n\r\t ")
                fname = Path(clean).name
                cp = output_dir / fname
                if cp.exists() and cp.is_file():
                    return str(cp)
        except Exception:
            pass

        # 3. Fuzzy search: if any file currently in data/output has its name/stem mentioned in content
        try:
            for f in output_dir.glob(f"*.{ext}"):
                if f.name.lower() in content.lower() or f.stem.lower() in content.lower():
                    return str(f)
        except Exception:
            pass

        return None

    def _find_docx_path(self, content: str) -> Optional[str]:
        return self._find_file_by_ext(content, "docx")

    def _find_pdf_path(self, content: str) -> Optional[str]:
        return self._find_file_by_ext(content, "pdf")

    def _find_md_path(self, content: str) -> Optional[str]:
        return self._find_file_by_ext(content, "md")

    def _find_sha256(self, content: str) -> Optional[str]:
        """Extracts a SHA-256 hash from agent output content."""
        m_sha = re.search(r'\b([a-fA-F0-9]{64})\b', content)
        return m_sha.group(1) if m_sha else None



    def _classify_step(self, msg) -> Dict[str, Any]:
        """
        Inspect a LangGraph message and return a structured step dict with:
        - agent: who emitted it
        - content: the text content
        - step_type: 'tool_call' | 'tool_result' | 'reasoning' | 'directive'
        - tool_name: name of the tool (if applicable)
        """
        from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

        name = getattr(msg, "name", None) or getattr(msg, "type", None) or type(msg).__name__
        content = getattr(msg, "content", str(msg))
        if isinstance(content, list):
            # AIMessage content can be a list of dicts for multi-modal
            content = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )

        step_type = "reasoning"
        tool_name = None

        # Detect tool invocation: AIMessage with tool_calls
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            step_type = "tool_call"
            tool_name = msg.tool_calls[0].get("name", "") if msg.tool_calls else None

        # Also detect text JSON tool calls emitted by open-weight models (e.g. {"name": "calculate_asme_stresses", ...})
        elif str(content).strip().startswith("{") and '"name"' in str(content) and ('"arguments"' in str(content) or '"parameters"' in str(content)):
            try:
                parsed_c = json.loads(str(content).strip())
                if "name" in parsed_c and ("arguments" in parsed_c or "parameters" in parsed_c):
                    step_type = "tool_call"
                    tool_name = parsed_c.get("name", "")
            except Exception:
                pass

        # Detect tool result: ToolMessage
        elif isinstance(msg, ToolMessage):
            step_type = "tool_result"
            tool_name = getattr(msg, "name", "tool")
            name = tool_name  # use tool name as the "agent" label for clarity

        # Also detect executed tool results wrapped in message content (e.g. Tool 'calculate_asme_stresses' executed:)
        elif "tool '" in str(content).lower() and "executed:" in str(content).lower():
            step_type = "tool_result"
            try:
                tool_name = str(content).split("'")[1]
            except Exception:
                tool_name = "Deterministic Tool"

        # Supervisor directive JSON
        elif isinstance(msg, HumanMessage) and str(name).lower() == "supervisor":
            step_type = "directive"

        return {
            "agent": str(name),
            "content": str(content),
            "step_type": step_type,
            "tool_name": tool_name,
        }

    # -------------------------------------------------------------------------
    # Multi-Agent Chat (non-streaming)
    # -------------------------------------------------------------------------
    def chat(
        self,
        prompt: str,
        attached_file: Optional[Union[str, Path]] = None,
        thread_id: str = "default_session",
    ) -> Dict[str, Any]:
        """
        Full conversational multi-agent workbench interaction.
        Ingests user prompts, handles file attachments, coordinates specialists, and returns structured outputs.
        """
        full_prompt = prompt
        if attached_file:
            doc_res = self.dossier.read_document(attached_file)
            content = doc_res.get("content", "")
            if content:
                full_prompt = f"[ATTACHED INDUSTRIAL DOSSIER: {Path(attached_file).name}]\n{content[:4000]}\n\n[USER INSTRUCTION]:\n{prompt}"

        from agent_orchestrator.pipeline import app
        config = {"configurable": {"thread_id": thread_id}}
        res = app.invoke({"messages": [("user", full_prompt)]}, config=config)

        steps = []
        final_answer = ""
        doc_path = None
        pdf_path = None
        md_path = None
        sha256 = None

        all_msgs = res.get("messages", [])

        # Find the start of the current turn (latest human message from user)
        latest_human_idx = 0
        for idx in range(len(all_msgs) - 1, -1, -1):
            msg = all_msgs[idx]
            msg_type = getattr(msg, "type", "")
            if msg_type in ["human", "user"] or (isinstance(msg, tuple) and msg[0] in ["human", "user"]):
                latest_human_idx = idx
                break

        current_turn_msgs = all_msgs[latest_human_idx:]

        for msg in current_turn_msgs:
            name_str = str(getattr(msg, "name", None) or getattr(msg, "type", None) or "").lower()
            content = str(getattr(msg, "content", str(msg)))

            if name_str in ["chief_reviewer", "direct_answer", "deliverable_publisher"]:
                final_answer = content

            # Exclude raw user prompt echo
            if name_str not in ["human", "user"] and content.strip() != full_prompt.strip():
                step = self._classify_step(msg)
                steps.append(step)

            doc_path = doc_path or self._find_docx_path(content)
            pdf_path = pdf_path or self._find_pdf_path(content)
            md_path  = md_path  or self._find_md_path(content)
            sha256   = sha256   or self._find_sha256(content)

        if not final_answer and steps:
            final_answer = steps[-1]["content"]

        if len(steps) == 1 and steps[0]["agent"].lower() == "direct_answer":
            steps = []

        # Check if the execution paused at a Human Approval Gate
        current_state = app.get_state(config)
        for task in getattr(current_state, "tasks", []):
            if getattr(task, "interrupts", None):
                gate_data = getattr(task.interrupts[0], "value", task.interrupts[0])
                return {
                    "status": "INTERRUPTED",
                    "prompt": prompt,
                    "gate_data": gate_data,
                    "thread_id": thread_id,
                    "steps": steps,
                    "final_answer": gate_data.get("message", "Operational authorization required."),
                    "docx_path": doc_path,
                    "pdf_path": pdf_path,
                    "md_path": md_path,
                    "sha256_hash": sha256,
                }

        return {
            "prompt": prompt,
            "final_answer": final_answer,
            "steps": steps,
            "docx_path": doc_path,
            "pdf_path": pdf_path,
            "md_path": md_path,
            "sha256_hash": sha256,
        }

    # -------------------------------------------------------------------------
    # Multi-Agent Chat (streaming — live tool call trace)
    # -------------------------------------------------------------------------
    def chat_stream(
        self,
        prompt: str,
        attached_file: Optional[Union[str, Path]] = None,
        thread_id: str = "default_session",
    ):
        """
        Live streaming generator for multi-agent collaboration.

        Uses LangGraph stream_mode='updates' with subgraphs=True so that
        intermediate steps *inside* create_react_agent subgraphs are visible:
        - Supervisor directives
        - Tool invocations (AIMessage with tool_calls)
        - Tool results (ToolMessage)
        - Agent reasoning and final answers
        - Human Approval Gate interrupts

        Yields events:
          {"type": "step", "step": {...}, "steps": [...]}
          {"type": "interrupt", "gate_data": {...}, "thread_id": "...", "steps": [...]}
          {"type": "done", "final_answer": "...", "steps": [...], ...}
        """
        full_prompt = prompt
        if attached_file:
            doc_res = self.dossier.read_document(attached_file)
            content = doc_res.get("content", "")
            if content:
                full_prompt = f"[ATTACHED INDUSTRIAL DOSSIER: {Path(attached_file).name}]\n{content[:4000]}\n\n[USER INSTRUCTION]:\n{prompt}"

        from agent_orchestrator.pipeline import app
        config = {"configurable": {"thread_id": thread_id}}

        steps = []
        final_answer = ""
        doc_path = None
        pdf_path = None
        md_path = None
        sha256 = None

        # stream_mode="updates" + subgraphs=True:
        # Each event is a 2-tuple: (namespace_tuple, update_dict)
        for event in app.stream(
            {"messages": [("user", full_prompt)]},
            config=config,
            stream_mode="updates",
            subgraphs=True
        ):
            # Unpack the 2-tuple from subgraph streaming
            if isinstance(event, tuple) and len(event) == 2:
                namespace, update = event
            else:
                namespace = ()
                update = event

            if not isinstance(update, dict):
                continue

            # Intercept Human Approval Gate interrupt
            if "__interrupt__" in update:
                interrupt_list = update["__interrupt__"]
                gate_data = getattr(interrupt_list[0], "value", interrupt_list[0]) if interrupt_list else {}
                yield {
                    "type": "interrupt",
                    "gate_data": gate_data,
                    "thread_id": thread_id,
                    "steps": list(steps)
                }
                return

            for node_name, node_update in update.items():
                msgs = []
                if isinstance(node_update, dict):
                    msgs = node_update.get("messages", [])
                elif hasattr(node_update, "get"):
                    msgs = node_update.get("messages", [])

                for msg in msgs:
                    name_str = str(getattr(msg, "name", None) or getattr(msg, "type", None) or node_name).lower()
                    content = str(getattr(msg, "content", str(msg)))
                    if isinstance(getattr(msg, "content", None), list):
                        content = " ".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in msg.content
                        )

                    # Skip pure user message echoes
                    if content.strip() == full_prompt.strip() or not content.strip():
                        continue

                    # Skip raw human/user messages (unless it is HumanGate sign-off)
                    if name_str in ["human", "user"] and name_str != "humangate":
                        continue

                    # Track final answer (direct_answer, chief_reviewer, deliverable_publisher)
                    if name_str in ["chief_reviewer", "direct_answer", "deliverable_publisher"]:
                        final_answer = content

                    # Only add to trace if it's NOT a direct_answer
                    if name_str != "direct_answer":
                        step_data = self._classify_step(msg)

                        # Attach namespace context so frontend can show which agent context it belongs to
                        if namespace:
                            parent_agent = str(namespace[0]).split(":")[0] if namespace else ""
                            if parent_agent and step_data["agent"].lower() in ["ai", "tool", "aichat", ""]:
                                step_data["agent"] = parent_agent

                        steps.append(step_data)

                        # Track deliverable paths and hashes
                        doc_path = doc_path or self._find_docx_path(content)
                        pdf_path = pdf_path or self._find_pdf_path(content)
                        md_path  = md_path  or self._find_md_path(content)
                        sha256   = sha256   or self._find_sha256(content)

                        yield {
                            "type": "step",
                            "step": step_data,
                            "steps": list(steps)
                        }
                    else:
                        # Still track deliverables from direct_answer content
                        doc_path = doc_path or self._find_docx_path(content)
                        pdf_path = pdf_path or self._find_pdf_path(content)
                        md_path  = md_path  or self._find_md_path(content)
                        sha256   = sha256   or self._find_sha256(content)

        # Check if the execution stopped at an interrupt
        current_state = app.get_state(config)
        for task in getattr(current_state, "tasks", []):
            if getattr(task, "interrupts", None):
                gate_data = getattr(task.interrupts[0], "value", task.interrupts[0])
                yield {
                    "type": "interrupt",
                    "gate_data": gate_data,
                    "thread_id": thread_id,
                    "steps": list(steps)
                }
                return

        if not final_answer and steps:
            final_answer = steps[-1]["content"]

        if len(steps) == 1 and steps[0]["agent"].lower() == "direct_answer":
            steps = []

        # Deliverable discovery from final_answer
        if final_answer:
            doc_path = doc_path or self._find_docx_path(final_answer)
            pdf_path = pdf_path or self._find_pdf_path(final_answer)
            md_path  = md_path  or self._find_md_path(final_answer)
            sha256   = sha256   or self._find_sha256(final_answer)

        # Auto-link companion files in data/output
        if doc_path and Path(doc_path).exists():
            p_doc = Path(doc_path)
            if not pdf_path and p_doc.with_suffix(".pdf").exists():
                pdf_path = str(p_doc.with_suffix(".pdf"))
            if not md_path and p_doc.with_suffix(".md").exists():
                md_path = str(p_doc.with_suffix(".md"))
        elif md_path and Path(md_path).exists():
            p_md = Path(md_path)
            if not doc_path and p_md.with_suffix(".docx").exists():
                doc_path = str(p_md.with_suffix(".docx"))
            if not pdf_path and p_md.with_suffix(".pdf").exists():
                pdf_path = str(p_md.with_suffix(".pdf"))

        cleaned_final_answer = self.sanitize_output(final_answer)

        yield {
            "type": "done",
            "prompt": prompt,
            "final_answer": cleaned_final_answer,
            "steps": steps,
            "docx_path": doc_path,
            "pdf_path": pdf_path,
            "md_path": md_path,
            "sha256_hash": sha256,
        }


    # -------------------------------------------------------------------------
    # Resume Human Approval Gate (Streaming & Non-Streaming)
    # -------------------------------------------------------------------------
    def resume_approval_stream(
        self,
        thread_id: str = "default_session",
        approved: bool = True,
        feedback: str = "",
        existing_steps: Optional[list] = None,
    ):
        """
        Resumes execution at the Human Approval Gate using Command(resume=...).
        Streams remaining execution steps and delivers the finalized review/output.
        """
        from agent_orchestrator.pipeline import app
        from langgraph.types import Command

        config = {"configurable": {"thread_id": thread_id}}
        steps = list(existing_steps) if existing_steps else []
        final_answer = ""
        doc_path = None
        pdf_path = None
        md_path = None
        sha256 = None

        default_feedback = "Approved by operator." if approved else "Rejected by operator."
        resume_payload = {
            "approved": bool(approved),
            "feedback": str(feedback).strip() if feedback else default_feedback
        }

        for event in app.stream(
            Command(resume=resume_payload),
            config=config,
            stream_mode="updates",
            subgraphs=True
        ):
            if isinstance(event, tuple) and len(event) == 2:
                namespace, update = event
            else:
                namespace = ()
                update = event

            if not isinstance(update, dict):
                continue

            # In case of nested/subsequent gate
            if "__interrupt__" in update:
                interrupt_list = update["__interrupt__"]
                gate_data = getattr(interrupt_list[0], "value", interrupt_list[0]) if interrupt_list else {}
                yield {
                    "type": "interrupt",
                    "gate_data": gate_data,
                    "thread_id": thread_id,
                    "steps": list(steps)
                }
                return

            for node_name, node_update in update.items():
                msgs = []
                if isinstance(node_update, dict):
                    msgs = node_update.get("messages", [])
                elif hasattr(node_update, "get"):
                    msgs = node_update.get("messages", [])

                for msg in msgs:
                    name_str = str(getattr(msg, "name", None) or getattr(msg, "type", None) or node_name).lower()
                    content = str(getattr(msg, "content", str(msg)))
                    if isinstance(getattr(msg, "content", None), list):
                        content = " ".join(
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in msg.content
                        )

                    if not content.strip() or (name_str in ["human", "user"] and name_str != "humangate"):
                        continue

                    if name_str in ["chief_reviewer", "direct_answer", "deliverable_publisher"]:
                        final_answer = content

                    step_data = self._classify_step(msg)
                    if namespace:
                        parent_agent = str(namespace[0]).split(":")[0] if namespace else ""
                        if parent_agent and step_data["agent"].lower() in ["ai", "tool", "aichat", ""]:
                            step_data["agent"] = parent_agent

                    steps.append(step_data)
                    doc_path = doc_path or self._find_docx_path(content)
                    pdf_path = pdf_path or self._find_pdf_path(content)
                    md_path  = md_path  or self._find_md_path(content)
                    sha256   = sha256   or self._find_sha256(content)

                    yield {
                        "type": "step",
                        "step": step_data,
                        "steps": list(steps)
                    }

        current_state = app.get_state(config)
        for task in getattr(current_state, "tasks", []):
            if getattr(task, "interrupts", None):
                gate_data = getattr(task.interrupts[0], "value", task.interrupts[0])
                yield {
                    "type": "interrupt",
                    "gate_data": gate_data,
                    "thread_id": thread_id,
                    "steps": list(steps)
                }
                return

        if not final_answer and steps:
            final_answer = steps[-1]["content"]

        if final_answer:
            doc_path = doc_path or self._find_docx_path(final_answer)
            pdf_path = pdf_path or self._find_pdf_path(final_answer)
            md_path  = md_path  or self._find_md_path(final_answer)
            sha256   = sha256   or self._find_sha256(final_answer)

        if doc_path and Path(doc_path).exists():
            p_doc = Path(doc_path)
            if not pdf_path and p_doc.with_suffix(".pdf").exists():
                pdf_path = str(p_doc.with_suffix(".pdf"))
            if not md_path and p_doc.with_suffix(".md").exists():
                md_path = str(p_doc.with_suffix(".md"))
        elif md_path and Path(md_path).exists():
            p_md = Path(md_path)
            if not doc_path and p_md.with_suffix(".docx").exists():
                doc_path = str(p_md.with_suffix(".docx"))
            if not pdf_path and p_md.with_suffix(".pdf").exists():
                pdf_path = str(p_md.with_suffix(".pdf"))

        cleaned_final_answer = self.sanitize_output(final_answer)

        yield {
            "type": "done",
            "prompt": "Human Approval Decision",
            "final_answer": cleaned_final_answer,
            "steps": steps,
            "docx_path": doc_path,
            "pdf_path": pdf_path,
            "md_path": md_path,
            "sha256_hash": sha256,
        }


    def resume_approval(
        self,
        thread_id: str = "default_session",
        approved: bool = True,
        feedback: str = "",
    ) -> Dict[str, Any]:
        """Synchronously resume a paused human approval gate."""
        from agent_orchestrator.pipeline import app
        from langgraph.types import Command

        config = {"configurable": {"thread_id": thread_id}}
        default_feedback = "Approved by operator." if approved else "Rejected by operator."
        resume_payload = {
            "approved": bool(approved),
            "feedback": str(feedback).strip() if feedback else default_feedback
        }
        res = app.invoke(Command(resume=resume_payload), config=config)

        steps = []
        final_answer = ""
        doc_path = None
        pdf_path = None
        md_path = None
        sha256 = None
        for msg in res.get("messages", []):
            content = str(getattr(msg, "content", str(msg)))
            name_str = str(getattr(msg, "name", None) or getattr(msg, "type", None) or "").lower()
            if name_str in ["chief_reviewer", "direct_answer", "deliverable_publisher"]:
                final_answer = content
            step = self._classify_step(msg)
            steps.append(step)
            doc_path = doc_path or self._find_docx_path(content)
            pdf_path = pdf_path or self._find_pdf_path(content)
            md_path  = md_path  or self._find_md_path(content)
            sha256   = sha256   or self._find_sha256(content)

        return {
            "final_answer": final_answer,
            "steps": steps,
            "docx_path": doc_path,
            "pdf_path": pdf_path,
            "md_path": md_path,
            "sha256_hash": sha256,
        }


