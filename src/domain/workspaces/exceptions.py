from domain.shared.exceptions import DomainError


class WorkspaceNotFoundError(DomainError):
    pass


class MemberNotFoundError(DomainError):
    pass


class LastOwnerError(DomainError):
    pass


class NotAWorkspaceMemberError(DomainError):
    pass


class InsufficientPermissionError(DomainError):
    pass
