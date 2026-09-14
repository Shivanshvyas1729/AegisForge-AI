import os
import sys
from pathlib import Path
import argparse
import ollama

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config.settings

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def test_vision_vlm(image_path: str, prompt: str = None, model: str = "moondream"):
    """
    Tests local multimodal Vision-Language Model on an engineering drawing or inspection sheet.
    """
    print(f"Testing Vision Model ({model}) on: {image_path}")
    if not os.path.exists(image_path):
        print(f"Error: File '{image_path}' not found.")
        return False

    if not prompt:
        prompt = (
            "Analyze this industrial engineering drawing or document. "
            "Identify and list: 1) The main equipment or process units, "
            "2) Any visible instrument/valve tags, "
            "3) Key engineering annotations or safety notes."
        )

    print(f"Prompt: {prompt}\n")
    print("Running vision inference via local Ollama...")

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_path],
                }
            ],
        )

        reply = response["message"]["content"]
        print("\n--- Vision Model Response ---")
        print(reply)
        print("-" * 50)
        print("\nTest Passed: Vision model processed the image and returned analysis!")
        return True

    except Exception as e:
        print(f"Test Failed with exception: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test local Vision-Language Model on AegisForge images")
    parser.add_argument("--image", type=str, required=True, help="Path to image file (.png, .jpg)")
    parser.add_argument("--prompt", type=str, default=None, help="Custom prompt for the vision model")
    parser.add_argument("--model", type=str, default="moondream", help="Ollama vision model name")
    args = parser.parse_args()

    test_vision_vlm(args.image, args.prompt, args.model)
