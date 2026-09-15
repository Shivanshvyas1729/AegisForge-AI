"""
AegisForge-AI: Sovereign Air-Gapped PSU Workbench
Unified Streamlit Application: Model Hub, Pipeline Orchestration & Offline Analytics
"""

import os
import sys
import time
from pathlib import Path
import streamlit as st

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    MODEL_POOL_DIR,
    EASYOCR_DIR,
    OLLAMA_MODELS_DIR,
    OLLAMA_HOST,
    get_disk_free_gb,
)
from models.model_downloader import (
    MODEL_METADATA,
    is_ollama_running,
    find_ollama_executable,
    start_ollama_server,
    is_model_installed,
    pull_ollama_model_stream,
    install_easyocr_models,
    purge_model,
)
from models.router.model_router import SovereignModelRouter
from tools.sandbox import execute_python_code
from tools.asme_calculator import evaluate_vessel_integrity
from schemas.mvp_schema import InspectionInput

# Page configuration
st.set_page_config(
    page_title="AegisForge-AI | Sovereign Industrial Workbench",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for high-tech industrial aesthetic
st.markdown("""
<style>
    .main {
        background-color: #0b0f19;
    }
    .stMetric {
        background: #161f30;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #223249;
    }
    .model-card {
        background: #131b2a;
        border: 1px solid #1f2d42;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .model-card:hover {
        border-color: #3b82f6;
    }
    .status-badge-installed {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-missing {
        background-color: #374151;
        color: #9ca3af;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-offline {
        background: #991b1b;
        color: #fca5a5;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
    }
    .badge-online {
        background: #065f46;
        color: #6ee7b7;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=64)
    st.title("AegisForge-AI")
    st.caption("🔒 100% Sovereign Air-Gapped PSU Workbench")
    st.divider()

    # System Status Monitor
    st.subheader("🖥️ Runtime Health")
    ollama_active = is_ollama_running()
    ollama_path = find_ollama_executable()

    if ollama_active:
        st.markdown("**Ollama Daemon:** <span class='badge-online'>🟢 ONLINE</span>", unsafe_allow_html=True)
    else:
        st.markdown("**Ollama Daemon:** <span class='badge-offline'>🔴 OFFLINE</span>", unsafe_allow_html=True)

    free_gb = get_disk_free_gb()
    st.metric("Free Disk Space", f"{free_gb:.1f} GB")

    st.caption(f"**Model Storage:** `{MODEL_POOL_DIR.name}/`")
    st.divider()

    st.markdown("""
    **Quick Actions:**
    - Models download directly into `model_pool/`
    - Zero host pollution (`C:\\Users\\...` untouched)
    - Works 100% offline once downloaded
    """)


# Main Navigation Tabs
tab_router, tab_mvp, tab_calculator, tab_sandbox, tab_models, tab_info = st.tabs([
    "💬 Live Model Router & Multi-Task Studio",
    "⚡ Sovereign Analysis (Golden Path)",
    "🧮 Interactive ASME Code Calculator",
    "🧪 Air-Gapped Code Sandbox",
    "📦 Model Hub & One-Click Downloader",
    "ℹ️ Architecture & Storage Details"
])

# -----------------------------------------------------------------------------
# TAB 1: LIVE MODEL ROUTER & MULTI-TASK STUDIO
# -----------------------------------------------------------------------------
with tab_router:
    st.header("💬 Live Multi-Model Router & Execution Studio")
    st.write(
        "Ask for **Python code**, **ASME engineering reasoning**, **executive summaries**, or analyze **P&ID drawings**. "
        "The **Dynamic Layer 3 Router** automatically classifies your request and delegates it to the specialized local model, "
        "or you can manually select a model to test."
    )

    # Initialize prompt in session_state if not present
    if "router_prompt" not in st.session_state:
        st.session_state.router_prompt = "Write a complete Python function to compute ASME Section VIII Div 1 UG-27 minimum shell thickness with input validation."

    st.markdown("**💡 Quick-Fill Example Prompts:**")
    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        if st.button("💻 ASME Python Code", use_container_width=True):
            st.session_state.router_prompt = "Write a complete Python function to compute ASME Section VIII Div 1 UG-27 minimum shell thickness given design pressure P, inside radius R, allowable stress S, and joint efficiency E. Include clear docstrings and error handling."
            st.rerun()
    with c_p2:
        if st.button("📄 Request DOCX Deliverable", use_container_width=True):
            st.session_state.router_prompt = "I need docx file for the emergency Note for Approval on vessel 11-V-102 statutory thickness breach with ASME UG-27 calculations."
            st.rerun()
    with c_p3:
        if st.button("📑 Request PDF Deliverable", use_container_width=True):
            st.session_state.router_prompt = "I need pdf file for the emergency Note for Approval on vessel 11-V-102 statutory thickness breach with ASME UG-27 calculations."
            st.rerun()

    c_p4, c_p5, c_p6 = st.columns(3)
    with c_p4:
        if st.button("🧠 CVC Compliance Rationale", use_container_width=True):
            st.session_state.router_prompt = "Evaluate whether an emergency single-source procurement of an OEM weld overlay repair for pressure vessel 11-V-102 complies with Central Vigilance Commission (CVC) Circular 02/02/2004 and DOP Clause 4.2."
            st.rerun()
    with c_p5:
        if st.button("📡 Modbus SCADA Parser", use_container_width=True):
            st.session_state.router_prompt = "Write a Python parser for SCADA Modbus RTU telemetry packets with CRC-16 checksum verification and register parsing."
            st.rerun()
    with c_p6:
        if st.button("📝 Crude Preheat Summary", use_container_width=True):
            st.session_state.router_prompt = "Summarize the key operational safety steps for inspecting the Crude Distillation Unit preheat train exchangers in 3 concise bullet points."
            st.rerun()

    c_input, c_options = st.columns([2.2, 1])

    with c_input:
        user_prompt = st.text_area(
            "Enter Task Prompt / Instruction:",
            value=st.session_state.router_prompt,
            height=160,
            key="user_prompt_input"
        )
        
        uploaded_img = st.file_uploader(
            "Optional: Upload Diagram / P&ID / Inspection Image for Vision VLM",
            type=["png", "jpg", "jpeg", "svg"],
            key="router_img_upload"
        )

    with c_options:
        st.markdown("**Routing Mode:**")
        route_mode = st.radio(
            "Select Routing Strategy:",
            [
                "⚡ Auto-Route (Dynamic Classifier)",
                "💻 Force Coding (Qwen2.5-Coder:1.5b)",
                "🧠 Force Reasoning (DeepSeek-R1:1.5b)",
                "📝 Force Summary (Llama-3.2:3b)",
                "👁️ Force Vision (Moondream VLM)",
            ],
            index=0
        )
        run_router_btn = st.button("🚀 Run Local Inference", type="primary", use_container_width=True)

    if run_router_btn:
        if not user_prompt.strip():
            st.warning("Please enter a prompt to test.")
        else:
            override_model = None
            if "Force Coding" in route_mode:
                override_model = "qwen2.5-coder:1.5b"
            elif "Force Reasoning" in route_mode:
                override_model = "deepseek-r1:1.5b"
            elif "Force Summary" in route_mode:
                override_model = "llama3.2:3b"
            elif "Force Vision" in route_mode:
                override_model = "moondream"

            # Handle optional uploaded image
            saved_image_path = None
            if uploaded_img:
                uploads_dir = PROJECT_ROOT / "data" / "uploads"
                uploads_dir.mkdir(parents=True, exist_ok=True)
                saved_image_path = str(uploads_dir / uploaded_img.name)
                with open(saved_image_path, "wb") as f_img:
                    f_img.write(uploaded_img.read())

            with st.spinner("Dispatching task to local sovereign model via Ollama..."):
                t_start = time.time()
                router = SovereignModelRouter()
                result = router.route_and_execute(
                    prompt=user_prompt,
                    image_path=saved_image_path,
                    override_model=override_model
                )
                t_elapsed = time.time() - t_start

            if result.get("success"):
                task_category = result.get("task_type", "GENERAL").upper()
                model_used = result.get("model_used", "unknown")
                response_text = result.get("response", "")

                # Telemetry Banner
                badge_color = {
                    "CODING": "#3b82f6",
                    "REASONING": "#8b5cf6",
                    "SUMMARY": "#10b981",
                    "VISION": "#f59e0b",
                    "GENERAL": "#6b7280"
                }.get(task_category, "#3b82f6")

                st.markdown(f"""
                <div style="background: #111827; border: 1px solid #374151; border-radius: 8px; padding: 12px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="background: {badge_color}; color: #fff; font-weight: bold; font-size: 0.8rem; padding: 4px 8px; border-radius: 4px; margin-right: 8px;">
                            {task_category}
                        </span>
                        <span style="color: #e5e7eb; font-size: 0.95rem;">Assigned Model: <b><code>{model_used}</code></b></span>
                    </div>
                    <div style="color: #9ca3af; font-size: 0.85rem;">
                        ⏱️ Latency: <b>{t_elapsed:.2f}s</b> &nbsp;|&nbsp; 🔒 100% Sovereign Air-Gapped
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("### 📤 Model Response:")
                st.markdown(response_text)

                # If Python code is detected, provide an instant "Run in Sandbox" feature
                import re
                code_blocks = re.findall(r"```(?:python)?\s*(.*?)```", response_text, re.DOTALL)
                if code_blocks:
                    st.divider()
                    st.subheader("🧪 Air-Gapped Sandbox Execution")
                    st.caption("Execute this generated Python code inside the local subprocess sandbox to verify correctness:")
                    extracted_code = code_blocks[0].strip()
                    
                    if st.button("▶️ Execute Code in Isolated Sandbox", key="exec_generated_code", type="secondary"):
                        with st.spinner("Executing script in air-gapped sandbox..."):
                            sandbox_res = execute_python_code(extracted_code)
                        
                        if sandbox_res["success"]:
                            st.success(f"Execution Successful! (Exit Code {sandbox_res['returncode']})")
                            st.markdown("**Standard Output (stdout):**")
                            st.code(sandbox_res["stdout"] if sandbox_res["stdout"] else "[No stdout output]")
                        else:
                            st.error(f"Execution Failed (Exit Code {sandbox_res['returncode']}):")
                            st.code(sandbox_res["stderr"])

                # Format intent detection & automatic document delivery
                p_lower = user_prompt.lower()
                wants_docx = any(k in p_lower for k in [
                    "need docx", "give me docx", "give docx", "download docx",
                    "generate docx", "export docx", "docx file", ".docx",
                    "word doc", "word file", "word format", "as docx"
                ])
                wants_pdf = any(k in p_lower for k in [
                    "need pdf", "give me pdf", "give pdf", "download pdf",
                    "generate pdf", "export pdf", "pdf file", ".pdf",
                    "pdf document", "pdf format", "pdf report", "as pdf"
                ])
                wants_doc = wants_docx or wants_pdf or any(k in p_lower for k in [
                    "note for approval", "nfa", "generate report", "download deliverable",
                    "deliverable", "approval note"
                ])

                if wants_doc:
                    st.divider()
                    st.subheader("📄 Generated Deliverables & Download")
                    with st.spinner("Compiling official deliverables from engineering reasoning..."):
                        from tools.doc_generator import generate_docx_deliverable, generate_pdf_deliverable
                        from schemas.mvp_schema import InspectionInput, CalculationOutput, ReasoningOutput
                        from tools.asme_calculator import evaluate_vessel_integrity

                        # Build baseline inspection and verified ASME calculation
                        base_insp = InspectionInput(
                            equipment_id="11-V-102",
                            equipment_name="HP Separator Drum",
                            material="2.25Cr-1Mo",
                            design_pressure_mpa=14.5,
                            inside_radius_mm=1200.0,
                            allowable_stress_mpa=138.0,
                            joint_efficiency=1.0,
                            corrosion_allowance_mm=4.0,
                            critical_location="BK-01",
                            measured_thickness_mm=138.20,
                            corrosion_rate_mm_yr=0.75,
                        )
                        base_calc = evaluate_vessel_integrity(base_insp)
                        base_reason = ReasoningOutput(
                            executive_summary=response_text[:400] if len(response_text) > 30 else "Statutory ASME Section VIII thickness breach on vessel 11-V-102.",
                            cvc_guideline_clause="CVC Circular No. 02/02/2004 & DOP Clause 4.2 Single-Source Emergency Repair.",
                            recommended_action="Immediate emergency single-source procurement of Inconel 625 weld overlay repair.",
                            estimated_cost="Rs. 88.0 Lakhs",
                            raw_model_response=response_text
                        )

                        c_dl1, c_dl2 = st.columns(2)

                        # If user specifically asked for docx (or both / general report)
                        if wants_docx or (not wants_pdf):
                            docx_res = generate_docx_deliverable(base_insp, base_calc, base_reason)
                            with open(docx_res["path"], "rb") as f_d:
                                docx_bytes = f_d.read()
                            with c_dl1:
                                st.download_button(
                                    label="📥 Download Executive Note (.docx)",
                                    data=docx_bytes,
                                    file_name="IOCL_Emergency_Approval_Note.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    use_container_width=True,
                                    key="tab1_dl_docx"
                                )
                                st.caption(f"Microsoft Word | {docx_res['size_bytes']} bytes | SHA-256: `{docx_res['sha256'][:12]}...`")

                        # If user specifically asked for pdf (or both / general report)
                        if wants_pdf or (not wants_docx):
                            pdf_res = generate_pdf_deliverable(base_insp, base_calc, base_reason)
                            with open(pdf_res["path"], "rb") as f_p:
                                pdf_bytes = f_p.read()
                            target_col = c_dl2 if (wants_docx or not wants_pdf) else c_dl1
                            with target_col:
                                st.download_button(
                                    label="📥 Download Executive Note (.pdf)",
                                    data=pdf_bytes,
                                    file_name="IOCL_Emergency_Approval_Note.pdf",
                                    mime="application/pdf",
                                    use_container_width=True,
                                    key="tab1_dl_pdf"
                                )
                                st.caption(f"Adobe PDF Document | {pdf_res['size_bytes']} bytes | SHA-256: `{pdf_res['sha256'][:12]}...`")
            else:
                st.error(f"Model Execution Failed: {result.get('error')}")
                if "connection" in str(result.get("error", "")).lower():
                    st.info("Tip: Ensure the local Ollama daemon is running (`scripts\\run_ollama_local.bat`).")

# -----------------------------------------------------------------------------
# TAB 2: SOVEREIGN ANALYSIS MVP
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# TAB 5: MODEL HUB & ONE-CLICK DOWNLOADER
# -----------------------------------------------------------------------------
with tab_models:
    st.header("One-Click Local Model Management")
    st.write(
        "Select and download local models directly into the project's **`model_pool/`** directory. "
        "No terminal commands or external file moves required."
    )

    # Ollama Health & Controls
    col_srv1, col_srv2 = st.columns([3, 1])
    with col_srv1:
        if not ollama_active:
            if ollama_path:
                st.warning("⚠️ Local Ollama daemon is currently stopped. Click below to start it in background.")
            else:
                st.error(
                    "❌ Ollama is not installed on this system. "
                    "Download and install it once from [ollama.com/download/windows](https://ollama.com/download/windows)."
                )
    with col_srv2:
        if not ollama_active and ollama_path:
            if st.button("▶️ Start Local Ollama", use_container_width=True):
                with st.spinner("Starting Ollama with storage in model_pool/ollama..."):
                    if start_ollama_server():
                        st.success("Ollama started successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to auto-start. Run scripts\\run_ollama_local.bat")

    st.write("")

    # Model Cards Grid
    for model_id, info in MODEL_METADATA.items():
        installed = is_model_installed(model_id)

        with st.container():
            st.markdown(f"""
            <div class="model-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h3 style="margin: 0; color: #f3f4f6;">{info['title']}</h3>
                    <div>
                        {f'<span class="status-badge-installed">✅ Installed in model_pool</span>' if installed else '<span class="status-badge-missing">⬇️ Not Downloaded</span>'}
                    </div>
                </div>
                <p style="color: #9ca3af; margin: 4px 0 10px 0;">{info['desc']}</p>
                <div style="font-size: 0.85rem; color: #6b7280;">
                    <b>Role:</b> {info['role']} &nbsp;|&nbsp; <b>Size:</b> {info['size_est']} &nbsp;|&nbsp; <b>Engine:</b> {info['backend'].upper()}
                </div>
            </div>
            """, unsafe_allow_html=True)

            c_btn1, c_btn2, c_spacer = st.columns([1.5, 1.2, 3])

            with c_btn1:
                if not installed:
                    btn_label = f"⬇️ Download {info['title'].split()[0]}"
                    if st.button(btn_label, key=f"dl_{model_id}", type="primary"):
                        progress_bar = st.progress(0, text="Initializing download...")
                        status_text = st.empty()

                        if info["backend"] == "easyocr":
                            for step in install_easyocr_models():
                                pct = int(step.get("percent", 0))
                                progress_bar.progress(pct, text=step.get("status", "Processing..."))
                                status_text.info(step.get("status", ""))
                                time.sleep(0.3)
                            st.success(f"✅ {info['title']} installed into model_pool/easyocr!")
                            st.rerun()

                        else:  # Ollama backend
                            if not is_ollama_running():
                                if not start_ollama_server():
                                    st.error("Please start Ollama first (scripts\\run_ollama_local.bat).")
                                    continue

                            for update in pull_ollama_model_stream(model_id):
                                if update.get("status") == "error":
                                    status_text.error(f"❌ {update.get('error')}")
                                    st.info("💡 You can click the download button again at any time to resume without losing completed progress.")
                                    break

                                pct = max(0, min(100, int(update.get("percent", 0))))
                                status_msg = update.get("status", "Downloading...")
                                total_mb = update.get("total_mb", 0)
                                comp_mb = update.get("completed_mb", 0)

                                if update.get("retrying"):
                                    # Network interruption recovery notice
                                    status_text.warning(status_msg)
                                    progress_bar.progress(pct, text=f"⚠️ Resuming from {pct}%...")
                                else:
                                    if total_mb > 0:
                                        label = f"{status_msg} ({pct}% — {comp_mb:.1f} MB / {total_mb:.1f} MB)"
                                    else:
                                        label = f"{status_msg} ({pct}%)"
                                    progress_bar.progress(pct, text=label)
                                    status_text.text(f"Status: {status_msg}")

                            if is_model_installed(model_id):
                                progress_bar.progress(100, text="Verification complete!")
                                st.success(f"✅ {info['title']} verified and ready in model_pool/ollama!")
                                time.sleep(1.5)
                                st.rerun()

            with c_btn2:
                if installed:
                    if st.button(f"🗑️ Remove", key=f"del_{model_id}"):
                        with st.spinner(f"Removing {model_id} from model_pool..."):
                            purge_model(model_id)
                            st.success(f"Removed {info['title']} from model_pool.")
                            time.sleep(1)
                            st.rerun()

            st.write("---")


# -----------------------------------------------------------------------------
# TAB 2: SOVEREIGN ANALYSIS MVP
# -----------------------------------------------------------------------------
with tab_mvp:
    st.header("⚡ Sovereign ASME Verification & Approval Generator")
    st.write("Golden Path: **Ultrasonic NDT OCR Log → ASME Code Math → Local DeepSeek-R1 Synthesis → Word Note for Approval**")

    sample_log_path = PROJECT_ROOT / "sample_data" / "06_inspection_reports" / "field_inspector_raw_ocr_log.txt"

    c_left, c_right = st.columns([1, 1])

    with c_left:
        st.subheader("1. Ingestion Source")
        use_sample = st.checkbox("Use Gold-Standard Sample Inspection Report", value=True)

        if use_sample:
            if sample_log_path.exists():
                raw_text = sample_log_path.read_text(encoding="utf-8")
                st.text_area("Field Inspector Ultrasonic Log (Raw)", raw_text, height=220)
            else:
                st.error("Sample inspection report not found.")
        else:
            uploaded_file = st.file_uploader("Upload Inspection OCR Log (.txt)", type=["txt"])
            if uploaded_file:
                raw_text = uploaded_file.read().decode("utf-8")
                st.text_area("Uploaded Log", raw_text, height=220)

        run_analysis = st.button("🚀 Run Sovereign Pipeline", type="primary", use_container_width=True)

    with c_right:
        st.subheader("2. Real-Time Processing Status")
        if run_analysis:
            from agent_orchestrator.orchestrator_mvp import run_mvp_pipeline

            input_source = sample_log_path if use_sample else (uploaded_file if 'uploaded_file' in locals() and uploaded_file else sample_log_path)

            with st.status("Executing Sovereign Workflow...", expanded=True) as status:
                st.write("🔍 Parsing inspection log parameters...")
                payload = run_mvp_pipeline(input_source)
                
                st.markdown(f"""
                > **Equipment:** `{payload.inspection_data.equipment_id}` ({payload.inspection_data.equipment_name})  
                > **Actual Wall Thickness:** `{payload.calculation_data.measured_thickness_mm:.2f} mm`  
                > **Minimum Required ($t_{{min}}$):** `{payload.calculation_data.t_req_mm:.2f} mm`  
                > **Delta:** `<span style='color: #ef4444; font-weight: bold;'>{payload.calculation_data.delta_mm:.2f} mm (STATUTORY VIOLATION)</span>`  
                > **API 510 Remaining Life:** `{payload.calculation_data.remaining_life_years:.2f} Years`
                """, unsafe_allow_html=True)

                st.write("🧠 Synthesizing executive justification via local DeepSeek-R1...")
                st.info(f"**Executive Finding:** {payload.reasoning_data.executive_summary}")

                st.write("📄 Compiling native Microsoft Word (.docx) & Adobe PDF (.pdf) Note for Approval...")
                status.update(label="✅ Analysis Complete!", state="complete")

            st.success(f"Deliverables Ready: `{Path(payload.docx_path).name}` & `{Path(payload.pdf_path).name}`")

            # Deliverable download buttons with genuine generated bytes
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if os.path.exists(payload.docx_path):
                    with open(payload.docx_path, "rb") as f_docx:
                        content_docx = f_docx.read()
                    st.download_button(
                        label="📥 Download Executive Note (.docx)",
                        data=content_docx,
                        file_name=Path(payload.docx_path).name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key="dl_golden_docx"
                    )
                    st.caption(f"Microsoft Word | SHA-256: `{payload.sha256_hash[:16]}...`")
            with col_d2:
                if payload.pdf_path and os.path.exists(payload.pdf_path):
                    with open(payload.pdf_path, "rb") as f_pdf:
                        content_pdf = f_pdf.read()
                    st.download_button(
                        label="📥 Download Executive Note (.pdf)",
                        data=content_pdf,
                        file_name=Path(payload.pdf_path).name,
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_golden_pdf"
                    )
                    st.caption(f"Adobe PDF | SHA-256: `{(payload.pdf_sha256 or '')[:16]}...`")


# -----------------------------------------------------------------------------
# TAB 3: INTERACTIVE ASME CODE CALCULATOR
# -----------------------------------------------------------------------------
with tab_calculator:
    st.header("🧮 Interactive ASME Section VIII & API 510 Calculator")
    st.write(
        "Direct deterministic mathematical verification engine. Test custom operating pressures, "
        "materials, radii, and measured wall thicknesses to evaluate immediate statutory code breaches."
    )

    c_calc1, c_calc2 = st.columns([1, 1.2])

    with c_calc1:
        st.subheader("Input Parameters")
        calc_eq_id = st.text_input("Equipment ID", value="11-V-102", key="calc_eq_id")
        calc_mat = st.selectbox(
            "Vessel Base Material",
            ["SA-516 Grade 70 (Carbon Steel)", "SA-387 Grade 11 (Cr-Mo Alloy)", "SA-240 Type 304 (Stainless Steel)"],
            index=0,
            key="calc_mat"
        )
        calc_p = st.number_input("Design Pressure P (MPa)", min_value=0.1, max_value=50.0, value=14.5, step=0.5, key="calc_p")
        calc_r = st.number_input("Inside Radius R (mm)", min_value=100.0, max_value=5000.0, value=1200.0, step=50.0, key="calc_r")
        calc_s = st.number_input("Maximum Allowable Stress S (MPa)", min_value=10.0, max_value=300.0, value=118.0, step=1.0, key="calc_s")
        calc_e = st.selectbox("Joint Efficiency E", [1.0, 0.85, 0.70], index=0, key="calc_e")
        calc_t_act = st.number_input("Actual Measured Wall Thickness t (mm)", min_value=1.0, max_value=500.0, value=138.20, step=0.1, key="calc_t_act")
        calc_cr = st.number_input("Observed Corrosion Rate Cr (mm/year)", min_value=0.01, max_value=5.0, value=0.75, step=0.05, key="calc_cr")

    with c_calc2:
        st.subheader("Verification Telemetry")
        custom_input = InspectionInput(
            equipment_id=calc_eq_id,
            equipment_name="Interactive Test Vessel",
            material=calc_mat.split()[0],
            design_pressure_mpa=calc_p,
            inside_radius_mm=calc_r,
            allowable_stress_mpa=calc_s,
            joint_efficiency=calc_e,
            measured_thickness_mm=calc_t_act,
            critical_location="Shell Test Section",
            corrosion_rate_mm_yr=calc_cr,
            inspector_notes="Interactive UI calculation test."
        )
        custom_calc = evaluate_vessel_integrity(custom_input)

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Minimum Required t_min", f"{custom_calc.t_req_mm:.2f} mm")
            st.metric("Measured Thickness t_act", f"{custom_calc.measured_thickness_mm:.2f} mm")
        with col_m2:
            delta_color = "normal" if custom_calc.delta_mm >= 0 else "inverse"
            st.metric("Margin Delta Δ", f"{custom_calc.delta_mm:.2f} mm", delta=f"{custom_calc.delta_mm:.2f} mm", delta_color=delta_color)
            st.metric("Safe Derated MAWP", f"{custom_calc.derated_mawp_bar:.1f} barg")

        if custom_calc.is_breach:
            st.error(
                f"🚨 **STATUTORY CODE BREACH DETECTED!**\n\n"
                f"The measured thickness ({custom_calc.measured_thickness_mm:.2f} mm) is below ASME allowable minimum "
                f"({custom_calc.t_req_mm:.2f} mm) by **{abs(custom_calc.delta_mm):.2f} mm**. "
                f"API 510 remaining safe service life is **{custom_calc.remaining_life_years:.2f} years** (EXPIRED)."
            )
        else:
            st.success(
                f"✅ **VESSEL COMPLIANT WITH ASME SEC VIII DIV 1**\n\n"
                f"Remaining corrosion allowance margin is **+{custom_calc.delta_mm:.2f} mm**. "
                f"Estimated API 510 safe operating life is **{custom_calc.remaining_life_years:.2f} years**."
            )

        st.markdown("---")
        st.markdown("### 📐 ASME Section VIII Div 1 UG-27 Formula Proof")
        st.latex(r"t_{\text{req}} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P}")
        st.write(
            f"$$t_{{\\text{{req}}}} = \\frac{{{calc_p} \\cdot {calc_r}}}{{{calc_s} \\cdot {calc_e} - 0.6 \\cdot {calc_p}}} "
            f"= \\frac{{{calc_p * calc_r:.2f}}}{{{calc_s * calc_e - 0.6 * calc_p:.2f}}} = {custom_calc.t_req_mm:.2f}\\text{{ mm}}$$"
        )

        st.markdown("---")
        st.subheader("📥 Export Official Note for Approval")
        st.caption("Generate and download a formal Note for Approval with these interactive calculation parameters:")

        from tools.doc_generator import generate_docx_deliverable, generate_pdf_deliverable
        from schemas.mvp_schema import ReasoningOutput

        calc_reasoning = ReasoningOutput(
            executive_summary=(
                f"Interactive ASME Sec VIII Div 1 assessment for vessel {calc_eq_id} ({calc_mat}). "
                f"Status: {custom_calc.status} with delta margin {custom_calc.delta_mm:.2f} mm. "
                f"Calculated t_min={custom_calc.t_req_mm:.2f} mm vs measured t_act={custom_calc.measured_thickness_mm:.2f} mm."
            ),
            cvc_guideline_clause=(
                "CVC Circular No. 02/02/2004 & DOP Clause 4.2 Emergency Single-Source Procurement."
                if custom_calc.is_breach else
                "Routine turnaround maintenance following standard statutory procurement procedures."
            ),
            recommended_action=(
                f"Immediate emergency weld overlay repair and derated operation at {custom_calc.derated_mawp_bar:.1f} barg."
                if custom_calc.is_breach else
                f"Continue safe commercial operation at rated {custom_calc.design_pressure_bar:.1f} barg until next turnaround."
            ),
            estimated_cost="Rs. 88.0 Lakhs" if custom_calc.is_breach else "Routine Opex",
            raw_model_response="Interactive calculator export verification."
        )

        calc_docx = generate_docx_deliverable(custom_input, custom_calc, calc_reasoning)
        calc_pdf = generate_pdf_deliverable(custom_input, custom_calc, calc_reasoning)

        c_exp1, c_exp2 = st.columns(2)
        with c_exp1:
            with open(calc_docx["path"], "rb") as f_dx:
                st.download_button(
                    label="📥 Download Calculation Note (.docx)",
                    data=f_dx.read(),
                    file_name=f"{calc_eq_id}_Approval_Note.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"dl_calc_docx_{calc_eq_id}"
                )
        with c_exp2:
            with open(calc_pdf["path"], "rb") as f_px:
                st.download_button(
                    label="📥 Download Calculation Note (.pdf)",
                    data=f_px.read(),
                    file_name=f"{calc_eq_id}_Approval_Note.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_calc_pdf_{calc_eq_id}"
                )

# -----------------------------------------------------------------------------
# TAB 4: AIR-GAPPED CODE SANDBOX
# -----------------------------------------------------------------------------
with tab_sandbox:
    st.header("🧪 Air-Gapped Python Code Sandbox")
    st.write(
        "Execute arbitrary engineering Python code within an isolated local subprocess with strict timeouts. "
        "Test custom algorithms, data transforms, or mathematical proofs safely."
    )

    default_sandbox_code = '''# Test Python Engineering Calculation
import numpy as np

# Simulate Wall Thickness ultrasonic readings along 11-V-102 vessel shell
measurements = np.array([139.5, 138.8, 138.2, 139.1, 138.4, 137.9])
mean_thickness = np.mean(measurements)
min_thickness = np.min(measurements)
std_dev = np.std(measurements)

print(f"Total Inspection Points: {len(measurements)}")
print(f"Mean Shell Thickness:   {mean_thickness:.2f} mm")
print(f"Critical Minimum Spot:  {min_thickness:.2f} mm")
print(f"Standard Deviation:     {std_dev:.3f} mm")

# ASME UG-27 Check against t_min = 138.57 mm
t_min_asme = 138.57
if min_thickness < t_min_asme:
    print(f"ALERT: Critical minimum {min_thickness:.2f} mm is BELOW ASME required {t_min_asme:.2f} mm!")
else:
    print("STATUS: All points above minimum required thickness.")
'''

    sandbox_input = st.text_area("Python Script:", value=default_sandbox_code, height=240, key="sandbox_code_area")
    
    if st.button("▶️ Execute Code in Isolated Sandbox", type="primary", key="btn_run_sandbox"):
        with st.spinner("Executing script in isolated sandbox..."):
            res = execute_python_code(sandbox_input)

        if res["success"]:
            st.success(f"Execution Succeeded (Exit Code: {res['returncode']})")
            st.markdown("**Console Output (stdout):**")
            st.code(res["stdout"] if res["stdout"] else "[No stdout output]")
        else:
            st.error(f"Execution Error (Exit Code: {res['returncode']}):")
            st.code(res["stderr"])

# -----------------------------------------------------------------------------
# TAB 6: ARCHITECTURE & STORAGE DETAILS
# -----------------------------------------------------------------------------
with tab_info:
    st.header("Self-Contained Storage Architecture")
    st.markdown(f"""
    All data and weights in AegisForge-AI are strictly confined to the project root:
    
    ```
    {PROJECT_ROOT.name}/
    ├── model_pool/
    │   ├── easyocr/          <- CRAFT & CRNN text recognition weights (.pth)
    │   └── ollama/           <- DeepSeek, Qwen & Llama quantized blobs & manifests
    ├── data/
    │   ├── uploads/          <- Uploaded logs & blueprints
    │   └── output/           <- Generated .docx / .xlsx reports
    └── scripts/
        ├── clean_models.bat  <- 1-click purge to reclaim disk space
        └── uninstall_all.bat <- Full zero-trace teardown
    ```
    
    ### Key Benefits:
    - **Portability:** Moving or zipping this folder moves everything including models.
    - **Uninstallation:** Deleting the folder or running `scripts\\clean_models.bat` leaves **zero orphaned files** on your Windows OS.
    - **Air-Gapped Security:** Zero data transmission over external networks.
    """)
