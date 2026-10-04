from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    source_chunk_ids: list[str]


class SendMessageRequest(BaseModel):
    content: str
