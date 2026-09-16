"""
database/qdrant_manager.py
Air-Gapped Sovereign Qdrant Vector Database Manager for AegisForge-AI.

Features:
1. Pure Local Embedded Execution: QdrantClient(path=...) stored on local disk in data/vector_storage/qdrant_db.
2. True Multimodal Vector Alignment: 512-d CLIP models (clip-ViT-B-32-text and clip-ViT-B-32-vision) mapping
   both text and images into the exact same vector space.
3. Indexed Keyword & Full-Text Payloads: Pre-indexed payload schema for ultra-fast, optimized keyword filtering
   alongside dense semantic retrieval.
4. Flexible Retrieval: Pure keyword lookup, semantic vector search, hybrid keyword-filtered search, and image-to-text / image-to-image queries.
"""

import os
import sys
import uuid
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import QDRANT_STORAGE_DIR, logger
from qdrant_client import QdrantClient, models

COLLECTION_NAME = "sovereign_multimodal_knowledge"
VECTOR_DIMENSION = 512

_client_instance: Optional[QdrantClient] = None
_client_lock = threading.Lock()

_text_embedder = None
_image_embedder = None
_embedder_lock = threading.Lock()


import atexit

def _cleanup():
    global _client_instance
    with _client_lock:
        if _client_instance is not None:
            try:
                _client_instance.close()
            except Exception:
                pass
            _client_instance = None

atexit.register(_cleanup)


def get_qdrant_client() -> QdrantClient:
    """
    Returns a thread-safe embedded local Qdrant client anchored to QDRANT_STORAGE_DIR.
    Runs 100% in-process without Docker or network sockets.
    """
    global _client_instance
    with _client_lock:
        if _client_instance is None:
            QDRANT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initializing local embedded Qdrant database at {QDRANT_STORAGE_DIR}")
            _client_instance = QdrantClient(path=str(QDRANT_STORAGE_DIR))
        return _client_instance


def get_text_embedder():
    """Lazy loader for FastEmbed CLIP Text embedder."""
    global _text_embedder
    with _embedder_lock:
        if _text_embedder is None:
            from fastembed import TextEmbedding
            logger.info("Loading FastEmbed CLIP Text embedder (Qdrant/clip-ViT-B-32-text)...")
            _text_embedder = TextEmbedding(model_name="Qdrant/clip-ViT-B-32-text")
        return _text_embedder


def get_image_embedder():
    """Lazy loader for FastEmbed CLIP Image embedder."""
    global _image_embedder
    with _embedder_lock:
        if _image_embedder is None:
            from fastembed import ImageEmbedding
            logger.info("Loading FastEmbed CLIP Vision embedder (Qdrant/clip-ViT-B-32-vision)...")
            _image_embedder = ImageEmbedding(model_name="Qdrant/clip-ViT-B-32-vision")
        return _image_embedder


def init_collection(collection_name: str = COLLECTION_NAME, recreate: bool = False) -> None:
    """
    Ensures the multimodal collection exists and initializes optimized payload indexes
    for keyword tagging and full-text search.
    """
    client = get_qdrant_client()
    existing_collections = [c.name for c in client.get_collections().collections]

    if recreate and collection_name in existing_collections:
        logger.info(f"Recreating collection {collection_name}")
        client.delete_collection(collection_name=collection_name)
        existing_collections.remove(collection_name)

    if collection_name not in existing_collections:
        logger.info(f"Creating collection {collection_name} with dim={VECTOR_DIMENSION}, metric=Cosine")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=VECTOR_DIMENSION,
                distance=models.Distance.COSINE,
            ),
        )

    # Configure payload schema indexes for fast keyword filtering & inverted text search
    indexed_fields = {
        "keywords": models.PayloadSchemaType.KEYWORD,
        "content_type": models.PayloadSchemaType.KEYWORD,
        "source": models.PayloadSchemaType.KEYWORD,
        "category": models.PayloadSchemaType.KEYWORD,
        "equipment_id": models.PayloadSchemaType.KEYWORD,
    }

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        for field_name, schema in indexed_fields.items():
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=schema,
                )
            except Exception as e:
                logger.debug(f"Payload index for '{field_name}' returned: {e}")

        # Full-text inverted index for lightning-fast keyword matching across text
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name="text",
                field_schema=models.TextIndexParams(
                    type="text",
                    tokenizer=models.TokenizerType.WORD,
                    lowercase=True,
                ),
            )
        except Exception as e:
            logger.debug(f"Full-text payload index returned: {e}")


def upsert_texts(
    texts: List[Dict[str, Any]],
    collection_name: str = COLLECTION_NAME,
) -> int:
    """
    Embeds and upserts a list of text chunks with keyword metadata into Qdrant.
    """
    if not texts:
        return 0

    client = get_qdrant_client()
    init_collection(collection_name)
    embedder = get_text_embedder()

    raw_texts = [item.get("text", "") for item in texts]
    vectors = list(embedder.embed(raw_texts))

    points = []
    for idx, item in enumerate(texts):
        pt_id = item.get("id") or str(uuid.uuid4())
        payload = {
            "content_type": "text",
            "text": item.get("text", ""),
            "keywords": item.get("keywords", []),
            "source": item.get("source", "unknown"),
            "page": item.get("page", 1),
            "chunk_index": item.get("chunk_index", idx + 1),
            "category": item.get("category", "document"),
            "equipment_id": item.get("equipment_id", ""),
        }
        points.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, str(pt_id))),
            vector=vectors[idx].tolist(),
            payload=payload,
        ))

    client.upsert(collection_name=collection_name, points=points)
    logger.info(f"Upserted {len(points)} text chunks into Qdrant collection '{collection_name}'.")
    return len(points)


def upsert_images(
    images: List[Dict[str, Any]],
    collection_name: str = COLLECTION_NAME,
) -> int:
    """
    Embeds and upserts a list of image items (with OCR text & keywords) into Qdrant.
    """
    if not images:
        return 0

    client = get_qdrant_client()
    init_collection(collection_name)
    embedder = get_image_embedder()

    valid_images = []
    image_paths = []
    for item in images:
        p = item.get("image_path")
        if p and Path(p).exists():
            valid_images.append(item)
            image_paths.append(str(p))

    if not valid_images:
        return 0

    vectors = list(embedder.embed(image_paths))

    points = []
    for idx, item in enumerate(valid_images):
        pt_id = item.get("id") or str(uuid.uuid4())
        payload = {
            "content_type": "image",
            "image_path": item.get("image_path", ""),
            "ocr_text": item.get("ocr_text", ""),
            "keywords": item.get("keywords", []),
            "source": item.get("source", "unknown"),
            "page": item.get("page", 1),
            "caption": item.get("caption", ""),
            "category": item.get("category", "schematic"),
            "equipment_id": item.get("equipment_id", ""),
        }
        points.append(models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, str(pt_id))),
            vector=vectors[idx].tolist(),
            payload=payload,
        ))

    client.upsert(collection_name=collection_name, points=points)
    logger.info(f"Upserted {len(points)} images into Qdrant collection '{collection_name}'.")
    return len(points)


def ingest_parsed_document(
    parsed_data: Dict[str, List[Dict[str, Any]]],
    collection_name: str = COLLECTION_NAME,
) -> Dict[str, int]:
    """Ingests both text and image streams from a parsed document."""
    t_count = upsert_texts(parsed_data.get("texts", []), collection_name)
    i_count = upsert_images(parsed_data.get("images", []), collection_name)
    return {"texts_indexed": t_count, "images_indexed": i_count}


def search_by_keywords(
    keywords: List[str],
    collection_name: str = COLLECTION_NAME,
    content_type: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Optimized exact/multi-tag keyword retrieval using Qdrant's payload index.
    Bypasses vector math for near-instantaneous (< 5ms) metadata matches.
    """
    client = get_qdrant_client()
    normalized = [k.strip().lower() for k in keywords if k and isinstance(k, str)]
    if not normalized:
        return []

    conditions = [
        models.FieldCondition(
            key="keywords",
            match=models.MatchAny(any=normalized)
        )
    ]
    if content_type:
        conditions.append(
            models.FieldCondition(
                key="content_type",
                match=models.MatchValue(value=content_type)
            )
        )

    filter_query = models.Filter(must=conditions)

    # Scroll using the filter
    points, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter=filter_query,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    results = []
    for pt in points:
        results.append({
            "id": pt.id,
            "score": 1.0,  # Exact match
            "match_type": "keyword_index",
            "content_type": pt.payload.get("content_type", "text"),
            "source": pt.payload.get("source", ""),
            "page": pt.payload.get("page", 1),
            "keywords": pt.payload.get("keywords", []),
            "text": pt.payload.get("text", "") if pt.payload.get("content_type") == "text" else pt.payload.get("ocr_text", ""),
            "image_path": pt.payload.get("image_path", ""),
            "caption": pt.payload.get("caption", ""),
        })

    return results


def search_hybrid(
    query_text: str,
    filter_keywords: Optional[List[str]] = None,
    content_type: Optional[str] = None,
    collection_name: str = COLLECTION_NAME,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Unified multimodal semantic search:
    Embeds the text query into 512-d CLIP space and finds the top matching text chunks
    and industrial images, optionally filtered by keyword values.
    """
    client = get_qdrant_client()
    embedder = get_text_embedder()

    query_vector = list(embedder.embed([query_text]))[0].tolist()

    filter_conditions = []
    if filter_keywords:
        normalized_kw = [k.strip().lower() for k in filter_keywords if k]
        if normalized_kw:
            filter_conditions.append(
                models.FieldCondition(
                    key="keywords",
                    match=models.MatchAny(any=normalized_kw)
                )
            )
    if content_type:
        filter_conditions.append(
            models.FieldCondition(
                key="content_type",
                match=models.MatchValue(value=content_type)
            )
        )

    query_filter = models.Filter(must=filter_conditions) if filter_conditions else None

    # Compatible with qdrant-client >= 1.10.0 (query_points)
    if hasattr(client, "query_points"):
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        search_hits = response.points
    else:
        search_hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    results = []
    for hit in search_hits:
        results.append({
            "id": hit.id,
            "score": round(hit.score, 4),
            "match_type": "multimodal_dense",
            "content_type": hit.payload.get("content_type", "text"),
            "source": hit.payload.get("source", ""),
            "page": hit.payload.get("page", 1),
            "keywords": hit.payload.get("keywords", []),
            "text": hit.payload.get("text", "") if hit.payload.get("content_type") == "text" else hit.payload.get("ocr_text", ""),
            "image_path": hit.payload.get("image_path", ""),
            "caption": hit.payload.get("caption", ""),
        })

    return results


def search_by_image(
    image_path: Union[str, Path],
    filter_keywords: Optional[List[str]] = None,
    collection_name: str = COLLECTION_NAME,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Visual search: Embeds an input diagram or photo and retrieves visually similar images
    or semantically aligned text descriptions.
    """
    path = Path(image_path)
    if not path.exists():
        logger.warning(f"Query image does not exist: {path}")
        return []

    client = get_qdrant_client()
    embedder = get_image_embedder()
    query_vector = list(embedder.embed([str(path)]))[0].tolist()

    filter_conditions = []
    if filter_keywords:
        normalized_kw = [k.strip().lower() for k in filter_keywords if k]
        if normalized_kw:
            filter_conditions.append(
                models.FieldCondition(
                    key="keywords",
                    match=models.MatchAny(any=normalized_kw)
                )
            )

    query_filter = models.Filter(must=filter_conditions) if filter_conditions else None

    if hasattr(client, "query_points"):
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        search_hits = response.points
    else:
        search_hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    results = []
    for hit in search_hits:
        results.append({
            "id": hit.id,
            "score": round(hit.score, 4),
            "match_type": "visual_dense",
            "content_type": hit.payload.get("content_type", "text"),
            "source": hit.payload.get("source", ""),
            "page": hit.payload.get("page", 1),
            "keywords": hit.payload.get("keywords", []),
            "text": hit.payload.get("text", "") if hit.payload.get("content_type") == "text" else hit.payload.get("ocr_text", ""),
            "image_path": hit.payload.get("image_path", ""),
            "caption": hit.payload.get("caption", ""),
        })

    return results


def get_collection_stats(collection_name: str = COLLECTION_NAME) -> Dict[str, Any]:
    """Returns total points and indexing status of the local Qdrant collection."""
    try:
        client = get_qdrant_client()
        count_res = client.count(collection_name)
        cnt = count_res.count if hasattr(count_res, "count") else int(count_res)
        info = client.get_collection(collection_name)
        status_str = str(info.status) if hasattr(info, "status") else "green"
        return {
            "collection_name": collection_name,
            "status": status_str,
            "points_count": cnt,
            "storage_path": str(QDRANT_STORAGE_DIR),
        }
    except Exception as e:
        return {
            "collection_name": collection_name,
            "status": "not_found_or_error",
            "error": str(e),
            "storage_path": str(QDRANT_STORAGE_DIR),
        }
