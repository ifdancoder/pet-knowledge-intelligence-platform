from dataclasses import dataclass


@dataclass(frozen=True)
class GetSourceStatusQuery:
    source_id: str
