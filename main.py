"""
AegisForge-AI: Central Operating Gateway (main.py)
===================================================
Layer 7 — Single master entry point for the entire 7-layer architecture.

Usage:
    python main.py                     # Interactive terminal menu
    python main.py status              # System health & model status
    python main.py run-golden-path     # End-to-end MVP pipeline
    python main.py route --prompt "…"  # Dynamic model router
    python main.py agent --prompt "…"  # LangGraph multi-agent execution
    python main.py calc --p 14.5 …     # ASME UG-27 deterministic calculator
    python main.py sandbox --code "…"  # Air-gapped code sandbox
    python main.py ui                  # Launch Streamlit dashboard
    python main.py download-models     # Pull all models into model_pool/
    python main.py test                # Run automated test suite
    python main.py build-samples       # Compile sample Office deliverables

Architecture Layers:
    Layer 0: Sovereign Runtime & Isolation (config/, scripts/, model_pool/)
    Layer 1: Unified Data Contracts & Schemas (schemas/, agent_orchestrator/state.py)
    Layer 2: Ingestion & Perception Preprocessing (ingestion/, models/vision_models/)
    Layer 3: Deterministic Physics & Sandbox Tools (tools/)
    Layer 4: Sovereign Model Pool & Local Serving (models/, model_pool/)
    Layer 5: Routing & Multi-Agent Orchestration (agent_orchestrator/, models/router/)
    Layer 6: Output Emission & Cryptographic Attestation (output_generation/)
    Layer 7: Central Gateway & User Interfaces (main.py, frontend/)
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union

# ---------------------------------------------------------------------------
# Layer 0: Bootstrap — Anchor project root and ensure consistent encoding
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows terminal encoding for Unicode output
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ===========================================================================
# AegisForgeCentralEngine — Programmatic Python API wrapping all 7 layers
# ===========================================================================
class AegisForgeCentralEngine:
    """
    Central engine providing a clean programmatic interface to every layer
    of AegisForge-AI. Each method wraps one architectural subsystem so that
    no caller ever needs to navigate internal directory structures.

    Example:
        >>> from main import AegisForgeCentralEngine
        >>> engine = AegisForgeCentralEngine()
        >>> status = engine.get_system_status()
        >>> result = engine.calculate_asme(p=14.5, r=1200, s=138, t_actual=138.2)
    """

    def __init__(self):
        # Layer 0 imports (always available — no heavy deps)
        from config.settings import (
            PROJECT_ROOT as _root,
            MODEL_POOL_DIR,
            EASYOCR_DIR,
            OLLAMA_MODELS_DIR,
            OLLAMA_HOST,
            OUTPUT_DIR,
            SAMPLE_DATA_DIR,
            get_disk_free_gb,
        )
        self._project_root = _root
        self._model_pool_dir = MODEL_POOL_DIR
        self._easyocr_dir = EASYOCR_DIR
        self._ollama_models_dir = OLLAMA_MODELS_DIR
        self._ollama_host = OLLAMA_HOST
        self._output_dir = OUTPUT_DIR
        self._sample_data_dir = SAMPLE_DATA_DIR
        self._get_disk_free_gb = get_disk_free_gb

    # -------------------------------------------------------------------
    # Layer 0: System Health & Environment Status
    # -------------------------------------------------------------------
    def get_system_status(self) -> Dict[str, Any]:
        """
        Comprehensive health report: Ollama daemon, installed models,
        GPU availability, disk space, and directory integrity.
        """
        from models.model_downloader import (
            is_ollama_running,
            find_ollama_executable,
            is_model_installed,
            MODEL_METADATA,
        )
        from config.settings import MODEL_REGISTRY

        # GPU detection
        gpu_available = False
        gpu_name = "N/A"
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                gpu_name = torch.cuda.get_device_name(0)
        except ImportError:
            pass

        # Model installation status
        model_status = {}
        for model_id in MODEL_METADATA:
            model_status[model_id] = {
                "installed": is_model_installed(model_id),
                "title": MODEL_METADATA[model_id]["title"],
                "role": MODEL_METADATA[model_id]["role"],
                "size": MODEL_METADATA[model_id]["size_est"],
            }

        return {
            "project_root": str(self._project_root),
            "ollama_host": self._ollama_host,
            "ollama_running": is_ollama_running(),
            "ollama_executable": find_ollama_executable(),
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "disk_free_gb": round(self._get_disk_free_gb(), 2),
            "model_pool_dir": str(self._model_pool_dir),
            "model_registry": MODEL_REGISTRY,
            "models": model_status,
        }

    # -------------------------------------------------------------------
    # Layer 2 + 3 + 5 + 6: Golden Path MVP Pipeline
    # -------------------------------------------------------------------
    def run_golden_path(
        self,
        input_source: Optional[Union[str, Path]] = None,
        output_name: str = "IOCL_Emergency_Approval_Note.docx",
        model_name: str = "deepseek-r1:1.5b",
    ) -> Dict[str, Any]:
        """
        End-to-end Golden Path:
        Inspection Log → ASME Math → DeepSeek-R1 Synthesis → Word .docx

        Args:
            input_source: Path to raw inspection log. Defaults to sample data.
            output_name: Filename for the generated .docx deliverable.
            model_name: Local reasoning model to use via Ollama.

        Returns:
            Dictionary with inspection, calculation, reasoning data and docx path.
        """
        from agent_orchestrator.orchestrator_mvp import run_mvp_pipeline

        if input_source is None:
            input_source = (
                self._sample_data_dir
                / "06_inspection_reports"
                / "field_inspector_raw_ocr_log.txt"
            )

        payload = run_mvp_pipeline(
            input_source=input_source,
            output_filename=output_name,
            model_name=model_name,
        )
        return {
            "equipment_id": payload.inspection_data.equipment_id,
            "t_req_mm": payload.calculation_data.t_req_mm,
            "measured_mm": payload.calculation_data.measured_thickness_mm,
            "delta_mm": payload.calculation_data.delta_mm,
            "is_breach": payload.calculation_data.is_breach,
            "remaining_life_years": payload.calculation_data.remaining_life_years,
            "status": payload.calculation_data.status,
            "executive_summary": payload.reasoning_data.executive_summary,
            "docx_path": payload.docx_path,
            "sha256_hash": payload.sha256_hash,
            "pdf_path": payload.pdf_path,
            "pdf_sha256": payload.pdf_sha256,
            "generated_at": payload.generated_at,
        }

    # -------------------------------------------------------------------
    # Layer 5: Dynamic Model Router (Direct Inference)
    # -------------------------------------------------------------------
    def route_query(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Classifies the prompt intent and dispatches to the appropriate local model.

        Args:
            prompt: User instruction / question.
            image_path: Optional path to an image for vision models.
            override_model: Force a specific model instead of auto-routing.

        Returns:
            Dictionary with task_type, model_used, success flag, and response text.
        """
        from models.router.model_router import SovereignModelRouter

        router = SovereignModelRouter()
        return router.route_and_execute(
            prompt=prompt,
            image_path=image_path,
            override_model=override_model,
        )

    # -------------------------------------------------------------------
    # Layer 5: LangGraph Multi-Agent State Machine
    # -------------------------------------------------------------------
    def run_langgraph(
        self,
        prompt: str,
        route: Optional[str] = None,
        files: Optional[list] = None,
        input_type: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Executes the LangGraph multi-agent state machine.

        Args:
            prompt: User instruction.
            route: Force a specific route (coding/reasoning/summary/multimodal/pipeline).
            files: Optional list of file paths for vision analysis.
            input_type: Optional list of input modality hints.

        Returns:
            Final AgentState dictionary with response and execution metadata.
        """
        from agent_orchestrator.graph import build_graph
        from models.router.model_router import LocalModelHandler
        from config.settings import MODEL_REGISTRY

        # Create model handlers for each route
        router_llm = LocalModelHandler(MODEL_REGISTRY["general"])
        coding_llm = LocalModelHandler(MODEL_REGISTRY["coding"])
        reasoning_llm = LocalModelHandler(MODEL_REGISTRY["reasoning"])
        summary_llm = LocalModelHandler(MODEL_REGISTRY["general"])
        multimodal_llm = LocalModelHandler(MODEL_REGISTRY.get("vision", "moondream"))

        graph = build_graph(
            router_llm=router_llm,
            coding_llm=coding_llm,
            reasoning_llm=reasoning_llm,
            summary_llm=summary_llm,
            multimodal_llm=multimodal_llm,
        )

        initial_state = {
            "user_prompt": prompt,
            "input_type": input_type or [],
            "files": files or [],
            "attempts": 0,
        }
        if route:
            initial_state["route"] = route

        result = graph.invoke(initial_state)
        return dict(result)

    # -------------------------------------------------------------------
    # Layer 3: Deterministic ASME UG-27 Calculator
    # -------------------------------------------------------------------
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
        """
        Runs deterministic ASME Section VIII Div 1 UG-27 pressure vessel calculation.

        Args:
            p: Design pressure in MPa.
            r: Inside radius in mm.
            s: Maximum allowable stress in MPa.
            e: Weld joint efficiency factor.
            ca: Corrosion allowance in mm.
            t_actual: Measured wall thickness in mm.
            cr: Observed corrosion rate in mm/year.
            equipment_id: Equipment tag identifier.

        Returns:
            Dictionary with t_req_mm, delta_mm, is_breach, remaining_life, status, etc.
        """
        from schemas.mvp_schema import InspectionInput
        from tools.asme_calculator import evaluate_vessel_integrity

        inp = InspectionInput(
            equipment_id=equipment_id,
            design_pressure_mpa=p,
            inside_radius_mm=r,
            allowable_stress_mpa=s,
            joint_efficiency=e,
            corrosion_allowance_mm=ca,
            measured_thickness_mm=t_actual,
            corrosion_rate_mm_yr=cr,
        )
        calc = evaluate_vessel_integrity(inp)
        return {
            "formula": calc.formula_used,
            "t_req_mm": calc.t_req_mm,
            "measured_thickness_mm": calc.measured_thickness_mm,
            "delta_mm": calc.delta_mm,
            "is_breach": calc.is_breach,
            "remaining_life_years": calc.remaining_life_years,
            "derated_mawp_bar": calc.derated_mawp_bar,
            "design_pressure_bar": calc.design_pressure_bar,
            "status": calc.status,
        }

    # -------------------------------------------------------------------
    # Layer 3: Air-Gapped Python Sandbox
    # -------------------------------------------------------------------
    def run_sandbox_code(self, code: str, timeout: int = 15) -> Dict[str, Any]:
        """
        Executes Python code in an isolated subprocess with strict timeout.

        Args:
            code: Python source code string.
            timeout: Maximum execution time in seconds.

        Returns:
            Dictionary with success flag, stdout, stderr, and return code.
        """
        from tools.sandbox import execute_python_code

        return execute_python_code(code, timeout_seconds=timeout)

    # -------------------------------------------------------------------
    # Layer 4: Model Downloads
    # -------------------------------------------------------------------
    def download_models(self, model_id: Optional[str] = None) -> None:
        """
        Downloads model weights into model_pool/.

        Args:
            model_id: Specific model to download (e.g. 'deepseek-r1:1.5b').
                       If None, runs the full setup_models script.
        """
        if model_id:
            from models.model_downloader import (
                is_model_installed,
                pull_ollama_model_stream,
                install_easyocr_models,
                is_ollama_running,
                start_ollama_server,
            )

            if is_model_installed(model_id):
                print(f"✅ '{model_id}' is already installed in model_pool/.")
                return

            if model_id == "easyocr":
                for step in install_easyocr_models():
                    print(f"  [{step.get('percent', 0):.0f}%] {step.get('status', '')}")
                return

            # Ollama models
            if not is_ollama_running():
                print("Starting Ollama daemon...")
                if not start_ollama_server():
                    print("❌ Could not start Ollama. Run scripts\\run_ollama_local.bat first.")
                    return

            for update in pull_ollama_model_stream(model_id):
                if update.get("status") == "error":
                    print(f"❌ {update.get('error')}")
                    return
                pct = update.get("percent", 0)
                status_msg = update.get("status", "")
                if update.get("done"):
                    print(f"✅ '{model_id}' downloaded and verified!")
                elif update.get("retrying"):
                    print(f"  ⚠️ {status_msg}")
                else:
                    print(f"  [{pct:.1f}%] {status_msg}", end="\r", flush=True)
            print()
        else:
            # Run full setup script
            from scripts.setup_models import (
                check_safety_preflight,
                setup_easyocr_model,
                setup_ollama_models,
                print_status_summary,
            )
            check_safety_preflight(min_gb_required=6.0)
            setup_easyocr_model()
            setup_ollama_models()
            print_status_summary()

    # -------------------------------------------------------------------
    # Layer 7: Launch Streamlit UI
    # -------------------------------------------------------------------
    def launch_ui(self, port: int = 8501) -> None:
        """Launches the Streamlit web dashboard."""
        import subprocess as _sp

        app_path = self._project_root / "frontend" / "app.py"
        if not app_path.exists():
            print(f"❌ Streamlit app not found at: {app_path}")
            return

        print(f"🚀 Launching AegisForge-AI Dashboard on http://localhost:{port}")
        print("   Press Ctrl+C to stop.\n")
        _sp.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
            cwd=str(self._project_root),
        )

    # -------------------------------------------------------------------
    # Layer 6: Compile Sample Deliverables
    # -------------------------------------------------------------------
    def compile_samples(self) -> None:
        """Compiles all sample Office deliverables (.docx, .xlsx, .pptx)."""
        import subprocess as _sp

        script = self._sample_data_dir / "generate_sample_documents.py"
        if not script.exists():
            print(f"❌ Sample generator not found at: {script}")
            return

        print("📄 Compiling sample Office deliverables...")
        result = _sp.run(
            [sys.executable, str(script)],
            cwd=str(self._project_root),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✅ Sample documents compiled successfully!")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ Compilation failed:\n{result.stderr}")

    # -------------------------------------------------------------------
    # Verification: Run Test Suite
    # -------------------------------------------------------------------
    def run_tests(self) -> int:
        """Runs the automated test suite via pytest. Returns exit code."""
        import subprocess as _sp

        print("🧪 Running AegisForge-AI test suite...\n")
        result = _sp.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            cwd=str(self._project_root),
        )
        return result.returncode


# ===========================================================================
# CLI Interface — argparse subcommands
# ===========================================================================
def _print_banner():
    """Prints the AegisForge-AI ASCII banner and layer summary."""
    banner = r"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║       █████╗ ███████╗ ██████╗ ██╗███████╗                         ║
    ║      ██╔══██╗██╔════╝██╔════╝ ██║██╔════╝                         ║
    ║      ███████║█████╗  ██║  ███╗██║███████╗                         ║
    ║      ██╔══██║██╔══╝  ██║   ██║██║╚════██║                         ║
    ║      ██║  ██║███████╗╚██████╔╝██║███████║                         ║
    ║      ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝╚══════╝                       ║
    ║          ███████╗ ██████╗ ██████╗  ██████╗ ███████╗               ║
    ║          ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝               ║
    ║          █████╗  ██║   ██║██████╔╝██║  ███╗█████╗                 ║
    ║          ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝                 ║
    ║          ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗               ║
    ║          ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝              ║
    ║                                                                   ║
    ║   Sovereign Air-Gapped AI Workbench for PSUs & Critical Infra     ║
    ║   100% On-Premises | Zero Cloud Transmission | Air-Gap Verified   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    print("  7-Layer Architecture:")
    print("  ─────────────────────────────────────────────────────────────")
    print("  L7  Central Gateway & UI      │ main.py, frontend/app.py")
    print("  L6  Output & Attestation      │ output_generation/, SHA-256")
    print("  L5  Routing & Orchestration   │ agent_orchestrator/, models/router/")
    print("  L4  Model Pool & Serving      │ models/, model_pool/, Ollama")
    print("  L3  Physics & Sandbox Tools   │ tools/ (ASME UG-27, sandbox)")
    print("  L2  Ingestion & Perception    │ ingestion/, vision_models/")
    print("  L1  Data Contracts & Schemas  │ schemas/, state.py")
    print("  L0  Runtime & Isolation       │ config/, scripts/")
    print("  ─────────────────────────────────────────────────────────────")
    print()


def _print_status(engine: AegisForgeCentralEngine):
    """Prints a formatted system status report."""
    status = engine.get_system_status()

    print("=" * 65)
    print("  AEGISFORGE-AI SYSTEM STATUS REPORT")
    print("=" * 65)
    print(f"  Project Root:     {status['project_root']}")
    print(f"  Ollama Host:      {status['ollama_host']}")
    print(f"  Ollama Running:   {'🟢 ONLINE' if status['ollama_running'] else '🔴 OFFLINE'}")
    print(f"  Ollama Executable:{status['ollama_executable'] or 'NOT FOUND'}")
    print(f"  GPU Available:    {'✅ ' + status['gpu_name'] if status['gpu_available'] else '❌ CPU Only'}")
    print(f"  Free Disk Space:  {status['disk_free_gb']} GB")
    print(f"  Model Pool:       {status['model_pool_dir']}")
    print()
    print("  Model Registry & Installation Status:")
    print("  " + "-" * 60)
    for model_id, info in status["models"].items():
        badge = "✅ INSTALLED" if info["installed"] else "⬇️  NOT INSTALLED"
        print(f"    {info['title']:<28} {info['role']:<30} {badge}")
    print("  " + "-" * 60)
    print()


def _print_calc_result(result: Dict[str, Any]):
    """Prints a formatted ASME calculation result."""
    print()
    print("=" * 55)
    print("  ASME SECTION VIII DIV 1 UG-27 VERIFICATION")
    print("=" * 55)
    print(f"  Formula:            {result['formula']}")
    print(f"  Required t_min:     {result['t_req_mm']:.2f} mm")
    print(f"  Measured Thickness: {result['measured_thickness_mm']:.2f} mm")
    print(f"  Safety Delta:       {result['delta_mm']:.2f} mm")
    print(f"  Breach Detected:    {'YES — CRITICAL' if result['is_breach'] else 'NO — SAFE'}")
    print(f"  Remaining Life:     {result['remaining_life_years']:.2f} years")
    print(f"  Derated MAWP:       {result['derated_mawp_bar']:.1f} barg")
    print(f"  Design Pressure:    {result['design_pressure_bar']:.1f} barg")
    print(f"  Status:             {result['status']}")
    print("=" * 55)
    print()


def _interactive_menu(engine: AegisForgeCentralEngine):
    """Interactive terminal menu for operators."""
    while True:
        print()
        print("  ┌───────────────────────────────────────────────────────┐")
        print("  │         AEGISFORGE-AI  COMMAND CENTER                │")
        print("  ├───────────────────────────────────────────────────────┤")
        print("  │  1.  System Status & Health Report                   │")
        print("  │  2.  Run Golden Path (Inspection → ASME → DOCX)     │")
        print("  │  3.  Dynamic Model Router (Ask a Question)          │")
        print("  │  4.  LangGraph Multi-Agent Pipeline                 │")
        print("  │  5.  ASME Code Calculator (Interactive)             │")
        print("  │  6.  Air-Gapped Code Sandbox                        │")
        print("  │  7.  Launch Streamlit Web Dashboard                 │")
        print("  │  8.  Download / Manage Models                       │")
        print("  │  9.  Run Automated Test Suite                       │")
        print("  │ 10.  Compile Sample Office Deliverables             │")
        print("  │  0.  Exit                                           │")
        print("  └───────────────────────────────────────────────────────┘")

        try:
            choice = input("\n  Enter choice [0-10]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Exiting AegisForge-AI. Goodbye!")
            break

        if choice == "0":
            print("  Exiting AegisForge-AI. Goodbye!")
            break

        elif choice == "1":
            _print_status(engine)

        elif choice == "2":
            print("\n  Running Golden Path MVP Pipeline (using sample data)...")
            try:
                result = engine.run_golden_path()
                print(f"\n  ✅ Pipeline Complete!")
                print(f"     Equipment:   {result['equipment_id']}")
                print(f"     t_min:       {result['t_req_mm']} mm")
                print(f"     Measured:    {result['measured_mm']} mm")
                print(f"     Delta:       {result['delta_mm']} mm")
                print(f"     Breach:      {result['is_breach']}")
                print(f"     DOCX Note:   {result['docx_path']}")
                print(f"     DOCX SHA256: {result['sha256_hash'][:24]}...")
                if result.get('pdf_path'):
                    print(f"     PDF Note:    {result['pdf_path']}")
                    print(f"     PDF SHA256:  {(result.get('pdf_sha256') or '')[:24]}...")
            except Exception as exc:
                print(f"  ❌ Pipeline Error: {exc}")

        elif choice == "3":
            try:
                prompt = input("  Enter your prompt: ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not prompt:
                print("  ⚠️ Empty prompt. Skipped.")
                continue
            print("  Routing and executing...")
            try:
                result = engine.route_query(prompt)
                if result.get("success"):
                    print(f"\n  Category: {result.get('task_type', '?').upper()}")
                    print(f"  Model:    {result.get('model_used', '?')}")
                    print(f"\n  Response:\n  {'-' * 55}")
                    print(f"  {result.get('response', '')[:1000]}")
                else:
                    print(f"  ❌ Error: {result.get('error')}")
            except Exception as exc:
                print(f"  ❌ Routing Error: {exc}")

        elif choice == "4":
            try:
                prompt = input("  Enter your prompt: ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not prompt:
                print("  ⚠️ Empty prompt. Skipped.")
                continue
            print("  Executing LangGraph agent pipeline...")
            try:
                result = engine.run_langgraph(prompt)
                print(f"\n  Route:    {result.get('route', '?')}")
                print(f"  Model:    {result.get('model_used', '?')}")
                print(f"  Valid:    {result.get('is_valid', '?')}")
                resp = result.get("response", "")
                print(f"\n  Response:\n  {'-' * 55}")
                print(f"  {resp[:1000] if resp else '[No response]'}")
            except Exception as exc:
                print(f"  ❌ Agent Error: {exc}")

        elif choice == "5":
            print("\n  ASME UG-27 Interactive Calculator")
            print("  (Press Enter to use defaults shown in brackets)")
            try:
                p = float(input("    Design Pressure P (MPa) [14.5]: ").strip() or "14.5")
                r = float(input("    Inside Radius R (mm) [1200]: ").strip() or "1200")
                s = float(input("    Allowable Stress S (MPa) [138]: ").strip() or "138")
                e_val = float(input("    Joint Efficiency E [1.0]: ").strip() or "1.0")
                ca = float(input("    Corrosion Allowance CA (mm) [4.0]: ").strip() or "4.0")
                t_act = float(input("    Measured Thickness t (mm) [138.20]: ").strip() or "138.20")
                cr = float(input("    Corrosion Rate (mm/yr) [0.75]: ").strip() or "0.75")
            except (KeyboardInterrupt, EOFError):
                continue
            except ValueError:
                print("  ⚠️ Invalid number entered.")
                continue
            result = engine.calculate_asme(p=p, r=r, s=s, e=e_val, ca=ca, t_actual=t_act, cr=cr)
            _print_calc_result(result)

        elif choice == "6":
            try:
                code = input("  Enter Python code (single line, or 'file:path'): ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not code:
                print("  ⚠️ Empty code. Skipped.")
                continue
            if code.startswith("file:"):
                filepath = code[5:].strip()
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        code = f.read()
                else:
                    print(f"  ❌ File not found: {filepath}")
                    continue
            result = engine.run_sandbox_code(code)
            if result["success"]:
                print(f"\n  ✅ Execution Succeeded (Exit Code {result['returncode']})")
                print(f"  Output:\n  {result['stdout']}" if result["stdout"] else "  [No output]")
            else:
                print(f"\n  ❌ Execution Failed (Exit Code {result['returncode']})")
                print(f"  Error:\n  {result['stderr']}")

        elif choice == "7":
            engine.launch_ui()

        elif choice == "8":
            engine.download_models()

        elif choice == "9":
            engine.run_tests()

        elif choice == "10":
            engine.compile_samples()

        else:
            print("  ⚠️ Invalid choice. Please enter a number 0-10.")


def _build_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="aegisforge",
        description="AegisForge-AI: Sovereign Air-Gapped AI Workbench — Central Command Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                           Interactive menu\n"
            "  python main.py status                    System health report\n"
            "  python main.py calc --p 14.5 --r 1200    ASME calculator\n"
            "  python main.py route --prompt \"Write CRC parser\"   Route query\n"
            "  python main.py sandbox --code \"print(42)\"          Run sandbox\n"
            "  python main.py run-golden-path            Full MVP pipeline\n"
            "  python main.py ui                         Launch Streamlit\n"
        ),
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # status
    sub.add_parser("status", help="Print system health & model installation report")

    # run-golden-path
    gp = sub.add_parser("run-golden-path", help="Run end-to-end MVP pipeline")
    gp.add_argument("--input", type=str, default=None, help="Path to inspection log file")
    gp.add_argument("--output", type=str, default="IOCL_Emergency_Approval_Note.docx", help="Output .docx filename")
    gp.add_argument("--model", type=str, default="deepseek-r1:1.5b", help="Reasoning model name")

    # route
    rt = sub.add_parser("route", help="Classify and route a prompt to the best local model")
    rt.add_argument("--prompt", type=str, required=True, help="User prompt text")
    rt.add_argument("--image", type=str, default=None, help="Optional image path for vision models")
    rt.add_argument("--model", type=str, default=None, help="Override model selection")

    # agent
    ag = sub.add_parser("agent", help="Run LangGraph multi-agent state machine")
    ag.add_argument("--prompt", type=str, required=True, help="User prompt text")
    ag.add_argument("--route", type=str, default=None, help="Force route (coding/reasoning/summary/multimodal/pipeline)")
    ag.add_argument("--pipeline", action="store_true", help="Force sequential pipeline mode")

    # calc
    cl = sub.add_parser("calc", help="ASME Section VIII Div 1 UG-27 calculator")
    cl.add_argument("--p", type=float, default=14.5, help="Design pressure P (MPa)")
    cl.add_argument("--r", type=float, default=1200.0, help="Inside radius R (mm)")
    cl.add_argument("--s", type=float, default=138.0, help="Allowable stress S (MPa)")
    cl.add_argument("--e", type=float, default=1.0, help="Joint efficiency E")
    cl.add_argument("--ca", type=float, default=4.0, help="Corrosion allowance CA (mm)")
    cl.add_argument("--t", type=float, default=138.20, help="Measured thickness t (mm)")
    cl.add_argument("--cr", type=float, default=0.75, help="Corrosion rate (mm/yr)")

    # sandbox
    sb = sub.add_parser("sandbox", help="Execute Python code in air-gapped sandbox")
    sb_group = sb.add_mutually_exclusive_group(required=True)
    sb_group.add_argument("--code", type=str, help="Python code string to execute")
    sb_group.add_argument("--file", type=str, help="Path to Python script to execute")

    # ui
    ui_cmd = sub.add_parser("ui", help="Launch the Streamlit web dashboard")
    ui_cmd.add_argument("--port", type=int, default=8501, help="Server port (default: 8501)")

    # download-models
    dm = sub.add_parser("download-models", help="Download model weights into model_pool/")
    dm.add_argument("--model", type=str, default=None, help="Specific model ID (e.g. 'deepseek-r1:1.5b')")

    # test
    sub.add_parser("test", help="Run automated test suite")

    # build-samples
    sub.add_parser("build-samples", help="Compile sample Office deliverables")

    return parser


# ===========================================================================
# Entry Point
# ===========================================================================
def main():
    """Main entry point — dispatches to CLI subcommand or interactive menu."""
    parser = _build_parser()
    args = parser.parse_args()
    engine = AegisForgeCentralEngine()

    if args.command is None:
        # No subcommand → interactive menu
        _print_banner()
        _interactive_menu(engine)

    elif args.command == "status":
        _print_banner()
        _print_status(engine)

    elif args.command == "run-golden-path":
        _print_banner()
        try:
            result = engine.run_golden_path(
                input_source=args.input,
                output_name=args.output,
                model_name=args.model,
            )
            print(f"\n✅ Golden Path Complete!")
            print(f"   DOCX Note:   {result['docx_path']}")
            print(f"   DOCX SHA256: {result['sha256_hash']}")
            if result.get('pdf_path'):
                print(f"   PDF Note:    {result['pdf_path']}")
                print(f"   PDF SHA256:  {result['pdf_sha256']}")
        except Exception as exc:
            print(f"❌ Pipeline Error: {exc}")
            sys.exit(1)

    elif args.command == "route":
        result = engine.route_query(
            prompt=args.prompt,
            image_path=args.image,
            override_model=args.model,
        )
        if result.get("success"):
            print(f"\nCategory: {result.get('task_type', '?').upper()}")
            print(f"Model:    {result.get('model_used', '?')}")
            print(f"\nResponse:\n{'─' * 55}")
            print(result.get("response", ""))
        else:
            print(f"❌ Error: {result.get('error')}")
            sys.exit(1)

    elif args.command == "agent":
        route = "pipeline" if args.pipeline else args.route
        result = engine.run_langgraph(prompt=args.prompt, route=route)
        print(f"\nRoute:  {result.get('route', '?')}")
        print(f"Model:  {result.get('model_used', '?')}")
        print(f"Valid:  {result.get('is_valid', '?')}")
        print(f"\nResponse:\n{'─' * 55}")
        print(result.get("response", "[No response]"))

    elif args.command == "calc":
        result = engine.calculate_asme(
            p=args.p, r=args.r, s=args.s, e=args.e,
            ca=args.ca, t_actual=args.t, cr=args.cr,
        )
        _print_calc_result(result)

    elif args.command == "sandbox":
        code = args.code
        if args.file:
            if not os.path.exists(args.file):
                print(f"❌ File not found: {args.file}")
                sys.exit(1)
            with open(args.file, "r", encoding="utf-8") as f:
                code = f.read()
        result = engine.run_sandbox_code(code)
        if result["success"]:
            print(result["stdout"] if result["stdout"] else "[No output]")
        else:
            print(f"Error (Exit {result['returncode']}):\n{result['stderr']}", file=sys.stderr)
            sys.exit(result["returncode"] or 1)

    elif args.command == "ui":
        engine.launch_ui(port=args.port)

    elif args.command == "download-models":
        engine.download_models(model_id=args.model)

    elif args.command == "test":
        exit_code = engine.run_tests()
        sys.exit(exit_code)

    elif args.command == "build-samples":
        engine.compile_samples()


if __name__ == "__main__":
    main()
