from __future__ import annotations

from dataclasses import dataclass, field

from shared.ids import generate_id


@dataclass
class Conversation:
    id: str
    workspace_id: str
    user_id: str

    @classmethod
    def create(cls, *, workspace_id: str, user_id: str) -> Conversation:
        return cls(id=generate_id(), workspace_id=workspace_id, user_id=user_id)


@dataclass
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    source_chunk_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_user(cls, *, conversation_id: str, content: str) -> Message:
        return cls(id=generate_id(), conversation_id=conversation_id, role="user", content=content)

    @classmethod
    def from_assistant(cls, *, conversation_id: str, content: str, source_chunk_ids: list[str]) -> Message:
        return cls(
            id=generate_id(), conversation_id=conversation_id, role="assistant",
            content=content, source_chunk_ids=source_chunk_ids,
        )
