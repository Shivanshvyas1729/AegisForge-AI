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
    
    # ─────────────────────────────────────────────────────────────────
    # VRAM Memory Status (Live from Ollama /api/ps)
    # ─────────────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Live VRAM Status</p>', unsafe_allow_html=True)
    
    if "pin_router" not in st.session_state:
        st.session_state.pin_router = True
        
    pin_router_toggle = st.toggle("⚡ Pin Ultra-Light Router (0ms Latency)", value=st.session_state.pin_router, help="Keeps qwen2.5:0.5b locked in VRAM permanently. If disabled, it unloads after 5 minutes.")
    
    # Pre-warm logic to immediately load it into VRAM so it shows up in the UI
    if "router_prewarmed" not in st.session_state:
        st.session_state.router_prewarmed = True
        if st.session_state.pin_router and ollama_active:
            import requests
            try:
                requests.post('http://127.0.0.1:11434/api/generate', json={"model": "qwen2.5:0.5b", "keep_alive": -1}, timeout=2)
            except Exception:
                pass
    
    if pin_router_toggle != st.session_state.pin_router:
        st.session_state.pin_router = pin_router_toggle
        if ollama_active:
            import requests
            try:
                if not pin_router_toggle:
                    # Flush from VRAM instantly
                    requests.post('http://127.0.0.1:11434/api/generate', json={"model": "qwen2.5:0.5b", "keep_alive": 0}, timeout=1)
                else:
                    # Load into VRAM instantly
                    requests.post('http://127.0.0.1:11434/api/generate', json={"model": "qwen2.5:0.5b", "keep_alive": -1}, timeout=2)
            except Exception:
                pass
        st.rerun()
    
    @st.fragment(run_every=2)
    def render_vram_status():
        loaded_models = []
        if ollama_active:
            import requests
            try:
                resp = requests.get('http://127.0.0.1:11434/api/ps', timeout=1)
                if resp.status_code == 200:
                    loaded_models = resp.json().get('models', [])
            except Exception:
                pass
                
        if loaded_models:
            for m in loaded_models:
                m_name = m.get('name', 'unknown')
                m_vram = m.get('size_vram', 0) / (1024 * 1024)
                
                # Determine if it's permanently pinned or temporarily cached
                is_permanently_pinned = ("qwen2.5:0.5b" in m_name) and st.session_state.pin_router
                
                if is_permanently_pinned:
                    status_label = "⚡ LOADED (PINNED FOREVER)"
                    status_color = "#10b981"  # Green
                    bg_color = "rgba(16, 185, 129, 0.1)"
                    border_color = "rgba(16, 185, 129, 0.2)"
                else:
                    status_label = "⏳ CACHED (WILL UNLOAD IN 5m)"
                    status_color = "#f59e0b"  # Amber/Orange
                    bg_color = "rgba(245, 158, 11, 0.1)"
                    border_color = "rgba(245, 158, 11, 0.2)"
    
                st.markdown(f"""
                <div style="background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 4px; padding: 8px; margin-bottom: 8px;">
                    <div style="color: {status_color}; font-weight: 600; font-size: 0.85rem;">{status_label}</div>
                    <div style="font-family: monospace; font-size: 0.9rem; margin-top: 2px;">{m_name}</div>
                    <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 2px;">VRAM Usage: {m_vram:.1f} MB</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color: rgba(148, 163, 184, 0.1); border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 4px; padding: 8px;">
                <div style="color: #94a3b8; font-size: 0.85rem;">❄️ VRAM Empty (Cold)</div>
            </div>
            """, unsafe_allow_html=True)

    render_vram_status()

    st.divider()
    st.markdown("""
    <div style="font-size: 0.75rem; color: #64748b; line-height: 1.6;">
        🔒 100% air-gapped operation<br>
        📁 All data stays in project folder<br>
        🚫 Zero external network calls
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Main Content — 2 Tabs (Strict End-User vs Developer Separation)
# ─────────────────────────────────────────────────────────────────
tab_user, tab_dev = st.tabs([
    "💬 Sovereign Copilot (End-User)",
    "⚙️ Developer Testing Console (Admin)",
])

with tab_user:
    render_workbench_tab()

with tab_dev:
    st.markdown("### 🛠️ Developer Testing Console")
    st.caption("End-to-End Unit Testing and Component Verification")
    
    dev_view = st.radio(
        "Select Testing Environment:",
        ["🧮 ASME Math Sandbox", "📦 Model Hub & Registry", "📋 System Logs (Routing Trace)"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("---")
    
    if dev_view == "🧮 ASME Math Sandbox":
        render_calculator_tab()
    elif dev_view == "📦 Model Hub & Registry":
        render_model_hub_tab(ollama_active, ollama_path, installed_set, clear_system_cache)
    elif dev_view == "📋 System Logs (Routing Trace)":
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
