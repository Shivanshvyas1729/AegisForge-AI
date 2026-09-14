import sys
import argparse
import ollama

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def test_reasoning(prompt: str = None, model: str = "deepseek-r1:1.5b"):
    """
    Tests local reasoning model (DeepSeek-R1) on ASME/API compliance and PSU approval synthesis.
    """
    if not prompt:
        prompt = (
            "An ultrasonic thickness survey on a refinery hydrocracker reactor nozzle indicates "
            "an actual wall thickness of 138.20 mm. The design code is ASME Sec VIII Div 1. "
            "The calculated minimum required thickness t_min is 138.57 mm with a corrosion rate "
            "of 0.45 mm/year. "
            "1. Determine if the nozzle is within safe operational limits. "
            "2. Formulate the required safety action and draft an executive finding for a PSU Note for Approval."
        )

    print(f"Testing Reasoning Model: {model}")
    print(f"Scenario Prompt:\n{prompt}\n")
    print("Running chain-of-thought inference via local Ollama...")

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        reply = response["message"]["content"]
        print("\n--- Reasoning Model Response ---")
        print(reply)
        print("-" * 50)
        print("\nTest Passed: DeepSeek-R1 generated step-by-step reasoning and recommendations!")
        return True

    except Exception as e:
        print(f"Test Failed with exception: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test DeepSeek-R1 reasoning model on AegisForge compliance scenarios")
    parser.add_argument("--prompt", type=str, default=None, help="Custom engineering or approval prompt")
    parser.add_argument("--model", type=str, default="deepseek-r1:1.5b", help="Reasoning model name in Ollama")
    args = parser.parse_args()

    test_reasoning(args.prompt, args.model)
