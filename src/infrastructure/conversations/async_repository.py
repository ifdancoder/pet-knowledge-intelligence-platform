from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.conversations.entities import Conversation, Message
from infrastructure.conversations.models import ConversationModel, MessageModel


class SqlAlchemyAsyncConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> None:
        self._session.add(
            ConversationModel(
                id=conversation.id, workspace_id=conversation.workspace_id, user_id=conversation.user_id
            )
        )
        await self._session.flush()

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        result = await self._session.execute(
            select(ConversationModel).where(ConversationModel.id == conversation_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return Conversation(id=model.id, workspace_id=model.workspace_id, user_id=model.user_id)

    async def list_by_workspace_and_user(self, workspace_id: str, user_id: str) -> list[Conversation]:
        result = await self._session.execute(
            select(ConversationModel)
            .where(ConversationModel.workspace_id == workspace_id, ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at)
        )
        return [
            Conversation(id=m.id, workspace_id=m.workspace_id, user_id=m.user_id)
            for m in result.scalars().all()
        ]


class SqlAlchemyAsyncMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: Message) -> None:
        self._session.add(
            MessageModel(
                id=message.id, conversation_id=message.conversation_id, role=message.role,
                content=message.content, source_chunk_ids=message.source_chunk_ids,
            )
        )
        await self._session.flush()

    async def list_by_conversation_id(self, conversation_id: str) -> list[Message]:
        result = await self._session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at)
        )
        return [
            Message(
                id=m.id, conversation_id=m.conversation_id, role=m.role,
                content=m.content, source_chunk_ids=list(m.source_chunk_ids),
            )
            for m in result.scalars().all()
        ]
