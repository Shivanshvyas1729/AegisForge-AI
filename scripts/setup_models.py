"""
AegisForge-AI: In-Project Self-Contained Model Setup & Health Check
Downloads and verifies all models inside <PROJECT_ROOT>/model_pool/.
Ensures zero pollution of host directories and dynamic paths for any user/machine.
"""

import os
import sys
import shutil
from pathlib import Path
import urllib.request
import json

# Add project root to sys.path dynamically
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    MODEL_POOL_DIR,
    EASYOCR_DIR,
    OLLAMA_MODELS_DIR,
    SAMPLE_DATA_DIR,
    MODEL_REGISTRY,
    OLLAMA_HOST,
    get_disk_free_gb,
)


def print_banner(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def check_safety_preflight(min_gb_required: float = 8.0) -> bool:
    """Pre-flight safety checks: disk space and path permissions."""
    print_banner("1. Pre-Flight Safety Checks")
    free_gb = get_disk_free_gb()
    print(f"[*] Checking disk space on drive hosting project...")
    print(f"    Available: {free_gb:.2f} GB | Required: {min_gb_required:.2f} GB")

    if free_gb < min_gb_required:
        print(f"[!] WARNING: Free space ({free_gb:.2f} GB) is below recommended {min_gb_required:.2f} GB.")
        print(f"    Consider cleaning up disk space before downloading full LLM suite.")
        return False
    else:
        print(f"[+] Disk space check PASSED.")

    # Check write permissions in model_pool
    try:
        test_file = MODEL_POOL_DIR / ".perm_check.tmp"
        test_file.write_text("ok")
        test_file.unlink()
        print(f"[+] Directory write permission in '{MODEL_POOL_DIR}' verified.")
    except Exception as e:
        print(f"[!] ERROR: Cannot write to '{MODEL_POOL_DIR}': {e}")
        return False

    return True


def setup_easyocr_model() -> bool:
    """Installs and validates EasyOCR weights strictly inside model_pool/easyocr."""
    print_banner("2. Setting up Vision Engine (EasyOCR) in model_pool")
    EASYOCR_DIR.mkdir(parents=True, exist_ok=True)

    # Check if weights already exist in model_pool/easyocr
    craft_file = EASYOCR_DIR / "craft_mlt_25k.pth"
    crnn_file = EASYOCR_DIR / "english_g2.pth"

    # Migration helper: if weights exist in ~/.EasyOCR, copy to project to save bandwidth
    user_home_easyocr = Path.home() / ".EasyOCR" / "model"
    if not (craft_file.exists() and crnn_file.exists()):
        if user_home_easyocr.exists():
            print(f"[*] Found cached weights in user profile. Migrating to project model_pool...")
            for f in ["craft_mlt_25k.pth", "english_g2.pth"]:
                src = user_home_easyocr / f
                dst = EASYOCR_DIR / f
                if src.exists() and not dst.exists():
                    print(f"    Copying {f} -> {EASYOCR_DIR}")
                    shutil.copy2(src, dst)

    try:
        import easyocr
        import torch

        use_gpu = torch.cuda.is_available()
        device_str = "GPU (CUDA)" if use_gpu else "CPU"
        print(f"[*] Initializing EasyOCR Reader on {device_str}...")
        print(f"    Model Storage Directory: {EASYOCR_DIR}")

        reader = easyocr.Reader(
            ["en"],
            gpu=use_gpu,
            model_storage_directory=str(EASYOCR_DIR),
            download_enabled=True,
        )

        # Quick validation on sample drawing
        sample_img = SAMPLE_DATA_DIR / "05_scanned_drawings_pid" / "pump_station_isometric_drawing.png"
        if sample_img.exists():
            print(f"[*] Validating OCR inference on sample drawing: {sample_img.name}...")
            results = reader.readtext(str(sample_img))
            print(f"[+] EasyOCR Test PASSED: Detected {len(results)} text regions.")
        else:
            print(f"[+] EasyOCR Reader initialized successfully (sample image not found for dry run).")

        return True

    except Exception as e:
        print(f"[!] EasyOCR Setup failed: {e}")
        return False


def check_ollama_service() -> bool:
    """Checks if local Ollama daemon is reachable."""
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def setup_ollama_models() -> bool:
    """Checks and pulls required Ollama models into model_pool/ollama."""
    print_banner("3. Setting up Reasoning, Coding & VLM Models (Ollama)")
    OLLAMA_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["OLLAMA_MODELS"] = str(OLLAMA_MODELS_DIR)

    print(f"[*] Target Ollama Model Storage: {OLLAMA_MODELS_DIR}")
    print(f"[*] Checking Ollama service at {OLLAMA_HOST}...")

    is_running = check_ollama_service()
    if not is_running:
        print(f"[!] Ollama daemon is not currently responding at {OLLAMA_HOST}.")
        print(f"    To run Ollama with models isolated in this project:")
        print(f"    1. Run: scripts\\run_ollama_local.bat")
        print(f"       OR set $env:OLLAMA_MODELS = '{OLLAMA_MODELS_DIR}' and run 'ollama serve'")
        print(f"    2. Re-run this script to pull the models.")
        return False

    print(f"[+] Ollama service is ONLINE.")
    import ollama

    models_to_pull = list(MODEL_REGISTRY.values())
    print(f"[*] Required models in registry: {models_to_pull}")

    for model_name in models_to_pull:
        print(f"\n[*] Checking / pulling model: '{model_name}' into model_pool...")
        try:
            # Check if model already exists locally
            current_tags = ollama.list().get("models", [])
            existing_names = [m.get("name") or m.get("model") for m in current_tags]
            
            # Check match (e.g. 'deepseek-r1:1.5b' or 'deepseek-r1:1.5b-latest')
            matched = any(model_name in name for name in existing_names if name)
            if matched:
                print(f"    [+] '{model_name}' already installed and ready.")
                continue

            print(f"    Downloading '{model_name}'... (this may take a few minutes)")
            ollama.pull(model_name)
            print(f"    [+] Successfully downloaded '{model_name}'.")

        except Exception as e:
            print(f"    [!] Failed to pull '{model_name}': {e}")

    return True


def print_status_summary():
    print_banner("4. Final In-Project Model Pool Status")
    print(f"{'Component':<25} {'Path / Reference':<45} {'Status'}")
    print("-" * 80)

    # EasyOCR weights
    craft = EASYOCR_DIR / "craft_mlt_25k.pth"
    crnn = EASYOCR_DIR / "english_g2.pth"
    ocr_status = "INSTALLED (model_pool)" if (craft.exists() and crnn.exists()) else "MISSING"
    print(f"{'EasyOCR Weights':<25} {str(EASYOCR_DIR):<45} {ocr_status}")

    # Ollama directory
    ollama_status = "READY (model_pool)" if OLLAMA_MODELS_DIR.exists() else "MISSING"
    print(f"{'Ollama Models Dir':<25} {str(OLLAMA_MODELS_DIR):<45} {ollama_status}")

    # Ollama service
    svc_status = "ONLINE" if check_ollama_service() else "OFFLINE"
    print(f"{'Ollama Service':<25} {OLLAMA_HOST:<45} {svc_status}")
    print("-" * 80)
    print("\nTo safely uninstall models at any time, run: scripts\\clean_models.bat")
    print("To completely wipe environment and models, run: scripts\\uninstall_all.bat\n")


if __name__ == "__main__":
    check_safety_preflight(min_gb_required=6.0)
    setup_easyocr_model()
    setup_ollama_models()
    print_status_summary()
