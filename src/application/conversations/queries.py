from dataclasses import dataclass


@dataclass(frozen=True)
class ListConversationsQuery:
    workspace_id: str
    user_id: str


@dataclass(frozen=True)
class GetConversationMessagesQuery:
    conversation_id: str
    requesting_user_id: str
