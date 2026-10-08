from collections.abc import AsyncIterator

from application.search.queries import SearchQuery
from application.search.query_handlers import RerankingSearchQueryHandler
from domain.conversations.entities import Message
from domain.conversations.ports import ConversationRepository, LLMProvider, MessageRepository

_SYSTEM_PROMPT = (
    "You are a helpful assistant for a personal knowledge base. Answer the user's "
    "question using only the information in the provided context below. If the "
    "context does not contain enough information to answer, say so clearly instead "
    "of guessing."
)
_RETRIEVAL_LIMIT = 5


class GenerateAssistantReplyService:
    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        search: RerankingSearchQueryHandler,
        llm: LLMProvider,
    ) -> None:
        self._conversations = conversations
        self._messages = messages
        self._search = search
        self._llm = llm

    async def stream(self, *, conversation_id: str, workspace_id: str) -> AsyncIterator[str]:
        history = await self._messages.list_by_conversation_id(conversation_id)
        latest_question = history[-1].content

        results = await self._search.handle(
            SearchQuery(
                query=latest_question, workspace_id=workspace_id, source_type=None, limit=_RETRIEVAL_LIMIT
            )
        )
        context_block = "\n\n".join(r.text for r in results)
        system = f"{_SYSTEM_PROMPT}\n\nContext:\n{context_block}"
        llm_messages = [{"role": m.role, "content": m.content} for m in history]

        chunks: list[str] = []
        async for delta in self._llm.stream(system=system, messages=llm_messages):
            chunks.append(delta)
            yield delta

        assistant_message = Message.from_assistant(
            conversation_id=conversation_id,
            content="".join(chunks),
            source_chunk_ids=[r.chunk_id for r in results],
        )
        await self._messages.add(assistant_message)
