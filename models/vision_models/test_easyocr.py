import os
import sys
from pathlib import Path
import argparse
import easyocr
from PIL import Image

# Ensure project root is on sys.path so config is importable regardless of current directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import EASYOCR_DIR

# Fix Windows terminal encoding issue with EasyOCR's Unicode progress bar
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def test_easyocr(image_path, force_cpu=False):
    print(f"Testing EasyOCR on: {image_path}")
    if not os.path.exists(image_path):
        print(f"Error: File {image_path} does not exist.")
        return False

    try:
        import torch
        use_gpu = torch.cuda.is_available() and not force_cpu
        device_str = f"GPU ({torch.cuda.get_device_name(0)})" if use_gpu else "CPU"
        print(f"Initializing EasyOCR on {device_str}...")
        print(f"Model Storage Directory: {EASYOCR_DIR}")
        reader = easyocr.Reader(
            ['en'],
            gpu=use_gpu,
            model_storage_directory=str(EASYOCR_DIR),
            download_enabled=True
        )

        print("Running OCR inference on image...")
        results = reader.readtext(image_path)

        if not results:
            print("No text detected in the image.")
            return False

        print("\n--- Extracted Text from Drawing ---")
        print(f"{'Confidence':>10}  Text")
        print("-" * 50)
        for (bbox, text, confidence) in results:
            print(f"{confidence:>10.2f}  {text}")

        print(f"\nTotal text regions detected: {len(results)}")
        print("\nTest Passed: EasyOCR successfully extracted text from the sample drawing!")
        return True

    except Exception as e:
        print(f"Test Failed with exception: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test EasyOCR on AegisForge sample data")
    parser.add_argument(
        "--image", type=str, required=True, help="Path to the sample image file to test"
    )
    parser.add_argument(
        "--cpu", action="store_true", help="Force CPU mode instead of GPU"
    )
    args = parser.parse_args()
    test_easyocr(args.image, force_cpu=args.cpu)
