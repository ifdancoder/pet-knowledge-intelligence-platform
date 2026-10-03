from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.ingestion.entities import Chunk, Document, Source
from infrastructure.ingestion.models import ChunkModel, DocumentModel, SourceModel


class SqlAlchemySourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, source: Source) -> None:
        model = SourceModel(
            id=source.id,
            workspace_id=source.workspace_id,
            type=source.type,
            storage_key=source.storage_key,
            status=source.status,
            error=source.error,
        )
        self._session.add(model)
        self._session.flush()

    def get_by_id(self, source_id: str) -> Source | None:
        model = self._session.execute(
            select(SourceModel).where(SourceModel.id == source_id)
        ).scalar_one_or_none()
        return _source_to_entity(model) if model is not None else None

    def update(self, source: Source) -> None:
        model = self._session.execute(
            select(SourceModel).where(SourceModel.id == source.id)
        ).scalar_one()
        model.status = source.status
        model.error = source.error
        self._session.flush()


def _source_to_entity(model: SourceModel) -> Source:
    return Source(
        id=model.id,
        workspace_id=model.workspace_id,
        type=model.type,
        storage_key=model.storage_key,
        status=model.status,
        error=model.error,
    )


class SqlAlchemyDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: Document) -> None:
        model = DocumentModel(id=document.id, source_id=document.source_id, raw_text=document.raw_text)
        self._session.add(model)
        self._session.flush()

    def get_by_source_id(self, source_id: str) -> Document | None:
        model = self._session.execute(
            select(DocumentModel).where(DocumentModel.source_id == source_id)
        ).scalar_one_or_none()
        if model is None:
            return None
        return Document(id=model.id, source_id=model.source_id, raw_text=model.raw_text)

    def update(self, document: Document) -> None:
        model = self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document.id)
        ).scalar_one()
        model.raw_text = document.raw_text
        self._session.flush()


class SqlAlchemyChunkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self._session.add(
                ChunkModel(
                    id=chunk.id,
                    source_id=chunk.source_id,
                    document_id=chunk.document_id,
                    workspace_id=chunk.workspace_id,
                    order_index=chunk.order_index,
                    text=chunk.text,
                    embedding=chunk.embedding,
                )
            )
        self._session.flush()

    def list_by_source_id(self, source_id: str) -> list[Chunk]:
        models = (
            self._session.execute(
                select(ChunkModel)
                .where(ChunkModel.source_id == source_id)
                .order_by(ChunkModel.order_index)
            )
            .scalars()
            .all()
        )
        return [
            Chunk(
                id=m.id,
                source_id=m.source_id,
                document_id=m.document_id,
                workspace_id=m.workspace_id,
                order_index=m.order_index,
                text=m.text,
                embedding=list(m.embedding) if m.embedding is not None else None,
            )
            for m in models
        ]

    def update_embeddings(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            model = self._session.execute(
                select(ChunkModel).where(ChunkModel.id == chunk.id)
            ).scalar_one()
            model.embedding = chunk.embedding
        self._session.flush()
