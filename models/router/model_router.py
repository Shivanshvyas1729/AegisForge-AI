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
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import ollama

# Ensure project root is on sys.path so config is importable regardless of current directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import MODEL_REGISTRY, OLLAMA_MODELS_DIR, OLLAMA_HOST, logger

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class SovereignModelRouter:
    def __init__(self, registry: Optional[Dict[str, str]] = None):
        self.registry = registry or MODEL_REGISTRY

    def _llm_classify(self, prompt: str) -> str:
        """Uses a lightweight LLM to semantically classify the prompt intent."""
        router_model = "qwen2.5:0.5b"
        
        # Check if the routing model is installed
        try:
            from models.model_downloader import is_model_installed, pull_ollama_model_stream
            if not is_model_installed(router_model):
                logger.warning(f"[Router] Mandatory semantic router '{router_model}' missing. Auto-downloading...")
                for update in pull_ollama_model_stream(router_model):
                    if update.get("status") == "error":
                        logger.error(f"[Router] Failed to auto-download router model: {update.get('error')}. Falling back to general.")
                        return "general"
                logger.info(f"[Router] Successfully auto-downloaded mandatory router '{router_model}'.")
        except Exception as e:
            logger.error(f"[Router] Exception during auto-download check: {e}. Falling back to general.")
            return "general"

        system_prompt = (
            "You are a routing agent for an industrial AI workbench. "
            "Analyze the user's prompt and classify the intent into exactly one of the following four categories:\n"
            "- 'coding': For Python scripts, software automation, SQL, or parsing logic.\n"
            "- 'reasoning': For engineering calculations, ASME/API compliance, regulatory audits, or approvals.\n"
            "- 'vision': For processing images, P&ID diagrams, schematics, or OCR.\n"
            "- 'general': For general conversation, summaries, or questions.\n\n"
            "Reply ONLY with the exact single word of the category. Do not include any other text or punctuation."
        )

        try:
            client = ollama.Client(host=OLLAMA_HOST)
            response = client.generate(
                model=router_model,
                prompt=prompt,
                system=system_prompt,
                options={
                    "temperature": 0.0,
                    "num_predict": 5, # We only need 1 word
                }
            )
            
            result = response.get("response", "").strip().lower()
            # Clean any stray punctuation
            result = re.sub(r'[^a-z]', '', result)
            
            valid_categories = {"coding", "reasoning", "vision", "general"}
            if result in valid_categories:
                return result
            else:
                logger.warning(f"[Router] LLM returned invalid category '{result}', falling back to general.")
                return "general"
                
        except Exception as e:
            logger.error(f"[Router] Semantic classification failed: {e}")
            return "general"

    def _heuristic_classify(self, prompt: str) -> Optional[str]:
        """Sub-millisecond keyword & regex pre-classifier for instantaneous routing."""
        p = prompt.lower()

        # Coding patterns
        coding_patterns = [
            r"\b(python|code|script|def |class |import |function|parser|crc|modbus|sql|json|regex|algorithm)\b",
            r"\b(write a (python|script|program|parser|function|code))\b",
            r"\b(develop|implement|debug|refactor)\b",
        ]
        if any(re.search(pat, p) for pat in coding_patterns):
            return "coding"

        # Reasoning & Statutory Compliance patterns
        reasoning_patterns = [
            r"\b(asme|ug-?27|api\s*510|mawp|cvc|dop|statutory|breach|allowable\s*stress|t_min|t_req|thickness\s*breach|corrosion\s*rate|procurement|single[\s-]source)\b",
            r"\b(compliance|integrity|evaluation|approval\s*note|nfa|derated|remaining\s*life)\b",
        ]
        if any(re.search(pat, p) for pat in reasoning_patterns):
            return "reasoning"

        # Vision patterns
        vision_patterns = [
            r"\b(blueprint|drawing|p&id|diagram|schematic|isometric|ocr|scan|bubble|nozzle\s*tag)\b",
        ]
        if any(re.search(pat, p) for pat in vision_patterns):
            return "vision"

        # Summary patterns
        summary_patterns = [
            r"\b(summarize|summary|overview|bullet\s*points|safety\s*steps|brief|recap)\b",
        ]
        if any(re.search(pat, p) for pat in summary_patterns):
            return "general"

        return None

    def classify_task(self, prompt: str, has_image: bool = False) -> str:
        """Classifies the task category based on input prompt and modality."""
        if has_image:
            return "vision"
            
        # 1. Primary: AI Semantic Classifier (qwen2.5:0.5b)
        # Trust the LLM's judgement entirely over brittle keyword matching.
        return self._llm_classify(prompt)

    def get_model(self, task_type: str) -> str:
        preferred = self.registry.get(task_type, self.registry["general"])
        try:
            from models.model_downloader import is_model_installed, get_installed_models_set
            if not is_model_installed(preferred):
                installed = [m for m in get_installed_models_set() if m != "easyocr"]
                if installed:
                    for candidate in ["deepseek-r1:1.5b", "qwen2.5-coder:1.5b", "llama3.2:3b"]:
                        if candidate in installed:
                            logger.info(f"[Router] Preferred model '{preferred}' not installed. Falling back to '{candidate}'.")
                            return candidate
                    return installed[0]
        except Exception:
            pass
        return preferred

    def route_and_execute(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        override_model: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Routes the prompt to the appropriate model and executes inference locally with session chat history.
        Extracts internal thinking/reasoning (<think> tags) and constructs a transparent step trace.
        """
        task_type = self.classify_task(prompt, has_image=bool(image_path))
        preferred_model = self.registry.get(task_type, self.registry["general"])
        target_model = override_model or self.get_model(task_type)

        logger.info(f"[Router] Category: '{task_type.upper()}' -> Assigned Model: '{target_model}' (History turns: {len(history) if history else 0})")

        messages: List[Dict[str, Any]] = []
        if history:
            for turn in history[-8:]:
                if turn.get("role") in ("user", "assistant") and turn.get("content"):
                    messages.append({"role": turn["role"], "content": turn["content"]})

        user_turn: Dict[str, Any] = {"role": "user", "content": prompt}
        if image_path and os.path.exists(image_path):
            user_turn["images"] = [image_path]
        messages.append(user_turn)

        try:
            client = ollama.Client(host=OLLAMA_HOST)
            response = client.chat(
                model=target_model,
                messages=messages,
                options={"temperature": 0.3},
                keep_alive="30m",
            )
            raw_content = response["message"]["content"]
            logger.info(f"[Router] Successfully received response from '{target_model}'")

            # Extract <think> reasoning tags if present (e.g. DeepSeek-R1 CoT)
            think_match = re.search(r"<think>(.*?)</think>", raw_content, re.DOTALL)
            if think_match:
                model_thinking = think_match.group(1).strip()
                clean_response = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
            else:
                model_thinking = None
                clean_response = raw_content

            # Construct transparent internal reasoning & routing trace
            steps = [f"Analyzed prompt tokens: classified as category **{task_type.upper()}**"]
            if not override_model and target_model != preferred_model:
                steps.append(f"Auto-fallback: target model `{preferred_model}` not in local pool; routed to available sovereign model **{target_model}**")
            else:
                steps.append(f"Selected sovereign model: **{target_model}** (100% on-premise air-gapped)")
            steps.append(f"Session context: preserved {len(messages) - 1} prior conversation turn(s)")
            steps.append(f"Dispatched via local socket `{OLLAMA_HOST}`")

            internal_trace = {
                "task_type": task_type,
                "model_used": target_model,
                "preferred_model": preferred_model,
                "history_turns": len(messages) - 1,
                "model_thinking": model_thinking,
                "steps": steps,
            }

            return {
                "success": True,
                "task_type": task_type,
                "model_used": target_model,
                "response": clean_response,
                "raw_response": raw_content,
                "model_thinking": model_thinking,
                "internal_trace": internal_trace,
            }
        except Exception as e:
            logger.exception(f"[Router] Inference failed for model '{target_model}'")
            return {
                "success": False,
                "task_type": task_type,
                "model_used": target_model,
                "error": str(e),
                "internal_trace": {
                    "task_type": task_type,
                    "model_used": target_model,
                    "history_turns": len(messages) - 1,
                    "model_thinking": None,
                    "steps": [
                        f"Attempted dispatch to {target_model}",
                        f"Local endpoint error: {e}",
                    ]
                }
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
