from domain.shared.exceptions import DomainError


class ConversationNotFoundError(DomainError):
    pass


class NotConversationOwnerError(DomainError):
    pass
