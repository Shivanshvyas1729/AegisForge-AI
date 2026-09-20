from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


class CollectionManager:
    """
    Manages collections in the local Qdrant database.
    """

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = "knowledge_base",
        vector_size: int = 768,
    ):
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size

    def collection_exists(self) -> bool:
        """Check whether the collection already exists."""

        collections = self.client.get_collections()

        return any(
            collection.name == self.collection_name
            for collection in collections.collections
        )

    def create_collection(self) -> None:
        """
        Create the knowledge-base collection if it
        does not already exist.
        """

        if self.collection_exists():
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

    def delete_collection(self) -> None:
        """Delete the collection."""

        if self.collection_exists():
            self.client.delete_collection(
                collection_name=self.collection_name
            )

    def recreate_collection(self) -> None:
        """Delete and recreate the collection."""

        self.delete_collection()
        self.create_collection()


if __name__ == "__main__":

    from qdrant_connection import LocalQdrantClient

    qdrant = LocalQdrantClient()
    client = qdrant.get_client()

    manager = CollectionManager(
        client=client,
        collection_name="knowledge_base",
        vector_size=768,
    )

    manager.create_collection()

    print(
        f"Collection '{manager.collection_name}' "
        "is ready."
    )

    qdrant.close()