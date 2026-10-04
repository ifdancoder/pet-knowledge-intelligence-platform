from application.conversations.queries import GetConversationMessagesQuery, ListConversationsQuery
from domain.conversations.entities import Conversation, Message
from domain.conversations.exceptions import ConversationNotFoundError, NotConversationOwnerError
from domain.conversations.ports import ConversationRepository, MessageRepository


class ListConversationsQueryHandler:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def handle(self, query: ListConversationsQuery) -> list[Conversation]:
        return await self._conversations.list_by_workspace_and_user(query.workspace_id, query.user_id)


class GetConversationMessagesQueryHandler:
    def __init__(self, conversations: ConversationRepository, messages: MessageRepository) -> None:
        self._conversations = conversations
        self._messages = messages

    async def handle(self, query: GetConversationMessagesQuery) -> list[Message]:
        conversation = await self._conversations.get_by_id(query.conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(query.conversation_id)
        if conversation.user_id != query.requesting_user_id:
            raise NotConversationOwnerError(query.conversation_id)
        return await self._messages.list_by_conversation_id(query.conversation_id)
