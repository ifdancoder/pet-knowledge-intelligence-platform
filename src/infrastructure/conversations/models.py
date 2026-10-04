from sqlalchemy import ARRAY, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base, TimestampMixin, ULIDPrimaryKeyMixin


class ConversationModel(Base, ULIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"

    workspace_id: Mapped[str] = mapped_column(String(26), index=True)
    user_id: Mapped[str] = mapped_column(String(26), index=True)


class MessageModel(Base, ULIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    source_chunk_ids: Mapped[list[str]] = mapped_column(ARRAY(String(26)), default=list)
