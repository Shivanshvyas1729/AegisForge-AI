"""
Config package initialization for AegisForge-AI.
Exposes settings and logging configurations.
"""

from config.settings import (
    PROJECT_ROOT,
    DATA_DIR,
    LOGS_DIR,
    LOG_FILE,
    logger,
    setup_logging,
    MODEL_POOL_DIR,
    EASYOCR_DIR,
    OLLAMA_MODELS_DIR,
    UPLOADS_DIR,
    OUTPUT_DIR,
    SAMPLE_DATA_DIR,
    OLLAMA_HOST,
    MODEL_REGISTRY,
    get_disk_free_gb,
)

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "LOGS_DIR",
    "LOG_FILE",
    "logger",
    "setup_logging",
    "MODEL_POOL_DIR",
    "EASYOCR_DIR",
    "OLLAMA_MODELS_DIR",
    "UPLOADS_DIR",
    "OUTPUT_DIR",
    "SAMPLE_DATA_DIR",
    "OLLAMA_HOST",
    "MODEL_REGISTRY",
    "get_disk_free_gb",
]
