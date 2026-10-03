from domain.shared.exceptions import DomainError


class InvalidStatusTransitionError(DomainError):
    pass


class SourceNotFoundError(DomainError):
    pass
