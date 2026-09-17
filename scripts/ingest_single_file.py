"""
scripts/ingest_single_file.py
CLI to ingest a single arbitrary file from any absolute or relative path directly into the Qdrant database.
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import EXTRACTED_IMAGES_DIR, logger
from ingestion.multimodal_parser import parse_file_multimodal
from database.qdrant_manager import ingest_parsed_document, COLLECTION_NAME


def main():
    parser = argparse.ArgumentParser(description="Ingest a specific file into the AegisForge-AI Qdrant database.")
    parser.add_argument("file_path", type=str, help="Absolute or relative path to the file to ingest.")
    args = parser.parse_args()

    file_path = Path(args.file_path).resolve()
    
    if not file_path.exists() or not file_path.is_file():
        print(f"Error: The file '{file_path}' does not exist or is not a valid file.")
        sys.exit(1)

    print(f"[*] Starting ingestion for: {file_path}")
    
    try:
        # 1. Parse
        print("[*] Parsing file (extracting text chunks and embedded images)...")
        parsed = parse_file_multimodal(file_path, output_image_dir=EXTRACTED_IMAGES_DIR)
        
        # 2. Ingest
        t_count = len(parsed["texts"])
        i_count = len(parsed["images"])
        print(f"[*] Extracted {t_count} text chunks and {i_count} images.")
        
        print(f"[*] Embedding and indexing into Qdrant collection '{COLLECTION_NAME}'...")
        counts = ingest_parsed_document(parsed, collection_name=COLLECTION_NAME)
        
        print("[+] Success!")
        print(f"    Indexed {counts['texts_indexed']} text records and {counts['images_indexed']} image records.")

    except Exception as e:
        logger.exception("Failed to ingest file.")
        print(f"[-] Error during ingestion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
