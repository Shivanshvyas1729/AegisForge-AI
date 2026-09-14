"""
AegisForge-AI: Safe Model Weights Uninstaller / Purge Utility
Safely removes downloaded model weights from <PROJECT_ROOT>/model_pool/
to immediately reclaim disk space without modifying any project code.
"""

import os
import sys
import shutil
from pathlib import Path
import argparse

# Dynamic project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import MODEL_POOL_DIR, EASYOCR_DIR, OLLAMA_MODELS_DIR


def get_dir_size_mb(path: Path) -> float:
    """Calculates total size of a directory in Megabytes."""
    if not path.exists():
        return 0.0
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def clean_models(force: bool = False):
    print("=" * 65)
    print("  AegisForge-AI: Safe Model Weights Uninstaller")
    print("=" * 65)
    print(f"Target Directory: {MODEL_POOL_DIR}")

    easyocr_size = get_dir_size_mb(EASYOCR_DIR)
    ollama_size = get_dir_size_mb(OLLAMA_MODELS_DIR)
    total_size = easyocr_size + ollama_size

    print(f"\nCurrent Storage Consumption in Project:")
    print(f"  - EasyOCR Weights:  {easyocr_size:.2f} MB")
    print(f"  - Ollama Weights:   {ollama_size:.2f} MB")
    print(f"  - Total Reclaimable: {total_size:.2f} MB ({(total_size/1024):.2f} GB)")

    if total_size == 0.0:
        print("\n[INFO] No model weights found in model_pool. Nothing to clean.")
        return

    if not force:
        confirm = input("\nAre you sure you want to delete these model weights? (y/N): ").strip().lower()
        if confirm != 'y':
            print("[INFO] Cleanup aborted. No files were deleted.")
            return

    print("\n[*] Purging model weights from project...")

    # 1. Clean EasyOCR weights (*.pth)
    if EASYOCR_DIR.exists():
        for pth in EASYOCR_DIR.glob("*.pth"):
            try:
                pth.unlink()
                print(f"    Deleted: {pth.name}")
            except Exception as e:
                print(f"    Failed to delete {pth.name}: {e}")

    # 2. Clean Ollama blobs and manifests
    for sub in ["blobs", "manifests"]:
        target_dir = OLLAMA_MODELS_DIR / sub
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
                print(f"    Deleted: {OLLAMA_MODELS_DIR.name}/{sub}/")
            except Exception as e:
                print(f"    Failed to delete {sub}: {e}")

    # Ensure .gitkeep files remain so git directories are preserved
    for d in [EASYOCR_DIR, OLLAMA_MODELS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    print(f"\n[+] Cleanup complete! Successfully reclaimed {(total_size/1024):.2f} GB.")
    print("    Source code and project files remain intact.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safely purge model weights from project model_pool")
    parser.add_argument("-y", "--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    clean_models(force=args.force)
