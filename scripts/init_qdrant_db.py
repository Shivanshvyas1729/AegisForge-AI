"""
scripts/init_qdrant_db.py
Database Initialization & Seeding CLI for Local Sovereign Qdrant Database.

Scans sample_data/ and data/uploads/, parses all documents (PDF, DOCX, MD, TXT, JSON, PNG),
extracts text chunks, embedded figures, and keyword values, and ingests them into the
local air-gapped Qdrant database in data/vector_storage/qdrant_db/.
"""

import os
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config.settings import (
    SAMPLE_DATA_DIR,
    UPLOADS_DIR,
    QDRANT_STORAGE_DIR,
    EXTRACTED_IMAGES_DIR,
)
from ingestion.multimodal_parser import parse_file_multimodal
from database.qdrant_manager import (
    init_collection,
    ingest_parsed_document,
    search_by_keywords,
    search_hybrid,
    get_collection_stats,
    COLLECTION_NAME,
)


def seed_database(recreate: bool = False):
    print("=" * 70)
    print("[INIT] INITIALIZING LOCAL SOVEREIGN MULTIMODAL QDRANT DATABASE")
    print("=" * 70)
    print(f"Target Storage Path:   {QDRANT_STORAGE_DIR}")
    print(f"Extracted Images Path: {EXTRACTED_IMAGES_DIR}")
    print(f"Collection Name:       {COLLECTION_NAME}")
    print("-" * 70)

    # 1. Initialize collection and payload schema indexes
    print("[1/3] Setting up Qdrant collection and keyword payload indexes...")
    init_collection(collection_name=COLLECTION_NAME, recreate=recreate)
    print("      ✓ Collection and indexes ready!")

    # 2. Collect candidate files to ingest
    print("\n[2/3] Scanning local knowledge repositories for documents and visual assets...")
    candidate_files = []
    
    supported_exts = [".md", ".txt", ".json", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".xlsx", ".xls", ".csv"]

    # Search sample_data
    if SAMPLE_DATA_DIR.exists():
        for p in SAMPLE_DATA_DIR.rglob("*"):
            if p.is_file() and p.suffix.lower() in supported_exts:
                candidate_files.append(p)

    # Search uploads
    if UPLOADS_DIR.exists():
        for p in UPLOADS_DIR.rglob("*"):
            if p.is_file() and p.suffix.lower() in supported_exts:
                candidate_files.append(p)

    print(f"      Found {len(candidate_files)} file(s) to process.")

    total_texts = 0
    total_images = 0

    for file_path in candidate_files:
        rel_path = file_path.relative_to(PROJECT_ROOT)
        print(f"  -> Ingesting: {rel_path} ({file_path.suffix.upper()})")
        parsed = parse_file_multimodal(file_path, output_image_dir=EXTRACTED_IMAGES_DIR)
        t_count = len(parsed["texts"])
        i_count = len(parsed["images"])
        print(f"     Parsed {t_count} text chunk(s), {i_count} image(s). Embedding & indexing...")
        
        counts = ingest_parsed_document(parsed, collection_name=COLLECTION_NAME)
        total_texts += counts["texts_indexed"]
        total_images += counts["images_indexed"]

    print(f"\n      [OK] Total Ingested: {total_texts} text chunk(s), {total_images} image asset(s)!")

    # 3. Verify retrieval functionality
    print("\n[3/3] Running verification retrieval queries...")
    stats = get_collection_stats(COLLECTION_NAME)
    print(f"      Collection Stats: points={stats.get('points_count')}, status={stats.get('status')}")

    # Test 1: Keyword retrieval
    test_keywords = ["asme", "ultrasonic"]
    print(f"\n  [QUERY] Testing Keyword Search for tags {test_keywords}:")
    kw_hits = search_by_keywords(test_keywords, limit=2)
    for i, h in enumerate(kw_hits, 1):
        print(f"     [{i}] Match: {h['source']} (Score: {h['score']}) | Keywords: {h['keywords']}")
        print(f"         Snippet: {h['text'][:120]}...")

    # Test 2: Hybrid semantic retrieval
    test_query = "wall thinning and remaining safe service life"
    print(f"\n  [QUERY] Testing Hybrid Semantic Search for: '{test_query}':")
    hybrid_hits = search_hybrid(test_query, limit=2)
    for i, h in enumerate(hybrid_hits, 1):
        print(f"     [{i}] Match: {h['source']} ({h['content_type']}) (Score: {h['score']})")
        if h['content_type'] == 'text':
            print(f"         Snippet: {h['text'][:120]}...")
        else:
            print(f"         Image: {h['image_path']}")

    print("\n" + "=" * 70)
    print("[SUCCESS] LOCAL QDRANT DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    recreate_flag = "--recreate" in sys.argv
    seed_database(recreate=recreate_flag)
