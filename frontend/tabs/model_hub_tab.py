import time
import streamlit as st
from config.settings import logger
from models.model_downloader import (
    is_model_installed,
    pull_ollama_model_stream,
    install_easyocr_models,
    purge_model,
    MODEL_METADATA,
    is_ollama_running, 
    find_ollama_executable, 
    start_ollama_server
)

def is_mid_installed(mid: str, installed_set: set) -> bool:
    if mid == "easyocr":
        return "easyocr" in installed_set
    return any(mid in name for name in installed_set if name)

@st.cache_data(ttl=3600)
def check_nvidia_gpu() -> bool:
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        return result.returncode == 0
    except (FileNotFoundError, Exception):
        return False

@st.cache_data(ttl=3600)
def is_pytorch_installed() -> bool:
    try:
        import torch
        return True
    except ImportError:
        return False

def render_model_hub_tab(ollama_active, ollama_path, installed_set, clear_system_cache):
    st.markdown("## 📦 Model Hub")
    st.markdown("Download and manage local AI models. All weights are stored in `model_pool/`.")

    has_gpu = check_nvidia_gpu()
    pytorch_installed = is_pytorch_installed()
    
    gpu_status_text = "<span style='color: #4ade80;'>✅ NVIDIA GPU Detected</span>" if has_gpu else "<span style='color: #f87171;'>❌ No NVIDIA GPU Detected</span>"

    if pytorch_installed:
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid #4ade80; margin-bottom: 24px; padding: 16px 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <h3 style="margin: 0; color: #4ade80; font-size: 1.1rem;">✅ PyTorch Engine Ready</h3>
            </div>
            <p style="color: #94a3b8; font-size: 0.9rem; margin: 8px 0 0 0;">
                The mandatory PyTorch dependency is installed. EasyOCR Vision Engine is fully functional.<br>
                <strong>Hardware Auto-Detection:</strong> {gpu_status_text}
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # PyTorch Dependency Installer
        st.markdown(f"""
        <div class="glass-card" style="border-left: 4px solid #ef4444; margin-bottom: 24px;">
            <h3 style="margin-top: 0; color: #f87171;">⚠️ Mandatory Dependency: PyTorch</h3>
            <p style="color: #cbd5e1; font-size: 0.95rem;">
                PyTorch is strictly required to run the <strong>EasyOCR Vision Engine</strong> and perform tensor calculations.
                You must download and install it once.
            </p>
            <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 8px;">
                <strong>Hardware Auto-Detection:</strong> {gpu_status_text}<br>
                We have automatically disabled the incorrect option for your hardware.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col_pt1, col_pt2, col_pt3 = st.columns([1, 1, 2])
        with col_pt1:
            if st.button("🔧 Download & Install PyTorch (GPU)", use_container_width=True, disabled=not has_gpu):
                with st.spinner("Downloading PyTorch with CUDA support (this will take a few minutes)..."):
                    try:
                        import subprocess
                        import sys
                        cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu124"]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            st.success("✅ PyTorch GPU Installed Successfully! Please restart the app.")
                        else:
                            st.error(f"Installation failed: {result.stderr}")
                    except Exception as e:
                        st.error(f"Failed to run installer: {e}")
                        
        with col_pt2:
            if st.button("⚙️ Download & Install PyTorch (CPU)", use_container_width=True, disabled=has_gpu):
                with st.spinner("Downloading PyTorch CPU version (this will take a minute)..."):
                    try:
                        import subprocess
                        import sys
                        cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cpu"]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            st.success("✅ PyTorch CPU Installed Successfully! Please restart the app.")
                        else:
                            st.error(f"Installation failed: {result.stderr}")
                    except Exception as e:
                        st.error(f"Failed to run installer: {e}")
                    
    st.markdown("---")

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
                        try:
                            logger.info(f"Starting EasyOCR installation for {model_id}...")
                            for step in install_easyocr_models():
                                pct = int(step.get("percent", 0))
                                progress_bar.progress(pct, text=step.get("status", "Processing..."))
                                status_text.info(step.get("status", ""))
                                time.sleep(0.3)
                            st.success(f"✅ {info['title']} installed!")
                            logger.info(f"Successfully installed EasyOCR models.")
                            st.rerun()
                        except Exception as e:
                            logger.error(f"Exception during EasyOCR installation: {e}")
                            st.error(f"Error installing EasyOCR: {e}")
                    else:
                        if not is_ollama_running():
                            logger.warning("Attempted to download model but Ollama is offline.")
                            if not start_ollama_server():
                                st.error("Start Ollama first.")
                                continue

                        try:
                            logger.info(f"Starting Ollama pull for model {model_id}...")
                            for update in pull_ollama_model_stream(model_id):
                                if update.get("status") == "error":
                                    status_text.error(f"❌ {update.get('error')}")
                                    logger.error(f"Ollama pull error for {model_id}: {update.get('error')}")
                                    break

                                pct = max(0, min(100, int(update.get("percent", 0))))
                                status_msg = update.get("status", "Downloading...")
                                total_mb = update.get("total_mb", 0)
                                comp_mb = update.get("completed_mb", 0)

                                if update.get("retrying"):
                                    status_text.warning(status_msg)
                                    progress_bar.progress(pct, text=f"⚠️ Resuming from {pct}%...")
                                    logger.warning(f"Ollama pull retrying for {model_id} at {pct}%.")
                                else:
                                    label = f"{status_msg} ({pct}% — {comp_mb:.0f}/{total_mb:.0f} MB)" if total_mb > 0 else f"{status_msg} ({pct}%)"
                                    progress_bar.progress(pct, text=label)

                            if is_model_installed(model_id):
                                progress_bar.progress(100, text="Complete!")
                                st.success(f"✅ {info['title']} ready!")
                                logger.info(f"Successfully downloaded and verified model: {model_id}")
                                clear_system_cache()
                                time.sleep(1)
                                st.rerun()
                            else:
                                logger.error(f"Failed to verify model {model_id} after download completed.")
                                st.error(f"Failed to verify {model_id} after downloading.")
                        except Exception as e:
                            logger.exception(f"Exception during Ollama model download for {model_id}: {e}")
                            st.error(f"Error downloading {model_id}: {e}")

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
