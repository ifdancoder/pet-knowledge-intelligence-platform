from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base, TimestampMixin, ULIDPrimaryKeyMixin


class SourceModel(Base, ULIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sources"

    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    type: Mapped[str] = mapped_column(String(20))
    storage_key: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    error: Mapped[str | None] = mapped_column(Text, default=None)


class DocumentModel(Base, ULIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    raw_text: Mapped[str] = mapped_column(Text)


class ChunkModel(Base, ULIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chunks"

    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
