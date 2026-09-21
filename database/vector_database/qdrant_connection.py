from pathlib import Path

from qdrant_client import QdrantClient


class LocalQdrantClient:
    """
    Local persistent Qdrant client.

    Qdrant runs entirely on the local machine.
    No external server or cloud service is required.
    """

    def __init__(
        self,
        storage_path: str = "database/vector_database/qdrant_storage",
    ):
        self.storage_path = Path(storage_path)

        self.storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = QdrantClient(
            path=str(self.storage_path)
        )

    def get_client(self) -> QdrantClient:
        """Return the Qdrant client."""

        return self.client

    def close(self) -> None:
        """Close the Qdrant client."""

        self.client.close()


if __name__ == "__main__":

    qdrant = LocalQdrantClient()

    client = qdrant.get_client()

    print("Qdrant initialized successfully.")
    print(
        "Storage:",
        qdrant.storage_path.resolve()
    )

    print(
        "Collections:",
        [
            collection.name
            for collection in client.get_collections().collections
        ]
    )

    qdrant.close()