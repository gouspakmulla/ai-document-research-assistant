from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    filename: str
    file_size_bytes: int
    mime_type: str
    page_count: int
    processing_status: str
    error_message: str | None = None
    checksum_sha256: str | None = None
    created_at: datetime
    updated_at: datetime

class DocumentRenameRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)

class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    page_number: int
    content: str
    token_count: int
    created_at: datetime
