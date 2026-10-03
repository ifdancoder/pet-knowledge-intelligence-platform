import io

from pypdf import PdfReader

from domain.ingestion.entities import Source


class PdfSourceLoader:
    async def load(self, source: Source, file_bytes: bytes) -> str:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
