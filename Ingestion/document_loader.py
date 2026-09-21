from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
    UnstructuredExcelLoader,
)


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".csv",
    ".xlsx",
    ".xls",
}


def load_document(file_path: str) -> List[Document]:
    """
    Load a document from the local filesystem using LangChain
    document loaders.

    No external API or cloud service is used.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Document not found: {file_path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Path is not a file: {file_path}"
        )

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    # Select the appropriate local LangChain loader.
    if extension == ".pdf":
        loader = PyPDFLoader(str(path))

    elif extension == ".docx":
        loader = Docx2txtLoader(str(path))

    elif extension == ".txt":
        loader = TextLoader(
            str(path),
            encoding="utf-8",
        )

    elif extension == ".csv":
        loader = CSVLoader(str(path))

    elif extension in {".xlsx", ".xls"}:
        loader = UnstructuredExcelLoader(str(path))

    else:
        raise ValueError(
            f"No loader available for: {extension}"
        )

    documents = loader.load()

    if not documents:
        raise ValueError(
            f"No content could be extracted from: {path.name}"
        )

    # Add common metadata to every LangChain Document.
    for document in documents:
        document.metadata.update(
            {
                "filename": path.name,
                "file_path": str(path),
                "file_type": extension,
            }
        )

    return documents