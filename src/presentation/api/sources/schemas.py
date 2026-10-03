from pydantic import BaseModel


class SourceResponse(BaseModel):
    source_id: str
    status: str
    error: str | None = None
