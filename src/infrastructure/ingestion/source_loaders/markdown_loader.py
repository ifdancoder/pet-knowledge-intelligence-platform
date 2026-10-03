from domain.ingestion.entities import Source


class MarkdownSourceLoader:
    async def load(self, source: Source, file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8")
