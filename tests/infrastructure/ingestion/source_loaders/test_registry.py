import pytest

from infrastructure.ingestion.source_loaders.markdown_loader import MarkdownSourceLoader
from infrastructure.ingestion.source_loaders.pdf_loader import PdfSourceLoader
from infrastructure.ingestion.source_loaders.registry import SourceLoaderRegistry


def test_registry_dispatches_by_source_type() -> None:
    registry = SourceLoaderRegistry()
    assert isinstance(registry.get("pdf"), PdfSourceLoader)
    assert isinstance(registry.get("markdown"), MarkdownSourceLoader)


def test_registry_rejects_unknown_type() -> None:
    registry = SourceLoaderRegistry()
    with pytest.raises(KeyError):
        registry.get("csv")
