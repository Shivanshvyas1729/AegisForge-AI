import sys
import os

sys.path.append(os.path.expanduser("~/Library/Python/3.9/lib/python/site-packages"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_orchestrator import build_graph
from models.router.model_router import SovereignModelRouter, LocalModelHandler


def test_sequential_pipeline():
    print("=" * 60)
    print("      SEQUENTIAL PIPELINE TEST (ALL 4 MODELS IN SERIES)")
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

    prompt = "Run full audit pipeline: inspect CDU drawing, generate parser script, calculate ASME compliance, and output executive summary"
    print(f"INPUT PROMPT: '{prompt}'")

    result = app.invoke({
        "user_prompt": prompt,
        "input_type": ["image", "text"],
        "files": ["sample_data/05_scanned_drawings_pid/cdu_feed_preheat_train_pid.svg"],
    })

    print(f"\nROUTER DECISION: {result.get('route')}")
    print(f"\n[STEP 1 - Multimodal Output]:\n{result.get('multimodal_output')}")
    print(f"\n[STEP 2 - Coding Output]:\n{result.get('coding_output')}")
    print(f"\n[STEP 3 - Reasoning Output]:\n{result.get('reasoning_output')}")
    print(f"\n[STEP 4 - Final Summary Output]:\n{result.get('summary_output')}")

    assert result.get("route") == "pipeline", f"Expected route 'pipeline', got {result.get('route')}"
    assert result.get("multimodal_output") is not None
    assert result.get("coding_output") is not None
    assert result.get("reasoning_output") is not None
    assert result.get("summary_output") is not None

    print("\n" + "=" * 60)
    print("   SEQUENTIAL PIPELINE PASSED THROUGH ALL 4 MODELS SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    test_sequential_pipeline()
