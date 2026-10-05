import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.conversations.entities import Conversation, Message
from infrastructure.conversations.async_repository import (
    SqlAlchemyAsyncConversationRepository,
    SqlAlchemyAsyncMessageRepository,
)

pytestmark = pytest.mark.integration

async def test_conversation_repository_add_get_and_list(db_session: AsyncSession) -> None:
    repo = SqlAlchemyAsyncConversationRepository(db_session)
    conversation = Conversation.create(workspace_id="w1", user_id="u1")
    await repo.add(conversation)

    fetched = await repo.get_by_id(conversation.id)
    assert fetched == conversation
    assert await repo.get_by_id("missing") is None

    other_user = Conversation.create(workspace_id="w1", user_id="u2")
    await repo.add(other_user)
    mine = await repo.list_by_workspace_and_user("w1", "u1")
    assert [c.id for c in mine] == [conversation.id]


async def test_message_repository_add_and_list_in_order(db_session: AsyncSession) -> None:
    conversations = SqlAlchemyAsyncConversationRepository(db_session)
    conversation = Conversation.create(workspace_id="w1", user_id="u1")
    await conversations.add(conversation)

    messages = SqlAlchemyAsyncMessageRepository(db_session)
    first = Message.from_user(conversation_id=conversation.id, content="hello")
    await messages.add(first)
    second = Message.from_assistant(
        conversation_id=conversation.id, content="hi there", source_chunk_ids=["ch1"]
    )
    await messages.add(second)

    history = await messages.list_by_conversation_id(conversation.id)
    assert [m.id for m in history] == [first.id, second.id]
    assert history[1].source_chunk_ids == ["ch1"]
