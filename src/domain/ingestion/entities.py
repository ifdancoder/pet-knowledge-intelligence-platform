from __future__ import annotations

from dataclasses import dataclass

from domain.ingestion.exceptions import InvalidStatusTransitionError
from shared.ids import generate_id

_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"extracting"},
    "extracting": {"normalizing"},
    "normalizing": {"chunking"},
    "chunking": {"embedding"},
    "embedding": {"indexing"},
    "indexing": {"indexed"},
    "indexed": set(),
    "failed": set(),
}


@dataclass
class Source:
    id: str
    workspace_id: str
    type: str
    storage_key: str
    status: str = "queued"
    error: str | None = None

    @classmethod
    def create(cls, *, workspace_id: str, type: str, storage_key: str) -> Source:
        return cls(id=generate_id(), workspace_id=workspace_id, type=type, storage_key=storage_key)

    def _transition_to(self, new_status: str) -> None:
        if new_status not in _TRANSITIONS.get(self.status, set()):
            raise InvalidStatusTransitionError(f"cannot move from {self.status!r} to {new_status!r}")
        self.status = new_status

    def mark_extracting(self) -> None:
        self._transition_to("extracting")

    def mark_normalizing(self) -> None:
        self._transition_to("normalizing")

    def mark_chunking(self) -> None:
        self._transition_to("chunking")

    def mark_embedding(self) -> None:
        self._transition_to("embedding")

    def mark_indexing(self) -> None:
        self._transition_to("indexing")

    def mark_indexed(self) -> None:
        self._transition_to("indexed")

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = error


@dataclass
class Document:
    id: str
    source_id: str
    raw_text: str


@dataclass
class Chunk:
    id: str
    source_id: str
    document_id: str
    workspace_id: str
    order_index: int
    text: str
    embedding: list[float] | None = None
