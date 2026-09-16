"""
Centralized Configuration & Dynamic Path Anchoring for AegisForge-AI.
Automatically computes paths relative to the project root, ensuring that
any user or clone location works out-of-the-box without hardcoded paths.
"""

import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict

# Dynamic Project Root: parent directory of 'config/'
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data & Output Directories (declare early for logs)
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"
LOG_FILE = LOGS_DIR / "aegisforge.log"

# Ensure log directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging():
    """Configures project-wide logging with file and console handlers."""
    logger = logging.getLogger("aegisforge")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

# Initialize the root logger immediately
logger = setup_logging()

# Self-Contained Model Pool Storage
MODEL_POOL_DIR = PROJECT_ROOT / "model_pool"
EASYOCR_DIR = MODEL_POOL_DIR / "easyocr"
OLLAMA_MODELS_DIR = MODEL_POOL_DIR / "ollama"

# Data & Output Directories
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
VECTOR_STORAGE_DIR = DATA_DIR / "vector_storage"
QDRANT_STORAGE_DIR = VECTOR_STORAGE_DIR / "qdrant_db"
EXTRACTED_IMAGES_DIR = VECTOR_STORAGE_DIR / "extracted_images"

# Ensure all essential internal directories exist
for directory in [
    MODEL_POOL_DIR,
    EASYOCR_DIR,
    OLLAMA_MODELS_DIR,
    UPLOADS_DIR,
    OUTPUT_DIR,
    VECTOR_STORAGE_DIR,
    QDRANT_STORAGE_DIR,
    EXTRACTED_IMAGES_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# Enforce project-contained model locations via environment variables
os.environ.setdefault("OLLAMA_MODELS", str(OLLAMA_MODELS_DIR))
os.environ.setdefault("EASYOCR_MODULE_PATH", str(EASYOCR_DIR))

# Ollama Endpoint Configuration (Always use 127.0.0.1 to avoid Windows IPv6 localhost connection delays)
_raw_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_HOST = _raw_host.replace("://localhost", "://127.0.0.1")

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
