from pathlib import Path
from typing import Dict, List, Optional

from langchain_core.documents import Document


class MetadataExtractor:
    """
    Extracts and manages metadata for knowledge-base documents.

    User-provided metadata is combined with automatically generated
    file metadata.

    No external API or cloud service is used.
    """

    def extract(
        self,
        documents: List[Document],
        document_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
    ) -> List[Document]:
        """
        Add metadata to every document/chunk.

        Parameters:
            documents:
                LangChain Documents produced by the document loader.

            document_id:
                Optional ID supplied by the user. If omitted,
                an ID is generated from the filename.

            keywords:
                Optional user-provided keywords.

            category:
                Optional document category.

            description:
                Optional document description.
        """

        if not documents:
            return []

        keywords = keywords or []

        filename = documents[0].metadata.get(
            "filename",
            "unknown",
        )

        file_path = documents[0].metadata.get(
            "file_path",
            "",
        )

        file_type = documents[0].metadata.get(
            "file_type",
            Path(filename).suffix.lower(),
        )

        if document_id is None:
            document_id = self._generate_document_id(
                filename
            )

        clean_keywords = self._clean_keywords(
            keywords
        )

        for document in documents:

            document.metadata.update(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "file_type": file_type,
                    "file_path": file_path,
                    "keywords": clean_keywords,
                }
            )

            if category:
                document.metadata["category"] = category

            if description:
                document.metadata["description"] = description

        return documents

    @staticmethod
    def _generate_document_id(
        filename: str,
    ) -> str:
        """
        Generate a simple document ID from the filename.

        Example:
            inspection_report_BK01.pdf
            →
            inspection_report_BK01
        """

        return Path(filename).stem

    @staticmethod
    def _clean_keywords(
        keywords: List[str],
    ) -> List[str]:
        """
        Clean and deduplicate user-provided keywords.
        """

        cleaned = []

        for keyword in keywords:

            keyword = keyword.strip()

            if not keyword:
                continue

            if keyword.lower() not in {
                item.lower()
                for item in cleaned
            }:
                cleaned.append(keyword)

        return cleaned


if __name__ == "__main__":

    sample_documents = [
        Document(
            page_content=(
                "Ultrasonic thickness inspection "
                "was performed on nozzle BK-01."
            ),
            metadata={
                "filename": "inspection_report_BK01.pdf",
                "file_path": "uploads/inspection_report_BK01.pdf",
                "file_type": ".pdf",
            },
        )
    ]

    extractor = MetadataExtractor()

    documents = extractor.extract(
        documents=sample_documents,
        keywords=[
            "Inspection",
            "ASME",
            "Thickness",
            "inspection",
        ],
        category="Engineering",
    )

    print("\n--- Metadata ---")

    for document in documents:
        print(document.metadata)