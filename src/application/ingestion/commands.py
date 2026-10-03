from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractDocumentCommand:
    source_id: str


@dataclass(frozen=True)
class NormalizeDocumentCommand:
    source_id: str


@dataclass(frozen=True)
class SplitIntoChunksCommand:
    source_id: str


@dataclass(frozen=True)
class GenerateEmbeddingsCommand:
    source_id: str


@dataclass(frozen=True)
class IndexChunksCommand:
    source_id: str


@dataclass(frozen=True)
class UploadSourceCommand:
    workspace_id: str
    type: str
    filename: str
    file_bytes: bytes
