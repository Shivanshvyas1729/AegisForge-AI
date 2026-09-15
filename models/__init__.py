"""
Models package initialization for AegisForge-AI.
"""
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
except ImportError:
    from models.model_downloader import get_installed_ollama_models
    def get_installed_models_set() -> set:
        models = set(get_installed_ollama_models())
        if is_model_installed("easyocr"):
            models.add("easyocr")
        return models

__all__ = [
    "MODEL_METADATA",
    "is_ollama_running",
    "find_ollama_executable",
    "start_ollama_server",
    "is_model_installed",
    "get_installed_models_set",
    "pull_ollama_model_stream",
    "install_easyocr_models",
    "purge_model",
]

