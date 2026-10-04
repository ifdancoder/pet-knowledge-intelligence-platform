from pydantic import BaseModel


class SearchResultResponse(BaseModel):
    chunk_id: str
    source_id: str
    text: str
    score: float
