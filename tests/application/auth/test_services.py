import datetime

from application.auth.services import AuthService
from domain.auth.entities import EmailVerificationToken, RefreshToken, User
from domain.auth.exceptions import (
    AccountNotActiveError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    RefreshTokenReuseError,
)
from infrastructure.security.tokens import generate_opaque_token, hash_opaque_token


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


def make_service() -> tuple[AuthService, FakeUserRepository, FakeVerificationTokenRepository, FakeEmailSender]:
    users = FakeUserRepository()
    verification_tokens = FakeVerificationTokenRepository()
    refresh_tokens = FakeRefreshTokenRepository()
    email_sender = FakeEmailSender()
    service = AuthService(users, verification_tokens, refresh_tokens, email_sender)
    return service, users, verification_tokens, email_sender


async def _registered_and_verified(
    service: AuthService, email_sender: FakeEmailSender, email: str = "a@example.com"
) -> None:
    await service.register(email=email, password="longenoughpassword")
    await service.verify_email(token=email_sender.sent[-1][1])


async def test_register_creates_inactive_user_and_sends_verification_email() -> None:
    service, users, verification_tokens, email_sender = make_service()
    user_id = await service.register(email="a@example.com", password="longenoughpassword")
    user = await users.get_by_id(user_id)
    assert user is not None
    assert user.is_active is False
    assert len(email_sender.sent) == 1
    sent_token = email_sender.sent[0][1]
    assert hash_opaque_token(sent_token) in verification_tokens.tokens_by_hash


async def test_register_rejects_duplicate_email() -> None:
    service, _, _, _ = make_service()
    await service.register(email="a@example.com", password="longenoughpassword")
    try:
        await service.register(email="a@example.com", password="anotherpassword")
        raise AssertionError("expected EmailAlreadyRegisteredError")
    except EmailAlreadyRegisteredError:
        pass


async def test_verify_email_activates_user() -> None:
    service, users, _, email_sender = make_service()
    await service.register(email="a@example.com", password="longenoughpassword")
    raw_token = email_sender.sent[0][1]
    await service.verify_email(token=raw_token)
    user = await users.get_by_email("a@example.com")
    assert user is not None
    assert user.is_active is True


async def test_verify_email_rejects_unknown_token() -> None:
    service, _, _, _ = make_service()
    try:
        await service.verify_email(token=generate_opaque_token())
        raise AssertionError("expected InvalidOrExpiredTokenError")
    except InvalidOrExpiredTokenError:
        pass


async def test_verify_email_rejects_reused_token() -> None:
    service, _, _, email_sender = make_service()
    await service.register(email="a@example.com", password="longenoughpassword")
    raw_token = email_sender.sent[0][1]
    await service.verify_email(token=raw_token)
    try:
        await service.verify_email(token=raw_token)
        raise AssertionError("expected InvalidOrExpiredTokenError")
    except InvalidOrExpiredTokenError:
        pass


async def test_login_rejects_unverified_account() -> None:
    service, _, _, _ = make_service()
    await service.register(email="a@example.com", password="longenoughpassword")
    try:
        await service.login(email="a@example.com", password="longenoughpassword")
        raise AssertionError("expected AccountNotActiveError")
    except AccountNotActiveError:
        pass


async def test_login_rejects_wrong_password() -> None:
    service, _, _, email_sender = make_service()
    await _registered_and_verified(service, email_sender)
    try:
        await service.login(email="a@example.com", password="wrongpassword")
        raise AssertionError("expected InvalidCredentialsError")
    except InvalidCredentialsError:
        pass


async def test_login_rejects_unknown_email() -> None:
    service, _, _, _ = make_service()
    try:
        await service.login(email="missing@example.com", password="whatever")
        raise AssertionError("expected InvalidCredentialsError")
    except InvalidCredentialsError:
        pass


async def test_login_returns_access_and_refresh_token_for_verified_user() -> None:
    service, _, _, email_sender = make_service()
    await _registered_and_verified(service, email_sender)
    access_token, refresh_token = await service.login(email="a@example.com", password="longenoughpassword")
    assert isinstance(access_token, str) and access_token
    assert isinstance(refresh_token, str) and refresh_token


async def test_refresh_rotates_token() -> None:
    service, _, _, email_sender = make_service()
    await _registered_and_verified(service, email_sender)
    _, refresh_token = await service.login(email="a@example.com", password="longenoughpassword")
    _, new_refresh_token = await service.refresh(refresh_token=refresh_token)
    assert new_refresh_token != refresh_token


async def test_refresh_rejects_reused_token_and_revokes_chain() -> None:
    service, _, _, email_sender = make_service()
    await _registered_and_verified(service, email_sender)
    _, old_refresh_token = await service.login(email="a@example.com", password="longenoughpassword")
    _, new_refresh_token = await service.refresh(refresh_token=old_refresh_token)

    try:
        await service.refresh(refresh_token=old_refresh_token)
        raise AssertionError("expected RefreshTokenReuseError")
    except RefreshTokenReuseError:
        pass

    try:
        await service.refresh(refresh_token=new_refresh_token)
        raise AssertionError("expected RefreshTokenReuseError")
    except RefreshTokenReuseError:
        pass


async def test_logout_revokes_only_that_token() -> None:
    service, _, _, email_sender = make_service()
    await _registered_and_verified(service, email_sender)
    _, refresh_token = await service.login(email="a@example.com", password="longenoughpassword")
    await service.logout(refresh_token=refresh_token)
    try:
        await service.refresh(refresh_token=refresh_token)
        raise AssertionError("expected RefreshTokenReuseError")
    except RefreshTokenReuseError:
        pass


async def test_logout_all_revokes_every_token_for_user() -> None:
    service, users, _, email_sender = make_service()
    await _registered_and_verified(service, email_sender)
    user = await users.get_by_email("a@example.com")
    assert user is not None
    _, first_token = await service.login(email="a@example.com", password="longenoughpassword")
    _, second_token = await service.login(email="a@example.com", password="longenoughpassword")
    await service.logout_all(user_id=user.id)
    for token in (first_token, second_token):
        try:
            await service.refresh(refresh_token=token)
            raise AssertionError("expected RefreshTokenReuseError")
        except RefreshTokenReuseError:
            pass
