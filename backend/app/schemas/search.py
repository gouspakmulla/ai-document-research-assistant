from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    document_id: Optional[str] = None
    collection_id: Optional[str] = None
    top_k: Optional[int] = Field(None, ge=1, le=50)
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    filename: str
    chunk_id: str
    page_number: int
    snippet: str
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
