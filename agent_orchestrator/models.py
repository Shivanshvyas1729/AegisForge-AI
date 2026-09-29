"""
AegisForge-AI — LLM Model Registry
=====================================
Single source of truth for all model names used across the pipeline.
Import these constants everywhere (sidebar, telemetry, downloader) to
keep the UI and pipeline in sync. Fixes problems #17 and #12.
"""

import logging
import os
import warnings

warnings.filterwarnings('ignore')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

from langchain_ollama import ChatOllama

logger = logging.getLogger("AegisForge.Models")

# ============================================================================
# MODEL NAME CONSTANTS — configurable via environment variables
# ============================================================================
ROUTER_MODEL         = os.getenv("ROUTER_MODEL", "laya:421m")
SUPERVISOR_MODEL     = os.getenv("SUPERVISOR_MODEL", "llama3.1:8b")
CODER_MODEL          = os.getenv("CODER_MODEL", "qwen2.5-coder:7b")
REASONING_MODEL      = os.getenv("REASONING_MODEL", "llama3.1:8b")
VISION_MODEL         = os.getenv("VISION_MODEL", "llama3.2:3b")
REVIEWER_MODEL       = os.getenv("REVIEWER_MODEL", "llama3.1:8b")
CONVERSATIONAL_MODEL = os.getenv("CONVERSATIONAL_MODEL", "llama3.1:8b")

# Models that must be installed for the pipeline to function
REQUIRED_MODELS = [
    ROUTER_MODEL,
    SUPERVISOR_MODEL,
    CODER_MODEL,
    VISION_MODEL,
]

# VRAM Protection for 6GB GPUs: prevent concurrent model allocations and oversized context
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")
os.environ.setdefault("OLLAMA_MAX_LOADED_MODELS", "1")

# ============================================================================
# LLM INSTANCES (configured with bounded context to prevent VRAM stack overflows)
# Explicitly named so Langfuse and telemetry traces show the exact model & agent role
# ============================================================================
supervisor_llm     = ChatOllama(model=SUPERVISOR_MODEL,      temperature=0,   format="json", num_ctx=4096, name=f"{SUPERVISOR_MODEL} (Supervisor)").with_config({"run_name": f"{SUPERVISOR_MODEL} (Supervisor)"})
coder_llm          = ChatOllama(model=CODER_MODEL,           temperature=0,   num_ctx=4096,                 name=f"{CODER_MODEL} (Coder Agent)").with_config({"run_name": f"{CODER_MODEL} (Coder Agent)"})
reasoning_llm      = ChatOllama(model=REASONING_MODEL,       temperature=0,   num_ctx=4096,                 name=f"{REASONING_MODEL} (Reasoning Agent)").with_config({"run_name": f"{REASONING_MODEL} (Reasoning Agent)"})
vision_llm         = ChatOllama(model=VISION_MODEL,          temperature=0,   format="json", num_ctx=2048, name=f"{VISION_MODEL} (Vision Agent)").with_config({"run_name": f"{VISION_MODEL} (Vision Agent)"})
reviewer_llm       = ChatOllama(model=REVIEWER_MODEL,        temperature=0,   num_ctx=4096,                 name=f"{REVIEWER_MODEL} (Chief Reviewer)").with_config({"run_name": f"{REVIEWER_MODEL} (Chief Reviewer)"})
conversational_llm = ChatOllama(model=CONVERSATIONAL_MODEL,  temperature=0.3, num_ctx=2048,                 name=f"{CONVERSATIONAL_MODEL} (Direct Answer)").with_config({"run_name": f"{CONVERSATIONAL_MODEL} (Direct Answer)"})
router_llm         = ChatOllama(model=ROUTER_MODEL,          temperature=0,   format="json", num_ctx=2048, name=f"{ROUTER_MODEL} (Laya Router)").with_config({"run_name": f"{ROUTER_MODEL} (Laya Router)"})

# ============================================================================
# LANGFUSE INTEGRATION (optional)
# ============================================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler
    Langfuse().auth_check()   # Validate credentials at startup
    _handler = CallbackHandler()
    LANGFUSE_CONFIG = {"callbacks": [_handler]}
    logger.info("Langfuse tracking enabled successfully.")
except Exception as e:
    LANGFUSE_CONFIG = {}
    logger.warning(f"Langfuse not enabled. Tracing disabled: {e}")

# ============================================================================
# STARTUP HEALTH CHECK — warn early if required models are missing
# Fixes Problem #12: no startup warning when Laya is missing.
# ============================================================================
def check_model_availability() -> dict:
    """Check which required models are available in Ollama. Call once at startup."""
    results = {}
    try:
        import urllib.request, json as _json
        ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        req = urllib.request.Request(f"{ollama_host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = _json.loads(resp.read().decode())
            installed = {m.get("name", "") for m in data.get("models", [])}
        for model in REQUIRED_MODELS:
            available = any(model in name for name in installed)
            results[model] = available
            if not available:
                logger.warning(
                    f"⚠️  Required model '{model}' NOT found in Ollama. "
                    f"Run: ollama pull {model}"
                )
    except Exception as e:
        logger.warning(f"Could not check Ollama model availability: {e}")
    return results


# Run check at import (non-blocking — just logs warnings)
_model_status = check_model_availability()
