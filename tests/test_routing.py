import sys
import os

sys.path.append(os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_orchestrator import build_graph
from models.router.model_router import SovereignModelRouter, LocalModelHandler


def run_routing_test():
    print("=" * 60)
    print("      ROUTING VERIFICATION TEST (4 MODEL ROLES)")
    print("=" * 60)

    router_llm = SovereignModelRouter()
    coding_llm = LocalModelHandler("qwen2.5-coder:1.5b")
    reasoning_llm = LocalModelHandler("deepseek-r1:1.5b")
    summary_llm = LocalModelHandler("llama3.2:3b")
    multimodal_llm = LocalModelHandler("moondream")

    app = build_graph(
        router_llm=router_llm,
        coding_llm=coding_llm,
        reasoning_llm=reasoning_llm,
        summary_llm=summary_llm,
        multimodal_llm=multimodal_llm,
    )

    test_cases = [
        {
            "category": "CODING",
            "prompt": "Write Python code to sort a list of numbers",
            "expected_route": "coding",
            "expected_model": "qwen2.5-coder:1.5b",
            "input_type": ["text"],
            "files": [],
        },
        {
            "category": "REASONING",
            "prompt": "Explain why neural networks overfit and how ASME guidelines apply",
            "expected_route": "reasoning",
            "expected_model": "deepseek-r1:1.5b",
            "input_type": ["text"],
            "files": [],
        },
        {
            "category": "SUMMARY",
            "prompt": "Summarize this paragraph into key executive takeaways",
            "expected_route": "summary",
            "expected_model": "llama3.2:3b",
            "input_type": ["text"],
            "files": [],
        },
        {
            "category": "MULTIMODAL",
            "prompt": "Analyze this industrial drawing or blueprint image",
            "expected_route": "multimodal",
            "expected_model": "moondream",
            "input_type": ["image"],
            "files": ["sample_data/05_scanned_drawings_pid/cdu_feed_preheat_train_pid.svg"],
        },
    ]

    for idx, test in enumerate(test_cases, 1):
        print(f"\n--- TEST CASE {idx}: {test['category']} ---")
        print(f"INPUT: {test['prompt']}")

        result = app.invoke({
            "user_prompt": test["prompt"],
            "input_type": test["input_type"],
            "files": test["files"],
        })

        route = result.get("route")
        model_used = result.get("model_used")
        response = result.get("response")

        print(f"ROUTER DECISION: {route}")
        print(f"SELECTED MODEL: {model_used}")
        print(f"MODEL RESPONSE: {response}")

        assert route == test["expected_route"], f"Expected route {test['expected_route']}, got {route}"
        print(f"✓ Case {idx} ({test['category']}) Passed Successfully!")

    print("\n" + "=" * 60)
    print("   ALL 4 ROUTING TESTS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_routing_test()
