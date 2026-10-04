from collections.abc import AsyncIterator

from application.conversations.services import GenerateAssistantReplyService
from application.search.queries import SearchQuery
from domain.conversations.entities import Conversation, Message
from domain.search.entities import SearchResult


class FakeConversationRepository:
    def __init__(self, conversations: dict[str, Conversation]) -> None:
        self._conversations = conversations

    async def add(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    async def list_by_workspace_and_user(self, workspace_id: str, user_id: str) -> list[Conversation]:
        raise NotImplementedError


class FakeMessageRepository:
    def __init__(self, messages: dict[str, list[Message]]) -> None:
        self._messages = messages

    async def add(self, message: Message) -> None:
        self._messages.setdefault(message.conversation_id, []).append(message)

    async def list_by_conversation_id(self, conversation_id: str) -> list[Message]:
        return self._messages.get(conversation_id, [])


class FakeSearchHandler:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.last_query: SearchQuery | None = None

    async def handle(self, query: SearchQuery) -> list[SearchResult]:
        self.last_query = query
        return self._results


class FakeLLMProvider:
    def __init__(self, deltas: list[str]) -> None:
        self._deltas = deltas
        self.last_call: dict | None = None

    async def stream(self, *, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.last_call = {"system": system, "messages": messages}
        for delta in self._deltas:
            yield delta


class FailingLLMProvider:
    async def stream(self, *, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        yield "partial"
        raise RuntimeError("the model exploded")


async def test_stream_yields_deltas_and_persists_the_assembled_reply() -> None:
    conversation = Conversation.create(workspace_id="w1", user_id="u1")
    conversations_db: dict[str, Conversation] = {conversation.id: conversation}
    messages_db: dict[str, list[Message]] = {
        conversation.id: [Message.from_user(conversation_id=conversation.id, content="what is a chunk?")]
    }
    search_results = [SearchResult(chunk_id="ch1", source_id="s1", text="a chunk is a piece of text", score=1.0)]
    llm = FakeLLMProvider(["A chunk", " is a piece of text."])

    service = GenerateAssistantReplyService(
        FakeConversationRepository(conversations_db),
        FakeMessageRepository(messages_db),
        FakeSearchHandler(search_results),
        llm,
    )

    deltas = [d async for d in service.stream(conversation_id=conversation.id, workspace_id="w1")]

    assert deltas == ["A chunk", " is a piece of text."]
    history = messages_db[conversation.id]
    assert len(history) == 2
    assert history[1].role == "assistant"
    assert history[1].content == "A chunk is a piece of text."
    assert history[1].source_chunk_ids == ["ch1"]
    assert llm.last_call["messages"] == [{"role": "user", "content": "what is a chunk?"}]
    assert "a chunk is a piece of text" in llm.last_call["system"]


async def test_stream_propagates_an_llm_error_without_persisting() -> None:
    conversation = Conversation.create(workspace_id="w1", user_id="u1")
    conversations_db: dict[str, Conversation] = {conversation.id: conversation}
    messages_db: dict[str, list[Message]] = {
        conversation.id: [Message.from_user(conversation_id=conversation.id, content="hi")]
    }
    service = GenerateAssistantReplyService(
        FakeConversationRepository(conversations_db),
        FakeMessageRepository(messages_db),
        FakeSearchHandler([]),
        FailingLLMProvider(),
    )

    collected = []
    try:
        async for delta in service.stream(conversation_id=conversation.id, workspace_id="w1"):
            collected.append(delta)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

    assert collected == ["partial"]
    assert len(messages_db[conversation.id]) == 1  # still just the original user message
