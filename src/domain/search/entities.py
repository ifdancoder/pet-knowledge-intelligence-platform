from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    source_id: str
    text: str
    score: float
