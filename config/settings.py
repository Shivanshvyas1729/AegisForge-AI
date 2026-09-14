"""
Centralized Configuration & Dynamic Path Anchoring for AegisForge-AI.
Automatically computes paths relative to the project root, ensuring that
any user or clone location works out-of-the-box without hardcoded paths.
"""

import os
import shutil
from pathlib import Path
from typing import Dict

# Dynamic Project Root: parent directory of 'config/'
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Self-Contained Model Pool Storage
MODEL_POOL_DIR = PROJECT_ROOT / "model_pool"
EASYOCR_DIR = MODEL_POOL_DIR / "easyocr"
OLLAMA_MODELS_DIR = MODEL_POOL_DIR / "ollama"

# Data & Output Directories
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"

# Ensure all essential internal directories exist
for directory in [MODEL_POOL_DIR, EASYOCR_DIR, OLLAMA_MODELS_DIR, UPLOADS_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Enforce project-contained model locations via environment variables
os.environ.setdefault("OLLAMA_MODELS", str(OLLAMA_MODELS_DIR))
os.environ.setdefault("EASYOCR_MODULE_PATH", str(EASYOCR_DIR))

# Ollama Endpoint Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Model Registry designations (quantized for edge / 4GB VRAM / CPU execution)
MODEL_REGISTRY: Dict[str, str] = {
    "coding": "qwen2.5-coder:1.5b",
    "reasoning": "deepseek-r1:1.5b",
    "vision": "moondream",
    "general": "llama3.2:3b",
}


def get_disk_free_gb() -> float:
    """Returns the free disk space on the drive hosting the project in Gigabytes."""
    total, used, free = shutil.disk_usage(PROJECT_ROOT)
    return free / (1024 ** 3)


if __name__ == "__main__":
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Model Pool:   {MODEL_POOL_DIR}")
    print(f"EasyOCR Dir:  {EASYOCR_DIR}")
    print(f"Ollama Dir:   {OLLAMA_MODELS_DIR}")
    print(f"Free Disk:    {get_disk_free_gb():.2f} GB available")
