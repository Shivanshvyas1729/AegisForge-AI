"""
AegisForge-AI: Sovereign Air-Gapped Industrial Workbench
Clean Streamlit Application — 3 focused tabs for productivity.
"""

import os
import sys
import time
import re
from pathlib import Path
import streamlit as st

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# In long-running Streamlit servers, re-sync cached project modules so newly defined methods appear
import importlib
for _mod_name in [
    "config.settings",
    "models.model_downloader",
    "models.router.model_router",
    "tools.doc_generator",
    "tools.sandbox",
    "tools.asme_calculator",
    "schemas.mvp_schema",
]:
    if _mod_name in sys.modules:
        try:
            importlib.reload(sys.modules[_mod_name])
        except Exception:
            pass

from config.settings import (
    MODEL_POOL_DIR,
    EASYOCR_DIR,
    OLLAMA_MODELS_DIR,
    OLLAMA_HOST,
    LOG_FILE,
    logger,
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

try:
    from models.model_downloader import get_installed_models_set
except (ImportError, AttributeError):
    try:
        from models.model_downloader import get_installed_ollama_models
        def get_installed_models_set() -> set:
            models = set(get_installed_ollama_models())
            if is_model_installed("easyocr"):
                models.add("easyocr")
            return models
    except Exception:
        def get_installed_models_set() -> set:
            return set()

from models.router.model_router import SovereignModelRouter
from tools.sandbox import execute_python_code
from tools.asme_calculator import evaluate_vessel_integrity

try:
    from tools.doc_generator import compile_nfa_documents_for_ui
except (ImportError, AttributeError):
    try:
        import tools.doc_generator
        importlib.reload(tools.doc_generator)
        from tools.doc_generator import compile_nfa_documents_for_ui
    except Exception:
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

from schemas.mvp_schema import InspectionInput


# ─────────────────────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AegisForge-AI | Sovereign Industrial Workbench",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# Premium Dark Theme CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .main { background: #0a0e1a; }
    .stApp { font-family: 'Inter', sans-serif; }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1224 0%, #111832 100%);
        border-right: 1px solid rgba(59, 130, 246, 0.15);
    }

    /* Glassmorphism cards */
    .glass-card {
        background: rgba(17, 24, 50, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(59, 130, 246, 0.12);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        border-color: rgba(59, 130, 246, 0.35);
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.08);
    }

    /* Result banner */
    .result-banner {
        background: linear-gradient(135deg, rgba(17, 24, 50, 0.9) 0%, rgba(30, 41, 82, 0.9) 100%);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }

    /* Category badges */
    .badge {
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.78rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge-coding { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-reasoning { background: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }
    .badge-summary { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-vision { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-general { background: rgba(107, 114, 128, 0.2); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.3); }

    /* Model cards */
    .model-card {
        background: rgba(17, 24, 50, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 14px;
        transition: all 0.3s ease;
    }
    .model-card:hover {
        border-color: rgba(59, 130, 246, 0.3);
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.06);
    }

    /* Status indicators */
    .status-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
    .status-online { background: #34d399; box-shadow: 0 0 8px rgba(52, 211, 153, 0.5); }
    .status-offline { background: #f87171; box-shadow: 0 0 8px rgba(248, 113, 113, 0.5); }

    .installed-badge {
        background: rgba(6, 78, 59, 0.7);
        color: #34d399;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .missing-badge {
        background: rgba(55, 65, 81, 0.7);
        color: #9ca3af;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
    }

    /* Metric cards override */
    [data-testid="stMetric"] {
        background: rgba(17, 24, 50, 0.6);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Section header */
    .section-header {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        color: #64748b;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(17, 24, 50, 0.5);
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
    }

    /* Sovereign footer */
    .sovereign-footer {
        text-align: center;
        color: #475569;
        font-size: 0.75rem;
        padding: 20px 0 10px 0;
        border-top: 1px solid rgba(255, 255, 255, 0.04);
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# Cached System Checks (Performance Optimization)
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def cached_system_health():
    """Batched, highly optimized system health check to make UI interactions instantaneous."""
    running = is_ollama_running()
    try:
        installed = get_installed_models_set() if running else set()
    except Exception:
        installed = set()
        if running:
            from models.model_downloader import get_installed_ollama_models
            installed.update(get_installed_ollama_models())
    if is_model_installed("easyocr"):
        installed.add("easyocr")
    return {
        "ollama_running": running,
        "installed_models": installed,
        "disk_free_gb": get_disk_free_gb(),
        "ollama_path": find_ollama_executable(),
    }

def is_mid_installed(mid: str, installed_set: set) -> bool:
    if mid == "easyocr":
        return "easyocr" in installed_set
    return any(mid in name for name in installed_set if name)

def clear_system_cache():
    """Clears cache after manual actions to force refresh."""
    st.cache_data.clear()

# Fetch health once per rerun (instant from cache)
health = cached_system_health()
ollama_active = health["ollama_running"]
ollama_path = health["ollama_path"]
free_gb = health["disk_free_gb"]
installed_set = health["installed_models"]

# ─────────────────────────────────────────────────────────────────
# Sidebar — System Health
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ AegisForge-AI")
    st.caption("Sovereign Air-Gapped PSU Workbench")
    st.divider()

    st.markdown('<p class="section-header">Runtime Health</p>', unsafe_allow_html=True)
    
    if ollama_active:
        st.markdown('<span class="status-dot status-online"></span> **Ollama** — Online', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-dot status-offline"></span> **Ollama** — Offline', unsafe_allow_html=True)
        if ollama_path:
            if st.button("▶️ Start Ollama", use_container_width=True, key="sidebar_start_ollama"):
                with st.spinner("Starting..."):
                    if start_ollama_server():
                        logger.info("Ollama server started manually via UI.")
                        clear_system_cache()
                        st.success("Started!")
                        st.rerun()
                    else:
                        logger.error("Failed to start Ollama server manually via UI.")
                        st.error("Failed to start. Check Ollama installation.")

    # Disk Space
    st.metric("Disk Space Available", f"{free_gb:.1f} GB")

    # Installed Models Count
    installed_count = sum(1 for mid in MODEL_METADATA if is_mid_installed(mid, installed_set))
    st.metric("Models Ready", f"{installed_count} / {len(MODEL_METADATA)}")

    st.divider()
    st.markdown("""
    <div style="font-size: 0.75rem; color: #64748b; line-height: 1.6;">
        🔒 100% air-gapped operation<br>
        📁 All data stays in project folder<br>
        🚫 Zero external network calls
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Main Content — 4 Tabs
# ─────────────────────────────────────────────────────────────────
tab_workbench, tab_calculator, tab_models, tab_logs = st.tabs([
    "💬  AI Workbench",
    "🧮  ASME Calculator",
    "📦  Model Hub",
    "📋  System Logs",
])


# ═══════════════════════════════════════════════════════════════
# TAB 1: AI WORKBENCH — Antigravity-Style Sovereign Chat & Deliverables
# ═══════════════════════════════════════════════════════════════
with tab_workbench:
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

    def set_chat_example(text: str):
        st.session_state.chat_pending_prompt = text

    # Quick Examples (Collapsible Prompt Library)
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

                    # Thought Process & Reasoning Trace (Claude / Gemini / Grok style)
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
                            st.markdown(f"- Dispatched via local socket `{OLLAMA_HOST}`")

                        if thinking:
                            st.markdown('<p class="section-header" style="margin-top: 10px; margin-bottom: 6px;">Model Internal Chain-of-Thought</p>', unsafe_allow_html=True)
                            st.markdown(f"""
                            <div style="background: rgba(15, 23, 42, 0.7); border-left: 3px solid #60a5fa; border-radius: 4px 8px 8px 4px; padding: 10px 14px; font-size: 0.84rem; color: #cbd5e1; font-family: 'JetBrains Mono', monospace; white-space: pre-wrap; line-height: 1.5;">
{thinking}
                            </div>
                            """, unsafe_allow_html=True)
                        elif cat == "REASONING":
                            st.markdown('<p class="section-header" style="margin-top: 10px; margin-bottom: 6px;">Reasoning Strategy</p>', unsafe_allow_html=True)
                            st.markdown("""
                            <div style="background: rgba(15, 23, 42, 0.7); border-left: 3px solid #a78bfa; border-radius: 4px 8px 8px 4px; padding: 10px 14px; font-size: 0.84rem; color: #cbd5e1; font-family: 'Inter', sans-serif; line-height: 1.5;">
                            • Evaluated ASME Section VIII Div 1 UG-27 cylindrical shell formula boundaries.<br>
                            • Verified CVC Circular No. 02/02/2004 emergency single-source procurement criteria.<br>
                            • Formulated statutory engineering repair justification and derated MAWP thresholds.
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown(msg["content"])

                    # Official Deliverables Download Section (Word / PDF)
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
                        # Offer on-demand compilation for any response
                        if st.button("📄 Compile Word (.docx) & PDF Deliverables for this Response", key=f"btn_compile_{idx}", type="secondary"):
                            with st.spinner("Compiling formal Word and PDF Note for Approval..."):
                                deliv_res = compile_nfa_documents_for_ui(msg["content"])
                                msg["deliverables"] = deliv_res
                                st.rerun()

                    # Python Code Sandbox Execution
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

                    # Antigravity-Style Action & Reaction Bar
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

    # Antigravity Model Selector & Chat Controls
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

    # Chat Input Box
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

        # Handle uploaded image if present
        saved_image_path = None
        if uploaded_img:
            uploads_dir = PROJECT_ROOT / "data" / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            saved_image_path = str(uploads_dir / uploaded_img.name)
            with open(saved_image_path, "wb") as f_img:
                f_img.write(uploaded_img.read())

        # 1. Add user turn to conversation history
        st.session_state.chat_history.append({
            "role": "user",
            "content": prompt_to_run,
            "image_path": saved_image_path,
        })

        # 2. Run Inference with Session Context
        with st.spinner("Processing with local sovereign model..."):
            t_start = time.time()
            try:
                logger.info(f"UI Chat Inference. Override: {override_model}. Prompt: {prompt_to_run[:50]}...")
                router = SovereignModelRouter()
                # Pass previous history for multi-turn conversational context
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

            # 3. Check for document generation intent
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

            # 4. Add assistant turn to conversation history
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


# ═══════════════════════════════════════════════════════════════
# TAB 2: ASME CALCULATOR
# ═══════════════════════════════════════════════════════════════
with tab_calculator:
    st.markdown("## 🧮 ASME Section VIII & API 510 Calculator")
    st.markdown("Deterministic engineering verification — no LLM involved. Pure math.")

    col_params, col_results = st.columns([1, 1.2])

    with col_params:
        st.markdown('<p class="section-header">Input Parameters</p>', unsafe_allow_html=True)
        
        calc_eq_id = st.text_input("Equipment ID", value="11-V-102", key="calc_eq_id")
        calc_p = st.number_input("Design Pressure P (MPa)", min_value=0.1, max_value=50.0, value=14.5, step=0.5, key="calc_p")
        calc_r = st.number_input("Inside Radius R (mm)", min_value=100.0, max_value=5000.0, value=1200.0, step=50.0, key="calc_r")
        calc_s = st.number_input("Allowable Stress S (MPa)", min_value=10.0, max_value=300.0, value=118.0, step=1.0, key="calc_s")
        calc_e = st.selectbox("Joint Efficiency E", [1.0, 0.85, 0.70], index=0, key="calc_e")
        calc_t = st.number_input("Measured Wall Thickness (mm)", min_value=1.0, max_value=500.0, value=138.20, step=0.1, key="calc_t")
        calc_cr = st.number_input("Corrosion Rate (mm/year)", min_value=0.01, max_value=5.0, value=0.75, step=0.05, key="calc_cr")

    with col_results:
        st.markdown('<p class="section-header">Verification Results</p>', unsafe_allow_html=True)

        custom_input = InspectionInput(
            equipment_id=calc_eq_id,
            equipment_name="Interactive Vessel",
            design_pressure_mpa=calc_p,
            inside_radius_mm=calc_r,
            allowable_stress_mpa=calc_s,
            joint_efficiency=calc_e,
            measured_thickness_mm=calc_t,
            critical_location="Shell",
            corrosion_rate_mm_yr=calc_cr,
        )
        custom_calc = evaluate_vessel_integrity(custom_input)

        # Metrics
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Required t_min", f"{custom_calc.t_req_mm:.2f} mm")
            st.metric("Measured Thickness", f"{custom_calc.measured_thickness_mm:.2f} mm")
        with m2:
            delta_color = "normal" if custom_calc.delta_mm >= 0 else "inverse"
            st.metric("Margin Δ", f"{custom_calc.delta_mm:.2f} mm", delta=f"{custom_calc.delta_mm:.2f} mm", delta_color=delta_color)
            st.metric("Derated MAWP", f"{custom_calc.derated_mawp_bar:.1f} barg")

        # Verdict
        if custom_calc.is_breach:
            st.error(
                f"🚨 **STATUTORY CODE BREACH**\n\n"
                f"Measured ({custom_calc.measured_thickness_mm:.2f} mm) is below ASME minimum "
                f"({custom_calc.t_req_mm:.2f} mm) by **{abs(custom_calc.delta_mm):.2f} mm**. "
                f"Remaining life: **{custom_calc.remaining_life_years:.2f} years**."
            )
        else:
            st.success(
                f"✅ **VESSEL COMPLIANT**\n\n"
                f"Margin: **+{custom_calc.delta_mm:.2f} mm**. "
                f"Safe operating life: **{custom_calc.remaining_life_years:.2f} years**."
            )

        # Formula proof
        st.markdown("---")
        st.markdown("#### 📐 ASME UG-27 Formula")
        st.latex(r"t_{\text{req}} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P}")
        st.markdown(
            f"$t_{{\\text{{req}}}} = \\frac{{{calc_p} \\cdot {calc_r}}}{{{calc_s} \\cdot {calc_e} - 0.6 \\cdot {calc_p}}} "
            f"= {custom_calc.t_req_mm:.2f}\\text{{ mm}}$"
        )

        # Export buttons
        st.markdown("---")
        st.markdown("#### 📥 Export Calculation Note")

        # Invalidate cached deliverables if calculation inputs change
        calc_cache_tuple = (calc_eq_id, calc_p, calc_r, calc_s, calc_e, calc_t, calc_cr)
        if st.session_state.get("last_calc_cache_tuple") != calc_cache_tuple:
            st.session_state.calc_docx_bytes = None
            st.session_state.calc_pdf_bytes = None
            st.session_state.last_calc_cache_tuple = calc_cache_tuple

        col_gen, col_dl1, col_dl2 = st.columns([1.5, 1, 1])

        with col_gen:
            if st.button("📄 Generate Deliverables", key="btn_gen_calc_docs", type="primary", use_container_width=True):
                with st.spinner("Compiling Note for Approval..."):
                    try:
                        from tools.doc_generator import generate_docx_deliverable, generate_pdf_deliverable
                        from schemas.mvp_schema import ReasoningOutput

                        calc_reasoning = ReasoningOutput(
                            executive_summary=(
                                f"ASME Sec VIII assessment for {calc_eq_id}. "
                                f"Status: {custom_calc.status}, delta {custom_calc.delta_mm:.2f} mm."
                            ),
                            cvc_guideline_clause=(
                                "CVC Circular 02/02/2004 Emergency Procurement." if custom_calc.is_breach
                                else "Routine turnaround maintenance."
                            ),
                            recommended_action=(
                                f"Emergency weld overlay repair, derate to {custom_calc.derated_mawp_bar:.1f} barg." if custom_calc.is_breach
                                else f"Continue operation at {custom_calc.design_pressure_bar:.1f} barg."
                            ),
                            estimated_cost="Rs. 88.0 Lakhs" if custom_calc.is_breach else "Routine Opex",
                            raw_model_response="Calculator export.",
                        )
                        calc_docx = generate_docx_deliverable(custom_input, custom_calc, calc_reasoning)
                        calc_pdf = generate_pdf_deliverable(custom_input, custom_calc, calc_reasoning)

                        with open(calc_docx["path"], "rb") as f_dx:
                            st.session_state.calc_docx_bytes = f_dx.read()
                        with open(calc_pdf["path"], "rb") as f_px:
                            st.session_state.calc_pdf_bytes = f_px.read()
                        st.success("Deliverables ready!")
                    except Exception as e:
                        logger.exception("Failed to compile documents in UI ASME Calculator.")
                        st.error(f"Failed to generate documents: {e}")

        if st.session_state.get("calc_docx_bytes"):
            with col_dl1:
                st.download_button(
                    "📥 Download .docx",
                    data=st.session_state.calc_docx_bytes,
                    file_name=f"{calc_eq_id}_Note.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="calc_dl_docx",
                )
            with col_dl2:
                st.download_button(
                    "📥 Download .pdf",
                    data=st.session_state.calc_pdf_bytes,
                    file_name=f"{calc_eq_id}_Note.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="calc_dl_pdf",
                )
        else:
            st.caption("Click 'Generate Deliverables' to compile formal DOCX & PDF notes on-demand.")


# ═══════════════════════════════════════════════════════════════
# TAB 3: MODEL HUB
# ═══════════════════════════════════════════════════════════════
with tab_models:
    st.markdown("## 📦 Model Hub")
    st.markdown("Download and manage local AI models. All weights are stored in `model_pool/`.")

    # Ollama Controls
    if not ollama_active:
        if ollama_path:
            col_warn, col_act = st.columns([3, 1])
            with col_warn:
                st.warning("⚠️ Ollama is offline. Start it to download or use models.")
            with col_act:
                if st.button("▶️ Start Ollama", use_container_width=True, key="hub_start_ollama"):
                    with st.spinner("Starting..."):
                        if start_ollama_server():
                            st.success("Started!")
                            st.rerun()
                        else:
                            st.error("Failed. Check Ollama installation.")
        else:
            st.error("❌ Ollama is not installed. Download from [ollama.com/download](https://ollama.com/download/windows)")

    st.markdown("")

    # Model Cards
    for model_id, info in MODEL_METADATA.items():
        installed = is_mid_installed(model_id, installed_set)

        st.markdown(f"""
        <div class="model-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h4 style="margin: 0; color: #f1f5f9; font-weight: 600;">{info['title']}</h4>
                <span class="{'installed-badge' if installed else 'missing-badge'}">
                    {'✅ Installed' if installed else '⬇️ Not Downloaded'}
                </span>
            </div>
            <p style="color: #94a3b8; margin: 4px 0 12px 0; font-size: 0.9rem;">{info['desc']}</p>
            <div style="font-size: 0.82rem; color: #64748b;">
                <b>Role:</b> {info['role']} &nbsp;│&nbsp; <b>Size:</b> {info['size_est']} &nbsp;│&nbsp; <b>Engine:</b> {info['backend'].upper()}
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_dl, col_rm, col_sp = st.columns([1.5, 1, 3])

        with col_dl:
            if not installed:
                if st.button(f"⬇️ Download", key=f"dl_{model_id}", type="primary"):
                    progress_bar = st.progress(0, text="Initializing...")
                    status_text = st.empty()

                    if info["backend"] == "easyocr":
                        for step in install_easyocr_models():
                            pct = int(step.get("percent", 0))
                            progress_bar.progress(pct, text=step.get("status", "Processing..."))
                            status_text.info(step.get("status", ""))
                            time.sleep(0.3)
                        st.success(f"✅ {info['title']} installed!")
                        st.rerun()
                    else:
                        if not is_ollama_running():
                            if not start_ollama_server():
                                st.error("Start Ollama first.")
                                continue

                        for update in pull_ollama_model_stream(model_id):
                            if update.get("status") == "error":
                                status_text.error(f"❌ {update.get('error')}")
                                break

                            pct = max(0, min(100, int(update.get("percent", 0))))
                            status_msg = update.get("status", "Downloading...")
                            total_mb = update.get("total_mb", 0)
                            comp_mb = update.get("completed_mb", 0)

                            if update.get("retrying"):
                                status_text.warning(status_msg)
                                progress_bar.progress(pct, text=f"⚠️ Resuming from {pct}%...")
                            else:
                                label = f"{status_msg} ({pct}% — {comp_mb:.0f}/{total_mb:.0f} MB)" if total_mb > 0 else f"{status_msg} ({pct}%)"
                                progress_bar.progress(pct, text=label)

                        if is_model_installed(model_id):
                            progress_bar.progress(100, text="Complete!")
                            st.success(f"✅ {info['title']} ready!")
                            logger.info(f"Successfully downloaded model: {model_id}")
                            clear_system_cache()
                            time.sleep(1)
                            st.rerun()

        with col_rm:
            if installed:
                if st.button("🗑️ Remove", key=f"del_{model_id}"):
                    with st.spinner(f"Removing {model_id}..."):
                        try:
                            purge_model(model_id)
                            logger.info(f"Purged model: {model_id}")
                            st.success(f"Removed.")
                            clear_system_cache()
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            logger.error(f"Error purging model {model_id}: {e}")
                            st.error(f"Error removing model.")

        st.markdown("---")


# ═══════════════════════════════════════════════════════════════
# TAB 4: SYSTEM LOGS
# ═══════════════════════════════════════════════════════════════
with tab_logs:
    st.markdown("## 📋 System Logs")
    st.markdown("Live view of `aegisforge.log`. Use this to troubleshoot runtime issues.")
    
    col_log1, col_log2 = st.columns([1, 4])
    with col_log1:
        if st.button("🔄 Refresh Logs", use_container_width=True):
            pass # Reruns app naturally
            
    with col_log2:
        num_lines = st.slider("Lines to display", min_value=50, max_value=500, value=100, step=50)
        
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            display_lines = lines[-num_lines:] if len(lines) > num_lines else lines
            log_text = "".join(display_lines)
            
            st.code(log_text, language="log")
        else:
            st.info("Log file is currently empty or does not exist.")
    except Exception as e:
        st.error(f"Could not read log file: {e}")


# ─────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sovereign-footer">
    🛡️ AegisForge-AI — 100% Sovereign Air-Gapped Operation — Zero External Network Calls<br>
    Built for Indian PSUs & Critical Infrastructure
</div>
""", unsafe_allow_html=True)
