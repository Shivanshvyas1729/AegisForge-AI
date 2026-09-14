"""
Layer 3: Dynamic Model Router & Serving Layer
Evaluates incoming task tokens/modality and routes to the most efficient local model:
- Coding & Automation -> Qwen2.5-Coder
- Deep Reasoning & Approvals -> DeepSeek-R1
- Visual Layout / Schematics -> Moondream / EasyOCR
- Fast Text & Summaries -> Llama-3.2
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import ollama

# Ensure project root is on sys.path so config is importable regardless of current directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import MODEL_REGISTRY, OLLAMA_MODELS_DIR, OLLAMA_HOST

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Heuristic keywords for fast task classification
CODING_KEYWORDS = [
    "python", "script", "code", "sql", "modbus", "scada", "crc", "parser",
    "function", "bug", "algorithm", "database", "query", "syntax", "program",
    "write code", "implement", "calculate in python", "python script", "def "
]
REASONING_KEYWORDS = [
    "asme", "api 510", "api 570", "t_min", "thickness", "corrosion", "approval note",
    "nfa", "cvc", "dop", "compliance", "calculate", "prove", "justification", "mawp"
]
VISION_KEYWORDS = [
    "p&id", "drawing", "schematic", "isometric", "blueprint", "diagram",
    "tag", "valve", "instrument bubble", "ocr", "scan", "image"
]


class SovereignModelRouter:
    def __init__(self, registry: Optional[Dict[str, str]] = None):
        self.registry = registry or MODEL_REGISTRY

    def classify_task(self, prompt: str, has_image: bool = False) -> str:
        """Classifies the task category based on input prompt and modality."""
        if has_image:
            return "vision"

        prompt_lower = prompt.lower()

        # Check for coding keywords (e.g. python, script, code, function)
        if any(kw in prompt_lower for kw in CODING_KEYWORDS):
            return "coding"

        # Check for reasoning / regulatory keywords
        if any(kw in prompt_lower for kw in REASONING_KEYWORDS):
            return "reasoning"

        # Check for vision/drawing text prompts
        if any(kw in prompt_lower for kw in VISION_KEYWORDS):
            return "vision"

        return "general"

    def get_model(self, task_type: str) -> str:
        return self.registry.get(task_type, self.registry["general"])

    def route_and_execute(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        override_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Routes the prompt to the appropriate model and executes inference locally.
        """
        task_type = self.classify_task(prompt, has_image=bool(image_path))
        target_model = override_model or self.get_model(task_type)

        print(f"[Router] Detected Category: '{task_type.upper()}' -> Assigned Model: '{target_model}'")

        messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
        if image_path and os.path.exists(image_path):
            messages[0]["images"] = [image_path]

        try:
            response = ollama.chat(
                model=target_model,
                messages=messages,
            )
            return {
                "success": True,
                "task_type": task_type,
                "model_used": target_model,
                "response": response["message"]["content"],
            }
        except Exception as e:
            return {
                "success": False,
                "task_type": task_type,
                "model_used": target_model,
                "error": str(e),
            }


class LocalModelHandler:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def invoke(self, prompt: str):
        try:
            import ollama
            res = ollama.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            content = res["message"]["content"]
        except Exception as e:
            content = f"[{self.model_name}] Local model response for: '{prompt}' (Ollama notice: {e})"

        class ResponseWrapper:
            def __init__(self, text):
                self.content = text
        return ResponseWrapper(content)



if __name__ == "__main__":
    router = SovereignModelRouter()
    test_queries = [
        "Write a Python function to compute CRC-16 Modbus checksum.",
        "Check ASME Section VIII Div 1 allowable stress for SA-516 Grade 70 plate.",
        "Summarize the executive takeaways of the Q3 refinery deck in 3 bullet points.",
    ]

    print("=== Testing Sovereign Dynamic Model Router ===\n")
    for query in test_queries:
        print(f"Query: {query}")
        result = router.route_and_execute(query)
        print(f"Status: {'SUCCESS' if result['success'] else 'FAILED'}")
        if result['success']:
            snippet = result['response'][:150].replace('\n', ' ')
            print(f"Sample Output: {snippet}...\n")
        else:
            print(f"Error: {result.get('error')}\n")
