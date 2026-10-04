from application.conversations.command_handlers import (
    CreateConversationCommandHandler,
    SendUserMessageCommandHandler,
)
from application.conversations.commands import CreateConversationCommand, SendUserMessageCommand
from application.conversations.queries import GetConversationMessagesQuery, ListConversationsQuery
from application.conversations.query_handlers import (
    GetConversationMessagesQueryHandler,
    ListConversationsQueryHandler,
)
from domain.conversations.entities import Conversation, Message
from domain.conversations.exceptions import NotConversationOwnerError


class FakeConversationRepository:
    def __init__(self) -> None:
        self.conversations_by_id: dict[str, Conversation] = {}

    async def add(self, conversation: Conversation) -> None:
        self.conversations_by_id[conversation.id] = conversation

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        return self.conversations_by_id.get(conversation_id)

    async def list_by_workspace_and_user(self, workspace_id: str, user_id: str) -> list[Conversation]:
        return [
            c for c in self.conversations_by_id.values()
            if c.workspace_id == workspace_id and c.user_id == user_id
        ]


class FakeMessageRepository:
    def __init__(self) -> None:
        self.messages_by_conversation_id: dict[str, list[Message]] = {}

    async def add(self, message: Message) -> None:
        self.messages_by_conversation_id.setdefault(message.conversation_id, []).append(message)

    async def list_by_conversation_id(self, conversation_id: str) -> list[Message]:
        return self.messages_by_conversation_id.get(conversation_id, [])


async def test_list_conversations_returns_only_the_caller_s_own() -> None:
    conversations = FakeConversationRepository()
    create = CreateConversationCommandHandler(conversations)
    mine = await create.handle(CreateConversationCommand(workspace_id="w1", user_id="u1"))
    await create.handle(CreateConversationCommand(workspace_id="w1", user_id="u2"))

    handler = ListConversationsQueryHandler(conversations)
    result = await handler.handle(ListConversationsQuery(workspace_id="w1", user_id="u1"))

    assert [c.id for c in result] == [mine]


async def test_get_conversation_messages_returns_the_history() -> None:
    conversations = FakeConversationRepository()
    messages = FakeMessageRepository()
    create = CreateConversationCommandHandler(conversations)
    conversation_id = await create.handle(CreateConversationCommand(workspace_id="w1", user_id="u1"))
    send = SendUserMessageCommandHandler(conversations, messages)
    await send.handle(
        SendUserMessageCommand(conversation_id=conversation_id, requesting_user_id="u1", content="hello")
    )

    handler = GetConversationMessagesQueryHandler(conversations, messages)
    history = await handler.handle(
        GetConversationMessagesQuery(conversation_id=conversation_id, requesting_user_id="u1")
    )

    assert len(history) == 1
    assert history[0].content == "hello"


async def test_get_conversation_messages_rejects_a_non_owner() -> None:
    conversations = FakeConversationRepository()
    messages = FakeMessageRepository()
    create = CreateConversationCommandHandler(conversations)
    conversation_id = await create.handle(CreateConversationCommand(workspace_id="w1", user_id="u1"))

    handler = GetConversationMessagesQueryHandler(conversations, messages)
    try:
        await handler.handle(
            GetConversationMessagesQuery(conversation_id=conversation_id, requesting_user_id="u2")
        )
        raise AssertionError("expected NotConversationOwnerError")
    except NotConversationOwnerError:
        pass
