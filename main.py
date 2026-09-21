"""
AegisForge-AI: Central Operating Gateway
=========================================
Single entry point for the Sovereign Air-Gapped AI Workbench.

Usage:
    python main.py                     # Interactive terminal menu
    python main.py status              # System health & model status
    python main.py run-golden-path     # End-to-end MVP pipeline
    python main.py route --prompt "…"  # Dynamic model router
    python main.py calc --p 14.5 …     # ASME UG-27 calculator
    python main.py sandbox --code "…"  # Air-gapped code sandbox
    python main.py ui                  # Launch Streamlit dashboard
    python main.py download-models     # Pull all models into model_pool/
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union

# Bootstrap — Anchor project root
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


from backend import AegisForgeBackend


class AegisForgeCentralEngine(AegisForgeBackend):
    """
    Central engine providing a clean programmatic interface to AegisForge-AI.
    Inherits from the unified AegisForgeBackend architecture.

    Example:
        >>> from main import AegisForgeCentralEngine
        >>> engine = AegisForgeCentralEngine()
        >>> status = engine.get_system_status()
        >>> result = engine.calculate_asme(p=14.5, r=1200, s=138, t_actual=138.2)
    """

    def __init__(self):
        super().__init__()
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

    def get_system_status(self) -> Dict[str, Any]:
        """Comprehensive health report: Ollama daemon, models, GPU, disk space."""
        from models.model_downloader import (
            is_ollama_running,
            find_ollama_executable,
            is_model_installed,
            MODEL_METADATA,
        )
        from config.settings import MODEL_REGISTRY

        gpu_available = False
        gpu_name = "N/A"
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                gpu_name = torch.cuda.get_device_name(0)
        except ImportError:
            pass

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

    def run_golden_path(
        self,
        input_source: Optional[Union[str, Path]] = None,
        output_name: str = "IOCL_Emergency_Approval_Note.docx",
        model_name: str = "llama3.2:3b",
        statutory_framework: str = "CVC Circular 02/02/2004 Clause 4.2 / GFR 2017 Rule 194 Emergency Exception",
    ) -> Dict[str, Any]:
        """
        End-to-end Golden Path:
        Inspection Log → ASME Math → Statutory Compliance → Word .docx Deliverable
        """
        from tools.file_io import read_scanned_pdf
        from tools.asme_calculator import calculate_asme_stresses
        from tools.compliance_auditor import audit_cvc_compliance
        from tools.doc_generator import generate_nfa_documents

        if input_source is None:
            input_source = (
                self._project_root
                / "data"
                / "sample_reports"
                / "UT_Scan_Separator_11V102.pdf"
            )

        # 1. Read document
        read_res = read_scanned_pdf.invoke({"file_path": str(input_source)})
        content = read_res.get("content", "")

        # 2. Default ASME Section VIII parameters (overridden dynamically if found in dossier)
        equipment_id = "11-V-102"
        p_val = 14.5
        r_val = 1200.0
        s_val = 138.0
        e_val = 1.0
        ca_val = 4.0
        t_act = 138.20
        cr_val = 0.75

        # Dynamic parameter extraction from dossier text
        import re
        m_id = re.search(r'(?:Equipment\s*(?:ID|Tag|No)?|Vessel\s*(?:Tag|ID|No)?|Tag)[:\s=]*([A-Za-z0-9\-]+)', content, re.IGNORECASE)
        if m_id: equipment_id = m_id.group(1).strip()

        m_p = re.search(r'(?:Design\s*Pressure|Operating\s*Pressure|Pressure\s*P|Pressure)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_p: p_val = float(m_p.group(1))

        m_r = re.search(r'(?:Inside\s*Radius|Internal\s*Radius|Radius\s*R|Radius)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_r: r_val = float(m_r.group(1))

        m_t = re.search(r'(?:Measured\s*Thickness|Actual\s*Thickness|Minimum\s*Recorded\s*Thickness|Thickness\s*t|Thickness)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_t: t_act = float(m_t.group(1))

        m_cr = re.search(r'(?:Corrosion\s*Rate|CR)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_cr: cr_val = float(m_cr.group(1))

        m_ca = re.search(r'(?:Corrosion\s*Allowance|CA)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_ca: ca_val = float(m_ca.group(1))

        m_s = re.search(r'(?:Allowable\s*Stress|Stress\s*S|Max\s*Allowable\s*Stress)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_s: s_val = float(m_s.group(1))

        # Dynamic material lookup if present in document
        m_mat = re.search(r'Material(?: Specification)?[:\s=]*([A-Za-z0-9\.\-\+ ]+)', content, re.IGNORECASE)
        if m_mat:
            mat_grade = m_mat.group(1).strip().split('\n')[0]
            try:
                from tools.material_lookup_tool import lookup_material
                mat_res = lookup_material.invoke({"material_grade": mat_grade, "temperature_c": 350.0})
                if mat_res.get("status") == "SUCCESS" and mat_res.get("allowable_stress_mpa"):
                    s_val = float(mat_res["allowable_stress_mpa"])
            except Exception:
                pass

        # Perform deterministic ASME Section VIII UG-27 calculation
        calc = calculate_asme_stresses.invoke({
            "design_pressure_mpa": p_val,
            "inside_radius_mm": r_val,
            "allowable_stress_mpa": s_val,
            "joint_efficiency": e_val,
            "corrosion_allowance_mm": ca_val,
            "measured_thickness_mm": t_act,
            "corrosion_rate_mm_yr": cr_val,
            "equipment_id": equipment_id
        })

        # Dynamic statutory / CVC compliance audit
        audit = audit_cvc_compliance.invoke({
            "request_id": f"REQ-{equipment_id}-01",
            "equipment_id": equipment_id,
            "estimated_cost_lakhs": 15.0,
            "is_single_source": True,
            "has_pac": False,
            "is_emergency": True,
            "dop_authority": "General Manager",
            "applicable_cvc_clause": statutory_framework
        })

        # Generate signed Word deliverable with cryptographic hash
        doc_res = generate_nfa_documents.invoke({
            "equipment_id": equipment_id,
            "asme_results": str(calc),
            "cvc_compliance": str(audit),
            "template_name": "NFA_Emergency_Procurement.docx"
        })

        import datetime
        return {
            "equipment_id": equipment_id,
            "t_req_mm": calc["t_req_mm"],
            "measured_mm": t_act,
            "delta_mm": calc["delta_mm"],
            "is_breach": calc["is_breach"],
            "remaining_life_years": calc["remaining_life_years"],
            "status": calc["status"],
            "executive_summary": (
                f"ASME Section VIII Div 1 UG-27 verification for {equipment_id}: "
                f"Required thickness = {calc['t_req_mm']:.2f}mm, Measured = {t_act:.2f}mm, "
                f"Safety Margin Δ = {calc['delta_mm']:.2f}mm ({calc['status']}). "
                f"Remaining Service Life = {calc['remaining_life_years']:.2f} years. "
                f"Statutory Audit ({audit.get('sanction_clause', 'Statutory Rules')}): {audit.get('compliance_status')}."
            ),
            "docx_path": doc_res.get("docx_path", ""),
            "sha256_hash": doc_res.get("document_hash", doc_res.get("sha256_hash", "")),
            "pdf_path": doc_res.get("pdf_path"),
            "pdf_sha256": doc_res.get("pdf_sha256"),
            "generated_at": datetime.datetime.now().isoformat(),
        }

    def route_query(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        override_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Classifies the prompt and dispatches to the appropriate local model."""
        from models.router.model_router import SovereignModelRouter

        router = SovereignModelRouter()
        return router.route_and_execute(
            prompt=prompt,
            image_path=image_path,
            override_model=override_model,
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
        """Runs ASME Section VIII Div 1 UG-27 pressure vessel calculation."""
        from schemas.inspection import InspectionInput
        from tools.asme_calculator import AsmeCalculator

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
        calc = AsmeCalculator().evaluate_vessel_integrity(inp)
        return {
            "formula": "t = (P*R)/(S*E - 0.6*P) + CA [ASME UG-27]",
            "t_req_mm": calc.t_req_mm,
            "measured_thickness_mm": t_actual,
            "delta_mm": calc.delta_mm,
            "is_breach": calc.is_breach,
            "remaining_life_years": calc.remaining_life_years,
            "derated_mawp_bar": calc.derated_mawp_mpa * 10.0,
            "design_pressure_bar": p * 10.0,
            "status": calc.status,
        }

    def run_sandbox_code(self, code: str, timeout: int = 15) -> Dict[str, Any]:
        """Executes Python code in the sandbox daemon or fallback runner."""
        return self.sandbox.run_code_in_docker(code, task_title="CLI Sandbox Task")

    def download_models(self, model_id: Optional[str] = None) -> None:
        """Downloads model weights into model_pool/."""
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

            if not is_ollama_running():
                print("Starting Ollama daemon...")
                if not start_ollama_server():
                    print("❌ Could not start Ollama.")
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
            from models.model_downloader import MODEL_METADATA
            for mid in MODEL_METADATA:
                self.download_models(mid)

    def launch_ui(self, port: int = 8501) -> None:
        """Launches the Streamlit web dashboard."""
        import subprocess as _sp
        import socket

        app_path = self._project_root / "frontend" / "app.py"
        if not app_path.exists():
            print(f"❌ Streamlit app not found at: {app_path}")
            return

        def find_free_port(start_port: int) -> int:
            for p in range(start_port, start_port + 100):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(('127.0.0.1', p)) != 0:
                        return p
            return start_port

        actual_port = find_free_port(port)

        print(f"🚀 Launching AegisForge-AI Dashboard on http://localhost:{actual_port}")
        print("   Press Ctrl+C to stop.\n")
        _sp.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(actual_port)],
            cwd=str(self._project_root),
        )


# ===========================================================================
# CLI Interface
# ===========================================================================
def _print_banner():
    banner = r"""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║      █████╗ ███████╗ ██████╗ ██╗███████╗                      ║
    ║     ██╔══██╗██╔════╝██╔════╝ ██║██╔════╝                      ║
    ║     ███████║█████╗  ██║  ███╗██║███████╗                      ║
    ║     ██╔══██║██╔══╝  ██║   ██║██║╚════██║                      ║
    ║     ██║  ██║███████╗╚██████╔╝██║███████║                      ║
    ║     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝╚══════╝                    ║
    ║          ███████╗ ██████╗ ██████╗  ██████╗ ███████╗           ║
    ║          ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝           ║
    ║          █████╗  ██║   ██║██████╔╝██║  ███╗█████╗             ║
    ║          ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝             ║
    ║          ██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗           ║
    ║          ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝          ║
    ║                                                               ║
    ║   Sovereign Air-Gapped AI Workbench for Industrial PSUs       ║
    ║   100% On-Premises │ Zero Cloud │ Air-Gap Verified            ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def _print_status(engine: AegisForgeCentralEngine):
    status = engine.get_system_status()

    print("=" * 60)
    print("  AEGISFORGE-AI SYSTEM STATUS REPORT")
    print("=" * 60)
    print(f"  Project Root:     {status['project_root']}")
    print(f"  Ollama Host:      {status['ollama_host']}")
    print(f"  Ollama Running:   {'🟢 ONLINE' if status['ollama_running'] else '🔴 OFFLINE'}")
    print(f"  GPU Available:    {'✅ ' + status['gpu_name'] if status['gpu_available'] else '❌ CPU Only'}")
    print(f"  Free Disk Space:  {status['disk_free_gb']} GB")
    print()
    print("  Model Status:")
    print("  " + "-" * 55)
    for model_id, info in status["models"].items():
        badge = "✅ INSTALLED" if info["installed"] else "⬇️  NOT INSTALLED"
        print(f"    {info['title']:<26} {info['role']:<28} {badge}")
    print("  " + "-" * 55)
    print()


def _print_calc_result(result: Dict[str, Any]):
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
    print(f"  Status:             {result['status']}")
    print("=" * 55)
    print()


def _interactive_menu(engine: AegisForgeCentralEngine):
    while True:
        print()
        print("  ┌─────────────────────────────────────────────────┐")
        print("  │         AEGISFORGE-AI  COMMAND CENTER           │")
        print("  ├─────────────────────────────────────────────────┤")
        print("  │  1.  System Status & Health Report              │")
        print("  │  2.  Run Golden Path (Inspection → DOCX)       │")
        print("  │  3.  Ask AI (Dynamic Model Router)             │")
        print("  │  4.  ASME Code Calculator                      │")
        print("  │  5.  Air-Gapped Code Sandbox                   │")
        print("  │  6.  Launch Streamlit Web Dashboard             │")
        print("  │  7.  Download / Manage Models                  │")
        print("  │  0.  Exit                                      │")
        print("  └─────────────────────────────────────────────────┘")

        try:
            choice = input("\n  Enter choice [0-7]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Goodbye!")
            break

        if choice == "0":
            print("  Goodbye!")
            break
        elif choice == "1":
            _print_status(engine)
        elif choice == "2":
            print("\n  Running Golden Path MVP Pipeline...")
            try:
                result = engine.run_golden_path()
                print(f"\n  ✅ Pipeline Complete!")
                print(f"     Equipment:   {result['equipment_id']}")
                print(f"     t_min:       {result['t_req_mm']} mm")
                print(f"     Measured:    {result['measured_mm']} mm")
                print(f"     Breach:      {result['is_breach']}")
                print(f"     DOCX:        {result['docx_path']}")
                if result.get('pdf_path'):
                    print(f"     PDF:         {result['pdf_path']}")
            except Exception as exc:
                print(f"  ❌ Pipeline Error: {exc}")
        elif choice == "3":
            try:
                prompt = input("  Enter your prompt: ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not prompt:
                continue
            print("  Routing and executing...")
            try:
                result = engine.route_query(prompt)
                if result.get("success"):
                    print(f"\n  Category: {result.get('task_type', '?').upper()}")
                    print(f"  Model:    {result.get('model_used', '?')}")
                    print(f"\n  Response:\n  {'-' * 50}")
                    print(f"  {result.get('response', '')[:1000]}")
                else:
                    print(f"  ❌ Error: {result.get('error')}")
            except Exception as exc:
                print(f"  ❌ Error: {exc}")
        elif choice == "4":
            print("\n  ASME UG-27 Interactive Calculator")
            print("  (Press Enter to use defaults)")
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
                print("  ⚠️ Invalid number.")
                continue
            result = engine.calculate_asme(p=p, r=r, s=s, e=e_val, ca=ca, t_actual=t_act, cr=cr)
            _print_calc_result(result)
        elif choice == "5":
            try:
                code = input("  Enter Python code (or 'file:path'): ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not code:
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
                print(f"\n  ✅ Exit Code {result['returncode']}")
                print(f"  {result['stdout']}" if result["stdout"] else "  [No output]")
            else:
                print(f"\n  ❌ Exit Code {result['returncode']}")
                print(f"  {result['stderr']}")
        elif choice == "6":
            engine.launch_ui()
        elif choice == "7":
            engine.download_models()
        else:
            print("  ⚠️ Invalid choice.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegisforge",
        description="AegisForge-AI: Sovereign Air-Gapped AI Workbench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                           Interactive menu\n"
            "  python main.py status                    System health\n"
            "  python main.py route --prompt \"Write CRC parser\"   Route query\n"
            "  python main.py calc --p 14.5 --r 1200    ASME calculator\n"
            "  python main.py ui                        Launch dashboard\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    sub.add_parser("status", help="System health & model status report")

    gp = sub.add_parser("run-golden-path", help="Run end-to-end MVP pipeline")
    gp.add_argument("--input", type=str, default=None, help="Path to inspection log")
    gp.add_argument("--output", type=str, default="IOCL_Emergency_Approval_Note.docx")
    gp.add_argument("--model", type=str, default="deepseek-r1:1.5b")

    rt = sub.add_parser("route", help="Route a prompt to the best local model")
    rt.add_argument("--prompt", type=str, required=True)
    rt.add_argument("--image", type=str, default=None)
    rt.add_argument("--model", type=str, default=None)

    cl = sub.add_parser("calc", help="ASME Section VIII Div 1 UG-27 calculator")
    cl.add_argument("--p", type=float, default=14.5)
    cl.add_argument("--r", type=float, default=1200.0)
    cl.add_argument("--s", type=float, default=138.0)
    cl.add_argument("--e", type=float, default=1.0)
    cl.add_argument("--ca", type=float, default=4.0)
    cl.add_argument("--t", type=float, default=138.20)
    cl.add_argument("--cr", type=float, default=0.75)

    sb = sub.add_parser("sandbox", help="Execute Python code in air-gapped sandbox")
    sb_group = sb.add_mutually_exclusive_group(required=True)
    sb_group.add_argument("--code", type=str)
    sb_group.add_argument("--file", type=str)

    ui_cmd = sub.add_parser("ui", help="Launch Streamlit dashboard")
    ui_cmd.add_argument("--port", type=int, default=8501)

    dm = sub.add_parser("download-models", help="Download model weights")
    dm.add_argument("--model", type=str, default=None)

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    engine = AegisForgeCentralEngine()

    if args.command is None:
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
            print(f"\n✅ Generated: {result['docx_path']}")
            print(f"   SHA-256:   {result['sha256_hash'][:24]}...")
        except Exception as exc:
            print(f"❌ Error: {exc}")
    elif args.command == "route":
        result = engine.route_query(
            prompt=args.prompt,
            image_path=args.image,
            override_model=args.model,
        )
        if result.get("success"):
            print(f"Category: {result['task_type'].upper()}")
            print(f"Model:    {result['model_used']}")
            print(f"\n{result['response']}")
        else:
            print(f"❌ {result.get('error')}")
    elif args.command == "calc":
        result = engine.calculate_asme(
            p=args.p, r=args.r, s=args.s, e=args.e,
            ca=args.ca, t_actual=args.t, cr=args.cr,
        )
        _print_calc_result(result)
    elif args.command == "sandbox":
        code = args.code
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                code = f.read()
        result = engine.run_sandbox_code(code)
        if result["success"]:
            print(result["stdout"])
        else:
            print(f"Error:\n{result['stderr']}", file=sys.stderr)
            sys.exit(result["returncode"])
    elif args.command == "ui":
        engine.launch_ui(port=args.port)
    elif args.command == "download-models":
        if args.model:
            engine.download_models(args.model)
        else:
            engine.download_models()


if __name__ == "__main__":
    main()
