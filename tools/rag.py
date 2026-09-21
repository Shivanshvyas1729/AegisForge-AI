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
