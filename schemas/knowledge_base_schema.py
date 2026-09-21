from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any 

class KnowledgeBaseDocumentInput(BaseModel):
    """Input receives for the knowledge base document."""
    file_path: str = Field(description= "path for the file to upload in the knowledge base")
    document_id: Optional[str] = Field(description= "document id for the knowledge base document")
    keywords: Optional[List[str]] = Field(description= "keywords for the knowledge base document")
    category: Optional[str] = Field(description= "additional category for the document")
    description: Optional[str] = Field(description= "optional description by the user")

class KnowledgeBaseDocumentOutput(BaseModel):
    """output for the knowledge base document."""
    document_id: str = Field(description= "document id of knowledge base.")
    filename: str = Field(description= "filename of the uploaded document")
    chunk_created: int = Field(..., ge= 0, description= "number of chunks created for the document")
    vector_created: int = Field(..., ge= 0, description= "number of vectors created for the document")
    collection_name: str = Field(description= "collection name for the document")
    keywords: List[str] = Field(default_factory=list)
    auto_extracted_keywords: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str
    
