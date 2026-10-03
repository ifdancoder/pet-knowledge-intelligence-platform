from domain.shared.exceptions import DomainError


class EmailAlreadyRegisteredError(DomainError):
    pass


class InvalidOrExpiredTokenError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class AccountNotActiveError(DomainError):
    pass


class RefreshTokenReuseError(DomainError):
    pass


class InvalidAccessTokenError(DomainError):
    pass


class ExpiredAccessTokenError(DomainError):
    pass
