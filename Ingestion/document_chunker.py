from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:
    """
    Splits loaded documents into smaller chunks suitable
    for embedding and vector storage.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ):
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than 0."
            )

        if chunk_overlap < 0:
            raise ValueError(
                "chunk_overlap cannot be negative."
            )

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

    def split_documents(
        self,
        documents: List[Document],
    ) -> List[Document]:
        """
        Split LangChain Documents into smaller Documents
        while preserving their metadata.
        """

        if not documents:
            return []

        chunks = self.splitter.split_documents(
            documents
        )

        # Add a chunk index for easier tracking.
        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = index

        return chunks


if __name__ == "__main__":

    sample_documents = [
        Document(
            page_content=(
                "This is a sample inspection report. "
                "The equipment was inspected according to "
                "the applicable engineering procedure. "
                "The measured thickness was recorded and "
                "the results were reviewed by the inspector."
            ),
            metadata={
                "filename": "inspection_report.txt",
                "document_id": "test-001",
            },
        )
    ]

    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = chunker.split_documents(
        sample_documents
    )

    print(f"Chunks created: {len(chunks)}")

    for chunk in chunks:
        print("\n--- Chunk ---")
        print(chunk.page_content)
        print("Metadata:", chunk.metadata)