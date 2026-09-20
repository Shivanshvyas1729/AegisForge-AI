from typing import List, Optional

from langchain_core.documents import Document

from Ingestion.document_loader import load_document
from Ingestion.document_chunker import DocumentChunker
from Ingestion.metadata_extractor import MetadataExtractor
from Ingestion.embedding_generator import OllamaEmbeddingGenerator

from database.vector_database.qdrant_connection import (
    LocalQdrantClient,
)
from database.vector_database.collection_manager import (
    CollectionManager,
)
from database.vector_database.document_store import (
    DocumentStore,
)


class IngestionPipeline:
    """
    Complete local knowledge-base ingestion pipeline.

    File
      ↓
    Loader
      ↓
    Chunker
      ↓
    Metadata
      ↓
    Embeddings
      ↓
    Qdrant
    """

    def __init__(
        self,
        collection_name: str = "knowledge_base",
        embedding_model: str = "nomic-embed-text",
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ):

        # Local Qdrant
        self.qdrant = LocalQdrantClient()
        self.client = self.qdrant.get_client()

        # Chunking
        self.chunker = DocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Metadata
        self.metadata_extractor = MetadataExtractor()

        # Local Ollama embeddings
        self.embedding_generator = (
            OllamaEmbeddingGenerator(
                model_name=embedding_model
            )
        )

        # Get embedding dimension automatically
        test_vector = self.embedding_generator.embed_query(
            "test"
        )

        vector_size = len(test_vector)

        # Qdrant collection
        self.collection_manager = CollectionManager(
            client=self.client,
            collection_name=collection_name,
            vector_size=vector_size,
        )

        self.collection_manager.create_collection()

        # Document storage
        self.document_store = DocumentStore(
            client=self.client,
            collection_name=collection_name,
        )

        self.collection_name = collection_name

    def ingest(
        self,
        file_path: str,
        document_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Process and store one document.
        """

        # 1. Load document
        documents = load_document(file_path)

        # 2. Add metadata
        documents = self.metadata_extractor.extract(
            documents=documents,
            document_id=document_id,
            keywords=keywords,
            category=category,
            description=description,
        )

        # 3. Split into chunks
        chunks = self.chunker.split_documents(
            documents
        )

        # 4. Generate embeddings
        embeddings = (
            self.embedding_generator
            .embed_documents_from_chunks(chunks)
        )

        # 5. Store in Qdrant
        vectors_created = (
            self.document_store.add_documents(
                documents=chunks,
                embeddings=embeddings,
            )
        )

        return {
            "document_id": chunks[0].metadata["document_id"],
            "filename": chunks[0].metadata["filename"],
            "chunks_created": len(chunks),
            "vectors_created": vectors_created,
            "collection_name": self.collection_name,
            "keywords": chunks[0].metadata.get(
                "keywords",
                [],
            ),
            "status": "success",
        }

    def close(self):
        """Close the local Qdrant connection."""

        self.qdrant.close()


if __name__ == "__main__":

    pipeline = IngestionPipeline()

    try:

        result = pipeline.ingest(
            file_path="test_data/sample.txt",
            keywords=[
                "inspection",
                "engineering",
            ],
            category="Engineering",
        )

        print("\n--- Ingestion Result ---")
        print(result)

    finally:
        pipeline.close()