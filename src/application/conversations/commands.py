from dataclasses import dataclass


@dataclass(frozen=True)
class CreateConversationCommand:
    workspace_id: str
    user_id: str


@dataclass(frozen=True)
class SendUserMessageCommand:
    conversation_id: str
    requesting_user_id: str
    content: str
