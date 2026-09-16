"""
AegisForge-AI: Sovereign Air-Gapped Industrial Workbench
Clean Streamlit Application — 4 focused tabs for productivity.
"""

import os
import sys
from pathlib import Path
import streamlit as st

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import logger, get_disk_free_gb
from models.model_downloader import get_installed_models_set, is_model_installed, MODEL_METADATA, is_ollama_running, find_ollama_executable, start_ollama_server

# Import modular tabs
from frontend.tabs.workbench_tab import render_workbench_tab
from frontend.tabs.calculator_tab import render_calculator_tab
from frontend.tabs.model_hub_tab import render_model_hub_tab
from frontend.tabs.logs_tab import render_logs_tab

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
with open(Path(__file__).parent / "assets" / "style.css", "r") as f:
    css_content = f.read()
st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

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

with tab_workbench:
    render_workbench_tab()

with tab_calculator:
    render_calculator_tab()

with tab_models:
    render_model_hub_tab(ollama_active, ollama_path, installed_set, clear_system_cache)

with tab_logs:
    render_logs_tab()

# ─────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sovereign-footer">
    🛡️ AegisForge-AI — 100% Sovereign Air-Gapped Operation — Zero External Network Calls<br>
    Built for Indian PSUs & Critical Infrastructure
</div>
""", unsafe_allow_html=True)
