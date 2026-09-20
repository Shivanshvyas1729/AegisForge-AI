from typing import List

import requests
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class OllamaEmbeddingGenerator(Embeddings):
    """
    Generates text embeddings using a local Ollama embedding model.

    Default model:
        nomic-embed-text

    No external API or cloud service is used.
    """

    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        ollama_url: str = "http://localhost:11434",
    ):
        self.model_name = model_name
        self.ollama_url = ollama_url.rstrip("/")

    def _embed(self, text: str) -> List[float]:
        """
        Generate one embedding using Ollama.
        """

        if not text.strip():
            raise ValueError(
                "Cannot generate an embedding for empty text."
            )

        response = requests.post(
            f"{self.ollama_url}/api/embed",
            json={
                "model": self.model_name,
                "input": text,
            },
            timeout=120,
        )

        response.raise_for_status()

        result = response.json()

        embeddings = result.get("embeddings")

        if not embeddings:
            raise RuntimeError(
                "Ollama did not return an embedding."
            )

        return embeddings[0]

    def embed_documents(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        """

        if not texts:
            return []

        response = requests.post(
            f"{self.ollama_url}/api/embed",
            json={
                "model": self.model_name,
                "input": texts,
            },
            timeout=120,
        )

        response.raise_for_status()

        result = response.json()

        embeddings = result.get("embeddings")

        if embeddings is None:
            raise RuntimeError(
                "Ollama did not return document embeddings."
            )

        return embeddings

    def embed_query(
        self,
        text: str,
    ) -> List[float]:
        """
        Generate an embedding for a search query.
        """

        return self._embed(text)

    def embed_documents_from_chunks(
        self,
        documents: List[Document],
    ) -> List[List[float]]:
        """
        Generate embeddings directly from LangChain Documents.
        """

        texts = [
            document.page_content
            for document in documents
        ]

        return self.embed_documents(texts)


if __name__ == "__main__":

    embedding_generator = OllamaEmbeddingGenerator(
        model_name="nomic-embed-text"
    )

    test_text = (
        "Ultrasonic thickness inspection "
        "of nozzle BK-01."
    )

    vector = embedding_generator.embed_query(
        test_text
    )

    print("Model:", embedding_generator.model_name)
    print("Embedding dimensions:", len(vector))
    print("First 10 values:", vector[:10])