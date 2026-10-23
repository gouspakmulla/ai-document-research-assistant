from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    document_id: str
    chunk_id: Optional[str] = None
    document_name: str
    page_number: int
    snippet: str
    relevance_score: float
    created_at: datetime

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    citations: List[CitationResponse] = []

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    collection_id: Optional[str] = None
    collection_name: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

class ConversationCreateRequest(BaseModel):
    title: str = Field("New Research Inquiry", max_length=255)
    collection_id: Optional[str] = None

class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=4000)
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    collection_id: Optional[str] = None

class AskQuestionResponse(BaseModel):
    conversation_id: str
    user_message: MessageResponse
    assistant_message: MessageResponse
