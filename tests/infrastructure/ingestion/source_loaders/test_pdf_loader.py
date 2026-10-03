from pathlib import Path

from domain.ingestion.entities import Source
from infrastructure.ingestion.source_loaders.pdf_loader import PdfSourceLoader


async def test_pdf_loader_returns_a_string() -> None:
    loader = PdfSourceLoader()
    source = Source.create(workspace_id="w1", type="pdf", storage_key="w1/sample.pdf")
    file_bytes = Path("tests/fixtures/sample.pdf").read_bytes()

    text = await loader.load(source, file_bytes)

    assert isinstance(text, str)
