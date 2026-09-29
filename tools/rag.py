from typing import List, Optional

from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from Ingestion.embedding_generator import OllamaEmbeddingGenerator


class RAG:
    """
    Retrieval layer for the local knowledge base.

    Responsibilities:
    - Convert a user query into an embedding.
    - Search the local Qdrant knowledge base.
    - Return the most relevant document chunks.

    This class does NOT call a chat/LLM model.
    The model router / agent handles answer generation later.
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = "knowledge_base",
        embedding_model: str = "nomic-embed-text",
    ):
        self.client = client
        self.collection_name = collection_name

        self.embedding_generator = OllamaEmbeddingGenerator(
            model_name=embedding_model
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> List[Document]:
        """
        Retrieve the most relevant chunks for a query.

        Args:
            query: User's question or search query.
            top_k: Maximum number of chunks to retrieve.
            document_id: Optional document-specific filter.

        Returns:
            List of relevant LangChain Documents.
        """

        if not query.strip():
            raise ValueError("Query cannot be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than 0.")

        # Convert query into an embedding.
        query_vector = self.embedding_generator.embed_query(query)

        # Optional filtering by document ID.
        query_filter = None

        if document_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

        # Search local Qdrant.
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        documents = []

        for point in results.points:
            payload = point.payload or {}

            text = payload.get("text", "")

            metadata = {
                key: value
                for key, value in payload.items()
                if key != "text"
            }

            metadata["score"] = point.score
            metadata["point_id"] = str(point.id)

            documents.append(
                Document(
                    page_content=text,
                    metadata=metadata,
                )
            )

        return documents

    @staticmethod
    def build_context(documents: List[Document]) -> str:
        """
        Combine retrieved chunks into a context string.

        This context can later be passed to the model router/LLM.
        """

        if not documents:
            return ""

        context_parts = []

        for index, document in enumerate(documents, start=1):
            context_parts.append(
                f"[Context {index}]\n"
                f"{document.page_content}"
            )

        return "\n\n".join(context_parts)


import os
import glob
import re
import logging
from langchain_core.tools import tool

logger = logging.getLogger("AegisForge.RAG")


@tool
def search_local_knowledge(query: str, top_k: int = 3) -> str:
    """
    Searches the air-gapped sovereign mining knowledge base:
    - Coal Mines Regulations 2017 (CMR 2017 Reg 104, 105, 106)
    - CMPDI Geological Reporting & UNFC Coal Reserves Guidelines (UNFC-111, UNFC-122)
    - Ministry of Coal Parliamentary Questions (PQs) precedents and standing reporting templates
    - CIL subsidiary operational mandates (ECL, BCCL, CCL, WCL, SECL, MCL, NCL)
    """
    logger.info(f"Executing tool: search_local_knowledge (Query: {query})")
    print(f"\n--- EXECUTING TOOL: search_local_knowledge (Query: {query}) ---\n")

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    kb_dirs = [
        os.path.join(workspace_root, "data", "knowledge_base"),
        os.path.join(workspace_root, "data", "sample_reports"),
        os.path.join(workspace_root, "data", "data_sample", "01_approval_notes"),
    ]

    files = []
    for d in kb_dirs:
        if os.path.exists(d):
            files.extend(glob.glob(os.path.join(d, "*.*")))


    query_terms = set(re.findall(r'\w+', query.lower()))
    matches = []

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        text = ""
        try:
            if ext == ".pdf":
                import pypdf
                reader = pypdf.PdfReader(f)
                text = "\n".join([p.extract_text() or "" for p in reader.pages])
            elif ext in (".txt", ".md", ".json", ".csv"):
                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    text = fp.read()
        except Exception as e:
            logger.debug(f"Failed reading {f}: {e}")
            continue

        if text.strip():
            score = sum(1 for term in query_terms if term in text.lower())
            if score > 0:
                matches.append({
                    "file": os.path.basename(f),
                    "score": score,
                    "content": text.strip()
                })

    matches.sort(key=lambda x: x["score"], reverse=True)
    top_matches = matches[:top_k]

    if not top_matches:
        return f"[KNOWLEDGE_BASE_SEARCH]: No matching documents found for query: '{query}'."

    results = []
    for idx, m in enumerate(top_matches, start=1):
        results.append(
            f"--- Document {idx}: {m['file']} (Relevance Score: {m['score']}) ---\n"
            f"{m['content']}\n"
        )

    return "\n".join(results)

