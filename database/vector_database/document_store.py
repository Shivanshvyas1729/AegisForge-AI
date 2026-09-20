import uuid
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from langchain_core.documents import Document


class DocumentStore:
    """
    Stores document chunks and their embeddings in local Qdrant.
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = "knowledge_base",
    ):
        self.client = client
        self.collection_name = collection_name

    def add_documents(
        self,
        documents: List[Document],
        embeddings: List[List[float]],
    ) -> int:
        """
        Store document chunks and embeddings in Qdrant.

        Each chunk receives a unique UUID so that different
        ingestion runs cannot overwrite each other.
        """

        if len(documents) != len(embeddings):
            raise ValueError(
                "Number of documents must match number of embeddings."
            )

        if not documents:
            return 0

        points = []

        for document, embedding in zip(documents, embeddings):

            # Generate a unique ID for every chunk
            point_id = str(uuid.uuid4())

            # Store text + metadata in Qdrant payload
            payload = {
                "text": document.page_content,
                **document.metadata,
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        return len(points)


if __name__ == "__main__":
    from database.vector_database.qdrant_connection import LocalQdrantClient

    qdrant = LocalQdrantClient()

    try:
        store = DocumentStore(
            client=qdrant.get_client(),
            collection_name="knowledge_base",
        )

        test_documents = [
            Document(
                page_content="Ultrasonic thickness inspection of vessel.",
                metadata={
                    "document_id": "test-001",
                    "filename": "inspection.txt",
                    "keywords": ["inspection", "thickness"],
                },
            ),
            Document(
                page_content="Minimum wall thickness was measured.",
                metadata={
                    "document_id": "test-001",
                    "filename": "inspection.txt",
                    "keywords": ["thickness"],
                },
            ),
        ]

        test_embeddings = [
            [0.0] * 768,
            [0.0] * 768,
        ]

        count = store.add_documents(
            documents=test_documents,
            embeddings=test_embeddings,
        )

        print(f"Stored {count} document chunks successfully.")

    finally:
        qdrant.close()