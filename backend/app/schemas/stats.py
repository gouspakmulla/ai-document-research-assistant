from pydantic import BaseModel

class DashboardStatsResponse(BaseModel):
    total_documents: int = 0
    total_collections: int = 0
    total_conversations: int = 0
    total_pages_indexed: int = 0
