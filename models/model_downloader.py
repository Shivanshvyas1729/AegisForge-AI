"""
AegisForge-AI: Model Download, Health & Lifecycle Manager
Provides streaming download progress, background server management,
and 1-click installation/uninstallation for the Streamlit UI.
"""

import os
import sys
import shutil
import subprocess
import threading
import json
import urllib.request
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
        with urllib.request.urlopen(req, timeout=1.5) as resp:
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
        import time
        time.sleep(0.5)
        if is_ollama_running():
            return True

    return False


def get_installed_ollama_models() -> list:
    """Fetches the list of currently installed model names from local Ollama."""
    if not is_ollama_running():
        return []
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode())
            return [m.get("name") or m.get("model") for m in data.get("models", [])]
    except Exception:
        return []


def is_model_installed(model_id: str) -> bool:
    """Checks if a model is installed in the project's model_pool."""
    if model_id == "easyocr":
        craft = EASYOCR_DIR / "craft_mlt_25k.pth"
        crnn = EASYOCR_DIR / "english_g2.pth"
        return craft.exists() and crnn.exists()

    installed = get_installed_ollama_models()
    return any(model_id in name for name in installed if name)


def pull_ollama_model_stream(model_name: str) -> Generator[Dict[str, Any], None, None]:
    """
    Streams the download progress of an Ollama model.
    Yields dicts with {'status': str, 'completed': int, 'total': int, 'percent': float}.
    """
    if not is_ollama_running():
        started = start_ollama_server()
        if not started:
            yield {"status": "error", "error": "Ollama server is not running and could not be started automatically."}
            return

    url = f"{OLLAMA_HOST}/api/pull"
    payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            for line in response:
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    status = chunk.get("status", "")
                    total = chunk.get("total", 0)
                    completed = chunk.get("completed", 0)
                    percent = (completed / total * 100) if total > 0 else 0.0

                    yield {
                        "status": status,
                        "completed": completed,
                        "total": total,
                        "percent": round(percent, 1),
                        "done": status == "success"
                    }
    except Exception as e:
        yield {"status": "error", "error": str(e)}


def install_easyocr_models() -> Generator[Dict[str, Any], None, None]:
    """Installs EasyOCR models into model_pool/easyocr with progress status."""
    yield {"status": "Checking local weights...", "percent": 10.0}
    EASYOCR_DIR.mkdir(parents=True, exist_ok=True)

    craft = EASYOCR_DIR / "craft_mlt_25k.pth"
    crnn = EASYOCR_DIR / "english_g2.pth"

    if craft.exists() and crnn.exists():
        yield {"status": "EasyOCR is already installed in model_pool!", "percent": 100.0, "done": True}
        return

    # Check user home for migration
    home_dir = Path.home() / ".EasyOCR" / "model"
    if home_dir.exists():
        yield {"status": "Migrating cached weights to model_pool...", "percent": 40.0}
        for f in ["craft_mlt_25k.pth", "english_g2.pth"]:
            src = home_dir / f
            dst = EASYOCR_DIR / f
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
        yield {"status": "EasyOCR weights migrated successfully!", "percent": 100.0, "done": True}
        return

    yield {"status": "Downloading EasyOCR weights via PyTorch...", "percent": 50.0}
    try:
        import easyocr
        easyocr.Reader(['en'], gpu=False, model_storage_directory=str(EASYOCR_DIR), download_enabled=True)
        yield {"status": "EasyOCR downloaded and verified successfully!", "percent": 100.0, "done": True}
    except Exception as e:
        yield {"status": "error", "error": str(e)}


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
