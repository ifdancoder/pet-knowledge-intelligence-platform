from prometheus_client import Histogram

ingestion_stage_duration_seconds = Histogram(
    "ingestion_stage_duration_seconds",
    "Duration of each ingestion pipeline stage",
    ["stage"],
)

rag_generation_duration_seconds = Histogram(
    "rag_generation_duration_seconds",
    "Duration of RAG reply generation (retrieval plus LLM streaming)",
)
