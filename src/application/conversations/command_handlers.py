from application.conversations.commands import CreateConversationCommand, SendUserMessageCommand
from domain.conversations.entities import Conversation, Message
from domain.conversations.exceptions import ConversationNotFoundError, NotConversationOwnerError
from domain.conversations.ports import ConversationRepository, MessageRepository


class CreateConversationCommandHandler:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def handle(self, command: CreateConversationCommand) -> str:
        conversation = Conversation.create(workspace_id=command.workspace_id, user_id=command.user_id)
        await self._conversations.add(conversation)
        return conversation.id


class SendUserMessageCommandHandler:
    def __init__(self, conversations: ConversationRepository, messages: MessageRepository) -> None:
        self._conversations = conversations
        self._messages = messages

    async def handle(self, command: SendUserMessageCommand) -> str:
        conversation = await self._conversations.get_by_id(command.conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(command.conversation_id)
        if conversation.user_id != command.requesting_user_id:
            raise NotConversationOwnerError(command.conversation_id)

        message = Message.from_user(conversation_id=command.conversation_id, content=command.content)
        await self._messages.add(message)
        return message.id
