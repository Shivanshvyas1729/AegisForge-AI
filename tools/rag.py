"""
tools/rag.py
Air-Gapped Sovereign Multimodal RAG & Knowledge Retrieval Tool.
Backed by local embedded Qdrant vector database (data/vector_storage/qdrant_db/)
with unified CLIP embeddings for text & diagrams, and pre-indexed keyword filters.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

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

# Locate project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import SAMPLE_DATA_DIR, QDRANT_STORAGE_DIR, logger


def search_local_knowledge(
    query: str,
    max_results: int = 3,
    filter_keywords: Optional[List[str]] = None,
) -> str:
    """
    Retrieves relevant knowledge snippets (text chunks, code clauses, and visual diagrams)
    from the local sovereign Qdrant database. Falls back to sample_data file scan if Qdrant is empty.
    """
    # 1. Primary path: Local Qdrant Vector & Keyword Engine
    try:
        from database.qdrant_manager import search_hybrid, search_by_keywords, get_collection_stats, COLLECTION_NAME

        stats = get_collection_stats(COLLECTION_NAME)
        if stats.get("points_count", 0) > 0:
            # Check if query specifically targets keywords
            hits = search_hybrid(
                query_text=query,
                filter_keywords=filter_keywords,
                limit=max_results,
            )
            if hits:
                formatted = [f"Found {len(hits)} relevant multimodal knowledge snippet(s) from local Qdrant for '{query}':\n"]
                for i, res in enumerate(hits, 1):
                    kw_tag = f" [Keywords: {', '.join(res['keywords'][:4])}]" if res.get('keywords') else ""
                    if res.get("content_type") == "text":
                        formatted.append(f"[{i}] (Text) Source: {res['source']}{kw_tag} (Score: {res['score']})\n{res['text']}\n")
                    else:
                        caption = res.get('caption') or 'Diagram'
                        formatted.append(f"[{i}] (Visual Asset) Source: {res['source']} - {caption} (Score: {res['score']})\nImage: {res.get('image_path')}\n")
                return "\n".join(formatted)
    except Exception as e:
        logger.debug(f"Qdrant retrieval fallback triggered: {e}")

    # 2. Fallback path: Basic lexical search over sample_data/
    if not SAMPLE_DATA_DIR.exists():
        return f"Knowledge base directory not found at {SAMPLE_DATA_DIR}."

    query_tokens = set(re.findall(r"\w+", query.lower()))
    stopwords = {"the", "a", "an", "is", "in", "and", "or", "for", "of", "to", "on", "with", "what", "how", "why", "need", "give", "me"}
    search_terms = query_tokens - stopwords or query_tokens

    results = []
    for file_path in SAMPLE_DATA_DIR.rglob("*"):
        if file_path.suffix.lower() in [".md", ".txt", ".json", ".py"]:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 30]
                for p in paragraphs:
                    p_lower = p.lower()
                    score = sum(1 for term in search_terms if term in p_lower)
                    if score > 0:
                        results.append({
                            "score": score,
                            "source": file_path.name,
                            "text": p[:400] + ("..." if len(p) > 400 else "")
                        })
            except Exception:
                continue

    if not results:
        return f"No local reference documents specifically matched '{query}'."

    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:max_results]

    formatted = [f"Found {len(top_results)} relevant knowledge snippet(s) for '{query}':\n"]
    for i, res in enumerate(top_results, 1):
        formatted.append(f"[{i}] Source: {res['source']}\n{res['text']}\n")

    return "\n".join(formatted)


def search_knowledge_by_keywords(keywords: List[str], max_results: int = 3) -> str:
    """
    Direct keyword-value indexed retrieval (near-zero latency, exact tag match).
    """
    try:
        from database.qdrant_manager import search_by_keywords
        hits = search_by_keywords(keywords=keywords, limit=max_results)
        if not hits:
            return f"No knowledge records matched keywords: {keywords}"

        formatted = [f"Found {len(hits)} indexed record(s) matching keywords {keywords}:\n"]
        for i, res in enumerate(hits, 1):
            if res.get("content_type") == "text":
                formatted.append(f"[{i}] Source: {res['source']} | Tags: {res.get('keywords')}\n{res['text']}\n")
            else:
                formatted.append(f"[{i}] Visual Asset: {res['source']} - {res.get('caption')}\nImage: {res.get('image_path')}\n")
        return "\n".join(formatted)
    except Exception as e:
        return f"Keyword index lookup failed: {e}"


try:
    from langchain_core.tools import tool
    import time
    from tools.audit_trail import append_audit_event

    @tool
    def rag_tool(query: str) -> str:
        """
        Search the local air-gapped PSU knowledge base (ASME codes, CVC rules, NDT reports, P&ID schematics)
        and return relevant context snippets.
        
        Args:
            query: Natural language engineering or regulatory question to search
        """
        start_time = time.time()
        try:
            res = search_local_knowledge(query)
            duration_ms = (time.time() - start_time) * 1000
            append_audit_event(
                tool_name="rag_tool",
                inputs={"query": query},
                outputs={"result_preview": res[:200] if isinstance(res, str) else str(res)},
                status="SUCCESS",
                duration_ms=duration_ms,
                caller="rag_tool"
            )
            return res
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            append_audit_event(
                tool_name="rag_tool",
                inputs={"query": query},
                outputs={"error": str(e)},
                status="FAILURE",
                duration_ms=duration_ms,
                caller="rag_tool"
            )
            return f"RAG search error: {str(e)}"

    # Backward compatibility alias
    rag = rag_tool

except ImportError:
    rag_tool = None
    rag = None


if __name__ == "__main__":
    test_q = "CVC circular emergency single-source procurement"
    print("Testing local RAG knowledge search on:", test_q)
    print("-" * 60)
    print(search_local_knowledge(test_q))
