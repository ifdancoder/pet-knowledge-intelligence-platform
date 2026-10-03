from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterUserCommand:
    email: str
    password: str


@dataclass(frozen=True)
class VerifyEmailCommand:
    token: str


@dataclass(frozen=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True)
class RefreshCommand:
    refresh_token: str


@dataclass(frozen=True)
class LogoutCommand:
    refresh_token: str


@dataclass(frozen=True)
class LogoutAllCommand:
    user_id: str


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
