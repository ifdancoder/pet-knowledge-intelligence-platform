import datetime

from application.auth.command_handlers import (
    LoginCommandHandler,
    LogoutAllCommandHandler,
    LogoutCommandHandler,
    RefreshCommandHandler,
    RegisterUserCommandHandler,
    VerifyEmailCommandHandler,
)
from application.auth.commands import (
    LoginCommand,
    LogoutAllCommand,
    LogoutCommand,
    RefreshCommand,
    RegisterUserCommand,
    VerifyEmailCommand,
)
from domain.auth.entities import EmailVerificationToken, RefreshToken, User
from domain.auth.exceptions import (
    AccountNotActiveError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    RefreshTokenReuseError,
)
from infrastructure.security.tokens import generate_opaque_token


class FakeUserRepository:
    def __init__(self) -> None:
        self.users_by_id: dict[str, User] = {}

    async def add(self, user: User) -> None:
        self.users_by_id[user.id] = user

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users_by_id.values() if u.email == email), None)

    async def get_by_id(self, user_id: str) -> User | None:
        return self.users_by_id.get(user_id)

    async def update(self, user: User) -> None:
        self.users_by_id[user.id] = user


class FakeVerificationTokenRepository:
    def __init__(self) -> None:
        self.tokens_by_hash: dict[str, EmailVerificationToken] = {}

    async def add(self, token: EmailVerificationToken) -> None:
        self.tokens_by_hash[token.token_hash] = token

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        return self.tokens_by_hash.get(token_hash)

    async def update(self, token: EmailVerificationToken) -> None:
        self.tokens_by_hash[token.token_hash] = token


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens_by_hash: dict[str, RefreshToken] = {}

    async def add(self, token: RefreshToken) -> None:
        self.tokens_by_hash[token.token_hash] = token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.tokens_by_hash.get(token_hash)

    async def update(self, token: RefreshToken) -> None:
        self.tokens_by_hash[token.token_hash] = token

    async def revoke_all_for_user(self, user_id: str, now: datetime.datetime) -> None:
        for token in self.tokens_by_hash.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = now


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_verification_email(self, to: str, token: str) -> None:
        self.sent.append((to, token))


def make_handlers() -> tuple[
    RegisterUserCommandHandler,
    VerifyEmailCommandHandler,
    LoginCommandHandler,
    RefreshCommandHandler,
    LogoutCommandHandler,
    LogoutAllCommandHandler,
    FakeUserRepository,
    FakeRefreshTokenRepository,
    FakeEmailSender,
]:
    users = FakeUserRepository()
    verification_tokens = FakeVerificationTokenRepository()
    refresh_tokens = FakeRefreshTokenRepository()
    email_sender = FakeEmailSender()
    return (
        RegisterUserCommandHandler(users, verification_tokens, email_sender),
        VerifyEmailCommandHandler(users, verification_tokens),
        LoginCommandHandler(users, refresh_tokens),
        RefreshCommandHandler(refresh_tokens),
        LogoutCommandHandler(refresh_tokens),
        LogoutAllCommandHandler(refresh_tokens),
        users,
        refresh_tokens,
        email_sender,
    )


async def _registered_and_verified(
    register: RegisterUserCommandHandler,
    verify: VerifyEmailCommandHandler,
    email_sender: FakeEmailSender,
    email: str = "a@example.com",
) -> None:
    await register.handle(RegisterUserCommand(email=email, password="longenoughpassword"))
    await verify.handle(VerifyEmailCommand(token=email_sender.sent[-1][1]))


async def test_register_creates_inactive_user_and_sends_verification_email() -> None:
    register, _, _, _, _, _, users, _, email_sender = make_handlers()
    user_id = await register.handle(RegisterUserCommand(email="a@example.com", password="longenoughpassword"))
    user = await users.get_by_id(user_id)
    assert user is not None
    assert user.is_active is False
    assert len(email_sender.sent) == 1


async def test_register_rejects_duplicate_email() -> None:
    register, _, _, _, _, _, _, _, _ = make_handlers()
    await register.handle(RegisterUserCommand(email="a@example.com", password="longenoughpassword"))
    try:
        await register.handle(RegisterUserCommand(email="a@example.com", password="anotherpassword"))
        raise AssertionError("expected EmailAlreadyRegisteredError")
    except EmailAlreadyRegisteredError:
        pass


async def test_verify_email_activates_user() -> None:
    register, verify, _, _, _, _, users, _, email_sender = make_handlers()
    await register.handle(RegisterUserCommand(email="a@example.com", password="longenoughpassword"))
    raw_token = email_sender.sent[0][1]
    await verify.handle(VerifyEmailCommand(token=raw_token))
    user = await users.get_by_email("a@example.com")
    assert user is not None
    assert user.is_active is True


async def test_verify_email_rejects_unknown_token() -> None:
    _, verify, _, _, _, _, _, _, _ = make_handlers()
    try:
        await verify.handle(VerifyEmailCommand(token=generate_opaque_token()))
        raise AssertionError("expected InvalidOrExpiredTokenError")
    except InvalidOrExpiredTokenError:
        pass


async def test_verify_email_rejects_reused_token() -> None:
    register, verify, _, _, _, _, _, _, email_sender = make_handlers()
    await register.handle(RegisterUserCommand(email="a@example.com", password="longenoughpassword"))
    raw_token = email_sender.sent[0][1]
    await verify.handle(VerifyEmailCommand(token=raw_token))
    try:
        await verify.handle(VerifyEmailCommand(token=raw_token))
        raise AssertionError("expected InvalidOrExpiredTokenError")
    except InvalidOrExpiredTokenError:
        pass


async def test_login_rejects_unverified_account() -> None:
    register, _, login, _, _, _, _, _, _ = make_handlers()
    await register.handle(RegisterUserCommand(email="a@example.com", password="longenoughpassword"))
    try:
        await login.handle(LoginCommand(email="a@example.com", password="longenoughpassword"))
        raise AssertionError("expected AccountNotActiveError")
    except AccountNotActiveError:
        pass


async def test_login_rejects_wrong_password() -> None:
    register, verify, login, _, _, _, _, _, email_sender = make_handlers()
    await _registered_and_verified(register, verify, email_sender)
    try:
        await login.handle(LoginCommand(email="a@example.com", password="wrongpassword"))
        raise AssertionError("expected InvalidCredentialsError")
    except InvalidCredentialsError:
        pass


async def test_login_rejects_unknown_email() -> None:
    _, _, login, _, _, _, _, _, _ = make_handlers()
    try:
        await login.handle(LoginCommand(email="missing@example.com", password="whatever"))
        raise AssertionError("expected InvalidCredentialsError")
    except InvalidCredentialsError:
        pass


async def test_login_returns_access_and_refresh_token_for_verified_user() -> None:
    register, verify, login, _, _, _, _, _, email_sender = make_handlers()
    await _registered_and_verified(register, verify, email_sender)
    tokens = await login.handle(LoginCommand(email="a@example.com", password="longenoughpassword"))
    assert isinstance(tokens.access_token, str) and tokens.access_token
    assert isinstance(tokens.refresh_token, str) and tokens.refresh_token


async def test_refresh_rotates_token() -> None:
    register, verify, login, refresh, _, _, _, _, email_sender = make_handlers()
    await _registered_and_verified(register, verify, email_sender)
    tokens = await login.handle(LoginCommand(email="a@example.com", password="longenoughpassword"))
    new_tokens = await refresh.handle(RefreshCommand(refresh_token=tokens.refresh_token))
    assert new_tokens.refresh_token != tokens.refresh_token


async def test_refresh_rejects_reused_token_and_revokes_chain() -> None:
    register, verify, login, refresh, _, _, _, _, email_sender = make_handlers()
    await _registered_and_verified(register, verify, email_sender)
    tokens = await login.handle(LoginCommand(email="a@example.com", password="longenoughpassword"))
    new_tokens = await refresh.handle(RefreshCommand(refresh_token=tokens.refresh_token))

    try:
        await refresh.handle(RefreshCommand(refresh_token=tokens.refresh_token))
        raise AssertionError("expected RefreshTokenReuseError")
    except RefreshTokenReuseError:
        pass

    try:
        await refresh.handle(RefreshCommand(refresh_token=new_tokens.refresh_token))
        raise AssertionError("expected RefreshTokenReuseError")
    except RefreshTokenReuseError:
        pass


async def test_logout_revokes_only_that_token() -> None:
    register, verify, login, refresh, logout, _, _, _, email_sender = make_handlers()
    await _registered_and_verified(register, verify, email_sender)
    tokens = await login.handle(LoginCommand(email="a@example.com", password="longenoughpassword"))
    await logout.handle(LogoutCommand(refresh_token=tokens.refresh_token))
    try:
        await refresh.handle(RefreshCommand(refresh_token=tokens.refresh_token))
        raise AssertionError("expected RefreshTokenReuseError")
    except RefreshTokenReuseError:
        pass


async def test_logout_all_revokes_every_token_for_user() -> None:
    register, verify, login, refresh, _, logout_all, users, _, email_sender = make_handlers()
    await _registered_and_verified(register, verify, email_sender)
    user = await users.get_by_email("a@example.com")
    assert user is not None
    first = await login.handle(LoginCommand(email="a@example.com", password="longenoughpassword"))
    second = await login.handle(LoginCommand(email="a@example.com", password="longenoughpassword"))
    await logout_all.handle(LogoutAllCommand(user_id=user.id))
    for tokens in (first, second):
        try:
            await refresh.handle(RefreshCommand(refresh_token=tokens.refresh_token))
            raise AssertionError("expected RefreshTokenReuseError")
        except RefreshTokenReuseError:
            pass
