from pydantic import BaseModel
from typing import Optional


class FileIOResult(BaseModel):
    status: str
    action: str
    file_path: str
    content: Optional[str] = None
    bytes_written: Optional[int] = None
    error: Optional[str] = None
