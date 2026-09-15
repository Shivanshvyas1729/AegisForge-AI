"""
tools/rag.py
Air-Gapped Sovereign RAG & Knowledge Retrieval Tool.
Searches local PSU standards, ASME calculations, CVC guidelines, and sample documents
stored in sample_data/ without external cloud dependencies.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

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

# Locate sample_data relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"


def search_local_knowledge(query: str, max_results: int = 3) -> str:
    """
    Scans local sample_data documents for keywords matching the query and returns
    relevant excerpts with source attribution.
    """
    if not SAMPLE_DATA_DIR.exists():
        return f"Knowledge base directory not found at {SAMPLE_DATA_DIR}."

    query_tokens = set(re.findall(r"\w+", query.lower()))
    # Ignore trivial stopwords
    stopwords = {"the", "a", "an", "is", "in", "and", "or", "for", "of", "to", "on", "with", "what", "how", "why", "need", "give", "me"}
    search_terms = query_tokens - stopwords
    if not search_terms:
        search_terms = query_tokens

    results = []

    # Search markdown, txt, and json files in sample_data
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
        return f"No local reference documents specifically matched '{query}'. (Searched {SAMPLE_DATA_DIR.name}/)"

    # Sort by relevance score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:max_results]

    formatted = [f"Found {len(top_results)} relevant knowledge snippet(s) for '{query}':\n"]
    for i, res in enumerate(top_results, 1):
        formatted.append(f"[{i}] Source: {res['source']}\n{res['text']}\n")

    return "\n".join(formatted)


try:
    from langchain_core.tools import tool

    @tool
    def rag(query: str) -> str:
        """
        Search the local air-gapped PSU knowledge base (ASME codes, CVC rules, NDT reports)
        and return relevant context snippets.
        """
        return search_local_knowledge(query)
except ImportError:
    rag = None


if __name__ == "__main__":
    test_q = "CVC circular emergency single-source procurement"
    print("Testing local RAG knowledge search on:", test_q)
    print("-" * 60)
    print(search_local_knowledge(test_q))
