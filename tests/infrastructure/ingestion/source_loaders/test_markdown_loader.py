from pathlib import Path

from domain.ingestion.entities import Source
from infrastructure.ingestion.source_loaders.markdown_loader import MarkdownSourceLoader


async def test_markdown_loader_returns_the_file_text() -> None:
    loader = MarkdownSourceLoader()
    source = Source.create(workspace_id="w1", type="markdown", storage_key="w1/sample.md")
    file_bytes = Path("tests/fixtures/sample.md").read_bytes()

    text = await loader.load(source, file_bytes)

    assert "sample" in text
    assert "**sample**" in text
