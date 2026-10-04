from dataclasses import dataclass


@dataclass(frozen=True)
class SearchQuery:
    query: str
    workspace_id: str
    source_type: str | None
    limit: int
