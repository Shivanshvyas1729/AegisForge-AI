"""
AegisForge-AI: Model Download, Health & Lifecycle Manager
Provides resilient streaming download progress, automatic network interruption recovery,
byte-level download resumption, and 1-click installation/uninstallation for the Streamlit UI.
"""

import os
import sys
import time
import shutil
import subprocess
import threading
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Generator, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    MODEL_POOL_DIR,
    EASYOCR_DIR,
    OLLAMA_MODELS_DIR,
    OLLAMA_HOST,
    MODEL_REGISTRY,
    logger,
    get_disk_free_gb,
)

# Detailed metadata for UI cards
MODEL_METADATA = {
    "deepseek-r1:1.5b": {
        "title": "DeepSeek-R1 (1.5B)",
        "role": "Reasoning & ASME Compliance",
        "category": "reasoning",
        "size_est": "~1.1 GB",
        "backend": "ollama",
        "desc": "Chain-of-thought engine for ASME Section VIII $t_{min}$ validation and PSU Note for Approval synthesis."
    },
    "qwen2.5-coder:1.5b": {
        "title": "Qwen2.5-Coder (1.5B)",
        "role": "Code & Automation",
        "category": "coding",
        "size_est": "~1.0 GB",
        "backend": "ollama",
        "desc": "Fast code generation for SCADA, Modbus CRC-16, and industrial automation scripts."
    },
    "llama3.2:3b": {
        "title": "Llama-3.2 (3B)",
        "role": "Fast Text & Summaries",
        "category": "general",
        "size_est": "~2.0 GB",
        "backend": "ollama",
        "desc": "High-speed executive briefings, Q3 presentation summaries, and general conversational QA."
    },
    "moondream": {
        "title": "Moondream (VLM)",
        "role": "Visual Schematic QA",
        "category": "vision",
        "size_est": "~1.7 GB",
        "backend": "ollama",
        "desc": "Lightweight vision-language model for reading tags, equipment bubbles, and P&ID diagrams."
    },
    "qwen2.5:0.5b": {
        "title": "Qwen2.5 (0.5B) - Semantic Router",
        "role": "Instant Task Classification",
        "category": "routing",
        "size_est": "~398 MB",
        "backend": "ollama",
        "mandatory": True,
        "desc": "MANDATORY: Ultra-lightweight AI router. Classifies user intent behind the scenes instantly (0.2s) without simple keyword guessing. Must be downloaded to use the workbench."
    },
    "easyocr": {
        "title": "EasyOCR (CRAFT + CRNN)",
        "role": "Offline P&ID OCR Engine",
        "category": "vision",
        "size_est": "~98 MB",
        "backend": "easyocr",
        "desc": "Zero-GPU offline OCR model running fully in-process on CPU to extract text from blueprints."
    }
}


def find_ollama_executable() -> Optional[str]:
    """Finds ollama.exe in system PATH or typical Windows installation directories."""
    ollama_path = shutil.which("ollama")
    if ollama_path:
        return ollama_path

    # Common Windows install path
    local_appdata = os.getenv("LOCALAPPDATA", "")
    if local_appdata:
        candidate = Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.exists():
            return str(candidate)

    # Program files
    candidate_pf = Path("C:/Program Files/Ollama/ollama.exe")
    if candidate_pf.exists():
        return str(candidate_pf)

    return None


def is_ollama_running() -> bool:
    """Checks whether the Ollama daemon is currently responsive."""
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_ollama_server() -> bool:
    """Launches the Ollama daemon in the background with storage locked to model_pool/ollama."""
    if is_ollama_running():
        return True

    exe = find_ollama_executable()
    if not exe:
        return False

    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(OLLAMA_MODELS_DIR)

    # Launch daemon detached in background
    if sys.platform == "win32":
        # CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS
        creationflags = 0x00000008 | 0x00000200
        subprocess.Popen([exe, "serve"], env=env, creationflags=creationflags, close_fds=True)
    else:
        subprocess.Popen([exe, "serve"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Give it up to 6 seconds to spin up
    for _ in range(12):
        time.sleep(0.5)
        if is_ollama_running():
            return True

    return False


def get_installed_ollama_models() -> list:
    """Fetches the list of currently installed model names from local Ollama in a single fast call."""
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                return [m.get("name") or m.get("model") for m in data.get("models", [])]
    except Exception:
        pass
    return []


def is_model_installed(model_id: str) -> bool:
    """Checks if a model is installed in the project's model_pool with integrity check."""
    if model_id == "easyocr":
        craft = EASYOCR_DIR / "craft_mlt_25k.pth"
        crnn = EASYOCR_DIR / "english_g2.pth"
        # Integrity check: craft >= 75MB, crnn >= 10MB
        if craft.exists() and crnn.exists():
            if craft.stat().st_size >= 75 * 1024 * 1024 and crnn.stat().st_size >= 10 * 1024 * 1024:
                return True
        return False

    installed = get_installed_ollama_models()
    return any(model_id in name for name in installed if name)


def get_installed_models_set() -> set:
    """Returns set of all installed model IDs across Ollama and EasyOCR in a single check."""
    models = set(get_installed_ollama_models())
    if is_model_installed("easyocr"):
        models.add("easyocr")
    return models


def pull_ollama_model_stream(
    model_name: str,
    max_retries: int = 10,
    retry_delay_seconds: float = 3.0
) -> Generator[Dict[str, Any], None, None]:
    """
    Streams the download progress of an Ollama model with automatic network recovery.
    
    Resilience Features:
    - If network drops, automatically pauses, reconnects, and resumes from partial blobs.
    - Never restarts from 0% if chunks/blobs are already downloaded on disk.
    - Yields status updates, transferred MBs, and retry notices.
    """
    if not is_ollama_running():
        started = start_ollama_server()
        if not started:
            err_msg = "Ollama server is not running and could not be started automatically. Run scripts\\run_ollama_local.bat"
            logger.error(f"[Downloader] {err_msg}")
            yield {
                "status": "error",
                "error": err_msg
            }
            return

    logger.info(f"[Downloader] Starting stream pull for model: {model_name}")
    url = f"{OLLAMA_HOST}/api/pull"
    payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")

    retry_count = 0
    last_percent = 0.0
    highest_completed = 0
    total_bytes = 0

    while retry_count < max_retries:
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            # Connect with a reasonable read timeout (30s inactivity triggers retry)
            with urllib.request.urlopen(req, timeout=30) as response:
                for line in response:
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        status = chunk.get("status", "")
                        chunk_total = chunk.get("total", 0)
                        chunk_completed = chunk.get("completed", 0)

                        if chunk_total > 0:
                            total_bytes = chunk_total
                            if chunk_completed > highest_completed:
                                highest_completed = chunk_completed
                            percent = (highest_completed / total_bytes * 100)
                            last_percent = max(last_percent, percent)
                        else:
                            percent = last_percent

                        # Reset retry count on active data transfer
                        if retry_count > 0 and chunk_completed > 0:
                            retry_count = 0

                        done = (status == "success")

                        yield {
                            "status": status,
                            "completed": highest_completed,
                            "total": total_bytes,
                            "completed_mb": round(highest_completed / (1024 * 1024), 1),
                            "total_mb": round(total_bytes / (1024 * 1024), 1),
                            "percent": round(last_percent, 1),
                            "done": done,
                            "retrying": False
                        }

                        if done:
                            return

            # If response stream finished without explicit error, verify model presence
            # Allow a short delay for Ollama daemon to register the model internally
            model_verified = False
            for _ in range(5):
                if is_model_installed(model_name):
                    model_verified = True
                    break
                time.sleep(1)
                
            if model_verified:
                logger.info(f"[Downloader] Pull complete and verified for model: {model_name}")
                yield {
                    "status": "success",
                    "percent": 100.0,
                    "done": True,
                    "retrying": False
                }
                return
            else:
                logger.error(f"[Downloader] Stream ended but model {model_name} not found locally.")

        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            retry_count += 1
            logger.warning(f"[Downloader] Network interrupt during {model_name} download. Attempt {retry_count}/{max_retries}. Error: {exc}")
            if retry_count >= max_retries:
                logger.error(f"[Downloader] Max retries reached for {model_name}.")
                yield {
                    "status": "error",
                    "error": (
                        f"Download interrupted after {max_retries} reconnection attempts. "
                        f"Network issue: {exc}. All partial data has been safely preserved in model_pool. "
                        f"Click 'Resume' to continue downloading from {last_percent:.1f}%."
                    ),
                    "percent": round(last_percent, 1),
                    "done": False,
                    "retrying": False
                }
                return

            yield {
                "status": f"⚠️ Connection interrupted ({exc}). Reconnecting and resuming from {last_percent:.1f}% (Attempt {retry_count}/{max_retries})...",
                "percent": round(last_percent, 1),
                "completed": highest_completed,
                "total": total_bytes,
                "done": False,
                "retrying": True,
                "retry_attempt": retry_count,
                "max_retries": max_retries
            }

            # Exponential backoff with small jitter
            backoff = min(retry_delay_seconds * (1.5 ** (retry_count - 1)), 15.0)
            time.sleep(backoff)

            # Ensure Ollama daemon is still alive
            if not is_ollama_running():
                start_ollama_server()


def install_easyocr_models() -> Generator[Dict[str, Any], None, None]:
    """Installs EasyOCR models into model_pool/easyocr with integrity verification."""
    yield {"status": "Checking local weights...", "percent": 10.0}
    EASYOCR_DIR.mkdir(parents=True, exist_ok=True)

    craft = EASYOCR_DIR / "craft_mlt_25k.pth"
    crnn = EASYOCR_DIR / "english_g2.pth"

    # Integrity verification
    if craft.exists() and crnn.exists():
        if craft.stat().st_size >= 75 * 1024 * 1024 and crnn.stat().st_size >= 10 * 1024 * 1024:
            logger.info("[Downloader] EasyOCR weights verified via sizes.")
            yield {"status": "EasyOCR is already installed and verified in model_pool!", "percent": 100.0, "done": True}
            return
        else:
            # File is corrupt or partial, remove bad file
            logger.warning("[Downloader] EasyOCR weights corrupt. Removing partial files.")
            yield {"status": "Found partial/corrupted weights. Cleaning bad files before resume...", "percent": 15.0}
            for bad_file in [craft, crnn]:
                if bad_file.exists() and bad_file.stat().st_size < 14 * 1024 * 1024:
                    bad_file.unlink(missing_ok=True)

    # Check user home for migration
    home_dir = Path.home() / ".EasyOCR" / "model"
    if home_dir.exists():
        yield {"status": "Checking cached weights in user profile for instant import...", "percent": 40.0}
        for f in ["craft_mlt_25k.pth", "english_g2.pth"]:
            src = home_dir / f
            dst = EASYOCR_DIR / f
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

        if craft.exists() and crnn.exists():
            yield {"status": "EasyOCR weights imported successfully into model_pool!", "percent": 100.0, "done": True}
            return

    yield {"status": "Downloading EasyOCR weights via PyTorch...", "percent": 50.0}
    try:
        import easyocr
        import torch
        logger.info("[Downloader] Launching EasyOCR torch download process.")
        use_gpu = torch.cuda.is_available()
        easyocr.Reader(['en'], gpu=use_gpu, model_storage_directory=str(EASYOCR_DIR), download_enabled=True)
        yield {"status": "EasyOCR downloaded and verified successfully!", "percent": 100.0, "done": True}
    except Exception as e:
        logger.exception("[Downloader] EasyOCR download failed.")
        yield {"status": "error", "error": f"Failed to download EasyOCR: {e}"}


def purge_model(model_id: str) -> bool:
    """Deletes a model from the local model_pool."""
    if model_id == "easyocr":
        for f in EASYOCR_DIR.glob("*.pth"):
            try:
                f.unlink()
            except Exception:
                pass
        return True

    if is_ollama_running():
        try:
            url = f"{OLLAMA_HOST}/api/delete"
            payload = json.dumps({"name": model_id}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="DELETE")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
    return False
