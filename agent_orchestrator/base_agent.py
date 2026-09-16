"""
agent_orchestrator/base_agent.py
Sovereign Base Agent & Local Ollama Interface.
Provides unified inference capabilities across specialized offline models
(DeepSeek-R1, Qwen2.5-Coder, Moondream, Llama 3.2).
Strictly enforces fail-fast error handling: raises explicit OllamaOfflineException
on daemon or connection failure rather than fabricating pseudo-heuristics.
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import OLLAMA_HOST, logger


class OllamaOfflineException(Exception):
    """Raised when the local Ollama inference service is offline or unreachable."""
    pass


def check_ollama_status(host: Optional[str] = None) -> bool:
    """
    Checks if local Ollama daemon is active and responding.
    Uses urllib to avoid external dependencies.
    """
    import urllib.request
    target_host = host or OLLAMA_HOST
    url = f"{target_host.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def call_ollama(
    model: str,
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    timeout_seconds: float = 60.0
) -> str:
    """
    Calls local Ollama chat API.
    Raises OllamaOfflineException immediately if daemon is unreachable.
    """
    import urllib.request
    import urllib.error
    import json

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    payload = {
        "model": model,
        "messages": full_messages,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Low temperature for deterministic engineering reasoning
            "num_predict": 350,   # Ensure sufficient tokens for thought + output
        }
    }

    url = f"{OLLAMA_HOST.rstrip('/')}/api/chat"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            if response.status != 200:
                raise OllamaOfflineException(
                    f"Ollama returned HTTP error status {response.status}: {response.read().decode('utf-8')}"
                )
            result = json.loads(response.read().decode("utf-8"))
            content = result.get("message", {}).get("content", "").strip()
            # Clean thinking tags from DeepSeek-R1 responses
            if "</think>" in content:
                cleaned = content.split("</think>", 1)[1].strip()
                if not cleaned:
                    # Model reached </think> at token boundary; use thought synthesis
                    cleaned = content.replace("<think>", "").replace("</think>", "").strip()
            else:
                cleaned = content.replace("<think>", "").replace("</think>", "").strip()
            return cleaned if cleaned else content.strip()
    except urllib.error.URLError as e:
        logger.error(f"[BaseAgent] Ollama connection failure on {url}: {e.reason}")
        raise OllamaOfflineException(
            f"Ollama daemon at {OLLAMA_HOST} is offline or unreachable ({e.reason}). "
            f"Run 'ollama serve' to initialize local offline inference."
        ) from e
    except Exception as e:
        logger.error(f"[BaseAgent] Unexpected error calling Ollama model {model}: {e}")
        raise OllamaOfflineException(f"Ollama invocation failure: {str(e)}") from e
