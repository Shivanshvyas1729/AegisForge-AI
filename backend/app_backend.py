"""
AegisForge-AI: Unified Backend Engine Facade
===========================================
Primary service gateway connecting UI layers (Streamlit, Web APIs) and CLI runtimes
to sovereign air-gapped domain services and multi-agent pipelines.
"""

from pathlib import Path
from typing import Optional, Union, Dict, Any

from .services.dossier_service import DossierService
from .services.engineering_service import EngineeringService
from .services.compliance_service import ComplianceService
from .services.telemetry_service import TelemetryService
from .services.sandbox_service import SandboxService
from .services.audit_service import AuditService


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

    @classmethod
    def get_instance(cls, workspace_root: Optional[Path] = None) -> "AegisForgeBackend":
        """Singleton accessor for efficient state sharing across Streamlit reruns."""
        if cls._instance is None:
            cls._instance = cls(workspace_root)
        return cls._instance

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
        equipment_id: str = "11-V-102",
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

    def chat(
        self,
        prompt: str,
        attached_file: Optional[Union[str, Path]] = None,
        thread_id: str = "default_session",
    ) -> Dict[str, Any]:
        """
        Full conversational multi-agent workbench interaction (Like Claude / Codex for Industrial PSUs).
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

        # Parse message history to extract steps and deliverables for THIS TURN ONLY
        steps = []
        final_answer = ""
        doc_path = None
        sha256 = None

        all_msgs = res.get("messages", [])
        
        # Find the start of the current turn (latest human message)
        latest_human_idx = 0
        for idx in range(len(all_msgs) - 1, -1, -1):
            msg = all_msgs[idx]
            msg_type = getattr(msg, "type", "")
            if msg_type in ["human", "user"] or isinstance(msg, tuple) and msg[0] in ["human", "user"]:
                latest_human_idx = idx
                break

        # Only process messages generated in this turn
        current_turn_msgs = all_msgs[latest_human_idx:]

        for msg in current_turn_msgs:
            name = getattr(msg, "name", None) or getattr(msg, "type", None) or type(msg).__name__
            content = getattr(msg, "content", str(msg))
            name_str = str(name).lower()

            if name_str in ["chief_reviewer", "direct_answer"]:
                final_answer = content

            # Keep intermediate agent reasoning in steps (exclude raw user prompt and standalone greetings)
            if name_str not in ["human", "user"] and content.strip() != full_prompt.strip() and not (name_str == "direct_answer" and not final_answer):
                steps.append({"agent": str(name), "content": str(content)})

            # Check if deliverable generated
            import re
            m_docx = re.search(r'([A-Za-z]:[^\s\n\'"]+\.docx)', content)
            if m_docx and Path(m_docx.group(1)).exists():
                doc_path = m_docx.group(1)
            m_sha = re.search(r'\b([a-fA-F0-9]{64})\b', content)
            if m_sha:
                sha256 = m_sha.group(1)

        if not final_answer and steps:
            final_answer = steps[-1]["content"]

        # If it was a simple direct answer with no intermediate tool agents, omit steps to keep UI clean
        if len(steps) == 1 and steps[0]["agent"].lower() == "direct_answer":
            steps = []

        return {
            "prompt": prompt,
            "final_answer": final_answer,
            "steps": steps,
            "docx_path": doc_path,
            "sha256_hash": sha256,
        }

    def chat_stream(
        self,
        prompt: str,
        attached_file: Optional[Union[str, Path]] = None,
        thread_id: str = "default_session",
    ):
        """
        Live streaming generator for multi-agent collaboration.
        Yields agent step events in real-time as each specialist executes.
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
        sha256 = None

        for event in app.stream({"messages": [("user", full_prompt)]}, config=config, stream_mode="updates"):
            for node_name, node_update in event.items():
                msgs = node_update.get("messages", []) if isinstance(node_update, dict) else []
                for msg in msgs:
                    name = getattr(msg, "name", None) or node_name
                    content = getattr(msg, "content", str(msg))
                    name_str = str(name).lower()

                    if name_str in ["chief_reviewer", "direct_answer"]:
                        final_answer = content

                    if name_str not in ["human", "user"] and content.strip() != full_prompt.strip():
                        step_data = {"agent": str(name), "content": str(content)}
                        steps.append(step_data)
                        yield {
                            "type": "step",
                            "step": step_data,
                            "steps": list(steps)
                        }

                    import re
                    m_docx = re.search(r'([A-Za-z]:[^\s\n\'"]+\.docx)', content)
                    if m_docx and Path(m_docx.group(1)).exists():
                        doc_path = m_docx.group(1)
                    m_sha = re.search(r'\b([a-fA-F0-9]{64})\b', content)
                    if m_sha:
                        sha256 = m_sha.group(1)

        if not final_answer and steps:
            final_answer = steps[-1]["content"]

        if len(steps) == 1 and steps[0]["agent"].lower() == "direct_answer":
            steps = []

        yield {
            "type": "done",
            "prompt": prompt,
            "final_answer": final_answer,
            "steps": steps,
            "docx_path": doc_path,
            "sha256_hash": sha256,
        }

