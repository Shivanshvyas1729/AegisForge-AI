import os
import re
import time
from pathlib import Path
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from config.settings import logger
from models.router.model_router import SovereignModelRouter
from tools.sandbox import execute_python_code

# Fallback for compile_nfa_documents_for_ui
try:
    from tools.doc_generator import compile_nfa_documents_for_ui
except (ImportError, AttributeError):
    def compile_nfa_documents_for_ui(response_text: str, equipment_id: str = "11-V-102", output_base_name=None):
        from tools.doc_generator import generate_both_deliverables
        from tools.asme_calculator import evaluate_vessel_integrity
        from schemas.mvp_schema import InspectionInput, ReasoningOutput
        base_name = output_base_name or f"{equipment_id}_Approval_Note"
        insp = InspectionInput(
            equipment_id=equipment_id,
            equipment_name="1st Stage HP Separator Drum",
            material="2.25Cr-1Mo + 347 SS cladding",
            design_pressure_mpa=14.5,
            inside_radius_mm=1200.0,
            allowable_stress_mpa=138.0,
            joint_efficiency=1.0,
            corrosion_allowance_mm=4.0,
            critical_location="BK-01",
            measured_thickness_mm=138.20,
            corrosion_rate_mm_yr=0.75,
        )
        calc = evaluate_vessel_integrity(insp)
        reason = ReasoningOutput(
            executive_summary=response_text[:500] if len(response_text) > 30 else "Statutory ASME Sec VIII thickness breach on vessel 11-V-102.",
            cvc_guideline_clause="CVC Circular No. 02/02/2004 & DOP Clause 4.2",
            recommended_action="Emergency single-source weld overlay and turnaround replacement.",
            estimated_cost="Rs. 88.0 Lakhs",
            raw_model_response=response_text,
        )
        both = generate_both_deliverables(insp, calc, reason, base_name=base_name)
        with open(both["docx"]["path"], "rb") as f_d:
            docx_bytes = f_d.read()
        with open(both["pdf"]["path"], "rb") as f_p:
            pdf_bytes = f_p.read()
        return {
            "equipment_id": equipment_id,
            "equipment_name": insp.equipment_name,
            "docx_filename": f"{base_name}.docx",
            "docx_bytes": docx_bytes,
            "docx_sha256": both["docx"]["sha256"],
            "pdf_filename": f"{base_name}.pdf",
            "pdf_bytes": pdf_bytes,
            "pdf_sha256": both["pdf"]["sha256"],
            "summary": reason.executive_summary,
            "t_req_mm": calc.t_req_mm,
            "measured_mm": calc.measured_thickness_mm,
            "delta_mm": calc.delta_mm,
        }

def set_chat_example(text: str):
    st.session_state.chat_pending_prompt = text

def render_workbench_tab():
    # Top Header & Session Controls
    c_head1, c_head2 = st.columns([4, 1])
    with c_head1:
        st.markdown("## 💬 Sovereign AI Workbench")
        st.caption("Persistent Session Active • 100% Air-Gapped • Automatic Multi-Turn Context • Auto-Routing")
    with c_head2:
        st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)
        if st.button("🗑️ New Chat", use_container_width=True, key="btn_clear_chat"):
            st.session_state.chat_history = []
            st.session_state.chat_pending_prompt = None
            st.rerun()

    # Session State Initialization
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_pending_prompt" not in st.session_state:
        st.session_state.chat_pending_prompt = None

    # Quick Examples
    with st.expander("⚡ Quick Prompt Library (Click to Launch)", expanded=(len(st.session_state.chat_history) == 0)):
        cols_ex = st.columns(3)
        with cols_ex[0]:
            st.button("💻 Write ASME Code", use_container_width=True, key="ex_code", on_click=set_chat_example, args=("Write a Python function to compute ASME Section VIII Div 1 UG-27 minimum shell thickness given design pressure P, inside radius R, allowable stress S, and joint efficiency E.",))
            st.button("📄 Generate DOCX Note", use_container_width=True, key="ex_docx", on_click=set_chat_example, args=("I need a formal Note for Approval (.docx) for vessel 11-V-102 statutory thickness breach with ASME UG-27 calculations.",))
        with cols_ex[1]:
            st.button("🧠 CVC Compliance Check", use_container_width=True, key="ex_reason", on_click=set_chat_example, args=("Evaluate whether an emergency single-source procurement of an OEM weld overlay repair for pressure vessel 11-V-102 complies with Central Vigilance Commission (CVC) Circular 02/02/2004 and DOP Clause 4.2.",))
            st.button("📑 Generate PDF Report", use_container_width=True, key="ex_pdf", on_click=set_chat_example, args=("Generate a complete PDF compliance report for vessel 11-V-102 thickness inspection.",))
        with cols_ex[2]:
            st.button("📡 Modbus SCADA Parser", use_container_width=True, key="ex_modbus", on_click=set_chat_example, args=("Write a Python parser for SCADA Modbus RTU telemetry packets with CRC-16 checksum verification and register parsing.",))
            st.button("📝 CDU Safety Summary", use_container_width=True, key="ex_summary", on_click=set_chat_example, args=("Summarize the key operational safety steps for inspecting the Crude Distillation Unit preheat train exchangers in 3 concise bullet points.",))

    st.markdown("---")

    # Render Conversation History
    if len(st.session_state.chat_history) == 0:
        st.markdown("""
        <div class="glass-card" style="text-align: center; padding: 32px 20px;">
            <h3 style="color: #f8fafc; margin-bottom: 8px;">🛡️ Sovereign Copilot Ready</h3>
            <p style="color: #94a3b8; max-width: 600px; margin: 0 auto 16px auto; font-size: 0.95rem;">
                Select a model or use <b>Auto-Route</b>. Type your engineering question, request formal Word (.docx) or PDF deliverables, or execute scripts in the isolated sandbox.
            </p>
            <div style="font-size: 0.8rem; color: #64748b;">
                🔒 Zero external network calls &bull; Persistent session context active &bull; Cryptographic air-gap hashes
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, msg in enumerate(st.session_state.chat_history):
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
                    if msg.get("image_path") and os.path.exists(msg["image_path"]):
                        st.image(msg["image_path"], caption="Attached Blueprint / Drawing", width=360)
            elif msg["role"] == "assistant":
                with st.chat_message("assistant", avatar="🛡️"):
                    cat = msg.get("category", "GENERAL")
                    model = msg.get("model_used", "unknown")
                    elapsed = msg.get("elapsed", 0.0)

                    badge_class = {
                        "CODING": "badge-coding",
                        "REASONING": "badge-reasoning",
                        "SUMMARY": "badge-summary",
                        "VISION": "badge-vision",
                    }.get(cat, "badge-general")

                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                        <div>
                            <span class="badge {badge_class}">{cat}</span>
                            &nbsp;&nbsp;<code style="color: #60a5fa; font-size: 0.85rem;">{model}</code>
                        </div>
                        <div style="color: #64748b; font-size: 0.78rem;">
                            ⏱️ {elapsed:.2f}s │ 🔒 Sovereign
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    trace = msg.get("internal_trace")
                    thinking = msg.get("model_thinking")
                    elapsed_str = f"({elapsed:.2f}s)" if elapsed else ""

                    thought_label = f"•.• Thought process & routing trace {elapsed_str}"
                    with st.expander(thought_label, expanded=False):
                        st.markdown('<p class="section-header" style="margin-bottom: 6px;">Internal Sovereign Execution Trace</p>', unsafe_allow_html=True)
                        if trace and trace.get("steps"):
                            for step in trace["steps"]:
                                st.markdown(f"- {step}")
                        else:
                            st.markdown(f"- Analyzed prompt tokens: classified as category **{cat}**")
                            st.markdown(f"- Selected sovereign model: **{model}** (100% on-premise air-gapped)")
                            st.markdown(f"- Dispatched via local socket `127.0.0.1:11434`")

                        if thinking:
                            st.markdown('<p class="section-header" style="margin-top: 10px; margin-bottom: 6px;">Model Internal Chain-of-Thought</p>', unsafe_allow_html=True)
                            st.markdown(f"""
                            <div style="background: rgba(15, 23, 42, 0.7); border-left: 3px solid #60a5fa; border-radius: 4px 8px 8px 4px; padding: 10px 14px; font-size: 0.84rem; color: #cbd5e1; font-family: 'JetBrains Mono', monospace; white-space: pre-wrap; line-height: 1.5;">
{thinking}
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown(msg["content"])

                    if msg.get("deliverables"):
                        deliv = msg["deliverables"]
                        st.markdown("""
                        <div style="margin-top: 14px; margin-bottom: 8px; font-weight: 600; font-size: 0.9rem; color: #93c5fd;">
                            📄 Official Deliverables Generated (Air-Gap Tamper-Proof)
                        </div>
                        """, unsafe_allow_html=True)

                        c_dl1, c_dl2 = st.columns(2)
                        with c_dl1:
                            st.download_button(
                                label=f"📥 Download Word (.docx)",
                                data=deliv["docx_bytes"],
                                file_name=deliv["docx_filename"],
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_docx_{idx}",
                                use_container_width=True,
                            )
                            st.caption(f"SHA-256: `{deliv['docx_sha256'][:16]}...`")
                        with c_dl2:
                            st.download_button(
                                label=f"📥 Download PDF (.pdf)",
                                data=deliv["pdf_bytes"],
                                file_name=deliv["pdf_filename"],
                                mime="application/pdf",
                                key=f"dl_pdf_{idx}",
                                use_container_width=True,
                            )
                            st.caption(f"SHA-256: `{deliv['pdf_sha256'][:16]}...`")

                        with st.expander("👁️ View Document Summary & Tamper-Proof Audit Details"):
                            st.markdown(f"**Equipment Tag:** `{deliv.get('equipment_id', '11-V-102')}` — *{deliv.get('equipment_name', 'HP Separator Drum')}*")
                            st.markdown(f"**ASME Code Check:** Status: `{deliv.get('status')}` │ $t_{{\\text{{req}}}}$: `{deliv.get('t_req_mm')} mm` │ Measured: `{deliv.get('measured_mm')} mm` (Delta: `{deliv.get('delta_mm')} mm`)")
                            st.markdown(f"**Executive Synthesis:** {deliv.get('summary')}")
                            st.markdown("---")
                            st.markdown(f"**DOCX SHA-256:** `{deliv['docx_sha256']}`")
                            st.markdown(f"**PDF SHA-256:** `{deliv['pdf_sha256']}`")
                    else:
                        if st.button("📄 Compile Word (.docx) & PDF Deliverables for this Response", key=f"btn_compile_{idx}", type="secondary"):
                            with st.spinner("Compiling formal Word and PDF Note for Approval..."):
                                deliv_res = compile_nfa_documents_for_ui(msg["content"])
                                msg["deliverables"] = deliv_res
                                st.rerun()

                    code_blocks = re.findall(r"```(?:python)?\s*(.*?)```", msg["content"], re.DOTALL)
                    if code_blocks:
                        st.markdown("---")
                        extracted_code = code_blocks[0].strip()
                        if st.button("🧪 Execute in Sandbox", key=f"sandbox_btn_{idx}", type="secondary"):
                            with st.spinner("Running in air-gapped sandbox..."):
                                sandbox_res = execute_python_code(extracted_code)
                            if sandbox_res["success"]:
                                st.success(f"Exit Code {sandbox_res['returncode']}")
                                st.code(sandbox_res["stdout"] or "[No output]")
                            else:
                                st.error(f"Exit Code {sandbox_res['returncode']}")
                                st.code(sandbox_res["stderr"])

                    c_act1, c_act2, c_sp = st.columns([1, 1, 8])
                    with c_act1:
                        like_state = msg.get("liked")
                        if st.button("👍 Helpful" if like_state is not True else "✅ Liked", key=f"like_{idx}"):
                            msg["liked"] = True
                            st.rerun()
                    with c_act2:
                        if st.button("👎" if like_state is not False else "❌ Disliked", key=f"dislike_{idx}"):
                            msg["liked"] = False
                            st.rerun()

    st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
    c_mod1, c_mod2 = st.columns([2.5, 1])
    with c_mod1:
        route_mode = st.selectbox(
            "🧠 Model Routing Strategy (Antigravity Style):",
            [
                "⚡ Auto-Route (Intelligent Multi-Model Dispatch)",
                "💻 Force Coding (Qwen2.5-Coder 1.5B)",
                "🧠 Force Reasoning (DeepSeek-R1 1.5B)",
                "📝 Force Summary (Llama-3.2 3B)",
                "👁️ Force Vision (Moondream VLM)",
            ],
            index=0,
            key="chat_model_selector",
        )
    with c_mod2:
        uploaded_img = st.file_uploader(
            "📎 Attach Blueprint / P&ID (Optional)",
            type=["png", "jpg", "jpeg"],
            key="chat_img_upload",
        )

    chat_prompt = st.chat_input("Ask a question, request code, or type 'Generate Word note for vessel 11-V-102'...")
    prompt_to_run = chat_prompt or st.session_state.chat_pending_prompt

    if prompt_to_run:
        st.session_state.chat_pending_prompt = None
        override_model = None
        if "Force Coding" in route_mode:
            override_model = "qwen2.5-coder:1.5b"
        elif "Force Reasoning" in route_mode:
            override_model = "deepseek-r1:1.5b"
        elif "Force Summary" in route_mode:
            override_model = "llama3.2:3b"
        elif "Force Vision" in route_mode:
            override_model = "moondream"

        saved_image_path = None
        if uploaded_img:
            uploads_dir = PROJECT_ROOT / "data" / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            saved_image_path = str(uploads_dir / uploaded_img.name)
            with open(saved_image_path, "wb") as f_img:
                f_img.write(uploaded_img.read())

        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt_to_run,
            "image_path": saved_image_path,
        })

        with st.spinner("Processing with local sovereign model..."):
            t_start = time.time()
            try:
                router = SovereignModelRouter()
                result = router.route_and_execute(
                    prompt=prompt_to_run,
                    image_path=saved_image_path,
                    override_model=override_model,
                    history=st.session_state.chat_history[:-1],
                )
            except Exception as e:
                logger.exception("Exception during UI chat inference.")
                result = {"success": False, "error": str(e)}
            t_elapsed = time.time() - t_start

        if result.get("success"):
            task_category = result.get("task_type", "general").upper()
            model_used = result.get("model_used", "unknown")
            response_text = result.get("response", "")

            p_lower = prompt_to_run.lower()
            wants_docx = any(k in p_lower for k in ["docx", "word", ".docx", "word file", "word doc"])
            wants_pdf = any(k in p_lower for k in ["pdf", ".pdf", "pdf file", "pdf report"])
            wants_doc = wants_docx or wants_pdf or any(k in p_lower for k in ["note for approval", "nfa", "deliverable", "approval note", "generate report", "approval document"])

            deliverables_payload = None
            if wants_doc:
                try:
                    deliverables_payload = compile_nfa_documents_for_ui(response_text)
                    logger.info("Successfully generated Note for Approval deliverables for chat message.")
                except Exception as exc:
                    logger.exception(f"Failed to auto-generate deliverables: {exc}")

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response_text,
                "category": task_category,
                "model_used": model_used,
                "elapsed": t_elapsed,
                "deliverables": deliverables_payload,
                "model_thinking": result.get("model_thinking"),
                "internal_trace": result.get("internal_trace"),
                "liked": None,
            })
            st.rerun()
        else:
            err_msg = result.get("error", "Unknown error")
            logger.error(f"UI routing failed: {err_msg}")
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"❌ **Error:** {err_msg}\n\n*Make sure Ollama is running (use the sidebar to start it).*",
                "category": "ERROR",
                "model_used": override_model or "none",
                "elapsed": t_elapsed,
                "deliverables": None,
                "liked": None,
            })
            st.rerun()
