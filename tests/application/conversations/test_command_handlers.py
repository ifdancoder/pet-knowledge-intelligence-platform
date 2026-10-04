from application.conversations.command_handlers import (
    CreateConversationCommandHandler,
    SendUserMessageCommandHandler,
)
from application.conversations.commands import CreateConversationCommand, SendUserMessageCommand
from domain.conversations.entities import Conversation, Message
from domain.conversations.exceptions import ConversationNotFoundError, NotConversationOwnerError


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


async def test_create_conversation_returns_its_id() -> None:
    conversations = FakeConversationRepository()
    handler = CreateConversationCommandHandler(conversations)

    conversation_id = await handler.handle(CreateConversationCommand(workspace_id="w1", user_id="u1"))

    stored = await conversations.get_by_id(conversation_id)
    assert stored is not None
    assert stored.workspace_id == "w1"
    assert stored.user_id == "u1"


async def test_send_user_message_persists_it_and_returns_its_id() -> None:
    conversations = FakeConversationRepository()
    messages = FakeMessageRepository()
    create = CreateConversationCommandHandler(conversations)
    conversation_id = await create.handle(CreateConversationCommand(workspace_id="w1", user_id="u1"))

    handler = SendUserMessageCommandHandler(conversations, messages)
    message_id = await handler.handle(
        SendUserMessageCommand(conversation_id=conversation_id, requesting_user_id="u1", content="hello")
    )

    history = await messages.list_by_conversation_id(conversation_id)
    assert len(history) == 1
    assert history[0].id == message_id
    assert history[0].content == "hello"


async def test_send_user_message_rejects_unknown_conversation() -> None:
    conversations = FakeConversationRepository()
    messages = FakeMessageRepository()
    handler = SendUserMessageCommandHandler(conversations, messages)

    try:
        await handler.handle(
            SendUserMessageCommand(conversation_id="missing", requesting_user_id="u1", content="hi")
        )
        raise AssertionError("expected ConversationNotFoundError")
    except ConversationNotFoundError:
        pass


async def test_send_user_message_rejects_a_non_owner() -> None:
    conversations = FakeConversationRepository()
    messages = FakeMessageRepository()
    create = CreateConversationCommandHandler(conversations)
    conversation_id = await create.handle(CreateConversationCommand(workspace_id="w1", user_id="u1"))

    handler = SendUserMessageCommandHandler(conversations, messages)
    try:
        await handler.handle(
            SendUserMessageCommand(conversation_id=conversation_id, requesting_user_id="u2", content="hi")
        )
        raise AssertionError("expected NotConversationOwnerError")
    except NotConversationOwnerError:
        pass
