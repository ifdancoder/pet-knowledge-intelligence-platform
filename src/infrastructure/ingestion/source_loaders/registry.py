from domain.ingestion.ports import SourceLoader
from infrastructure.ingestion.source_loaders.markdown_loader import MarkdownSourceLoader
from infrastructure.ingestion.source_loaders.pdf_loader import PdfSourceLoader


class SourceLoaderRegistry:
    def __init__(self) -> None:
        self._loaders: dict[str, SourceLoader] = {
            "pdf": PdfSourceLoader(),
            "markdown": MarkdownSourceLoader(),
        }

    def get(self, source_type: str) -> SourceLoader:
        return self._loaders[source_type]
