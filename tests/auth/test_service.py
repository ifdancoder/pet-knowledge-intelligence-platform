import datetime

from app.auth.email_sender import EmailSender
from app.auth.models import EmailVerificationToken, RefreshToken, User
from app.auth.security import generate_opaque_token, hash_opaque_token
from app.auth.service import (
    AccountNotActiveError,
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
    RefreshTokenReuseError,
)


class FakeUserRepository:
    def __init__(self) -> None:
        self.users_by_id: dict[str, User] = {}
        self._next_id = 0

    async def create(self, *, email: str, hashed_password: str) -> User:
        self._next_id += 1
        user = User(id=str(self._next_id), email=email, hashed_password=hashed_password, is_active=False)
        self.users_by_id[user.id] = user
        return user

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users_by_id.values() if u.email == email), None)

    async def get_by_id(self, user_id: str) -> User | None:
        return self.users_by_id.get(user_id)

    async def activate(self, user: User) -> None:
        user.is_active = True


class FakeVerificationTokenRepository:
    def __init__(self) -> None:
        self.tokens_by_hash: dict[str, EmailVerificationToken] = {}
        self._next_id = 0

    async def create(
        self, *, user_id: str, token_hash: str, expires_at: datetime.datetime
    ) -> EmailVerificationToken:
        self._next_id += 1
        token = EmailVerificationToken(
            id=str(self._next_id), user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.tokens_by_hash[token_hash] = token
        return token

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        return self.tokens_by_hash.get(token_hash)

    async def mark_used(self, token: EmailVerificationToken) -> None:
        token.used_at = datetime.datetime.now(datetime.UTC)


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens_by_hash: dict[str, RefreshToken] = {}
        self._next_id = 0

    async def create(
        self, *, user_id: str, token_hash: str, expires_at: datetime.datetime
    ) -> RefreshToken:
        self._next_id += 1
        token = RefreshToken(
            id=str(self._next_id), user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.tokens_by_hash[token_hash] = token
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.tokens_by_hash.get(token_hash)

    async def revoke(self, token: RefreshToken, *, replaced_by_id: str | None = None) -> None:
        token.revoked_at = datetime.datetime.now(datetime.UTC)
        token.replaced_by_id = replaced_by_id

    async def revoke_all_for_user(self, user_id: str) -> None:
        for token in self.tokens_by_hash.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = datetime.datetime.now(datetime.UTC)


class FakeEmailSender(EmailSender):
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


async def test_register_creates_inactive_user_and_sends_verification_email() -> None:
    service, users, verification_tokens, email_sender = make_service()

    user_id = await service.register(email="a@example.com", password="longenoughpassword")

    user = await users.get_by_id(user_id)
    assert user is not None
    assert user.is_active is False
    assert len(email_sender.sent) == 1
    assert email_sender.sent[0][0] == "a@example.com"
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
    service, users, verification_tokens, email_sender = make_service()
    await service.register(email="a@example.com", password="longenoughpassword")
    raw_token = email_sender.sent[0][1]

    await service.verify_email(token=raw_token)

    user = await users.get_by_email("a@example.com")
    assert user is not None
    assert user.is_active is True
    record = await verification_tokens.get_by_hash(hash_opaque_token(raw_token))
    assert record is not None
    assert record.used_at is not None


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
    await service.register(email="a@example.com", password="longenoughpassword")
    await service.verify_email(token=email_sender.sent[0][1])
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
    await service.register(email="a@example.com", password="longenoughpassword")
    await service.verify_email(token=email_sender.sent[0][1])

    access_token, refresh_token = await service.login(email="a@example.com", password="longenoughpassword")

    assert isinstance(access_token, str) and access_token
    assert isinstance(refresh_token, str) and refresh_token


async def _registered_and_verified(
    service: AuthService, email_sender: FakeEmailSender, email: str = "a@example.com"
) -> None:
    await service.register(email=email, password="longenoughpassword")
    await service.verify_email(token=email_sender.sent[-1][1])


async def test_refresh_rotates_token() -> None:
    service, _, _, email_sender = make_service()
    await _registered_and_verified(service, email_sender)
    _, refresh_token = await service.login(email="a@example.com", password="longenoughpassword")

    new_access_token, new_refresh_token = await service.refresh(refresh_token=refresh_token)

    assert new_refresh_token != refresh_token
    assert isinstance(new_access_token, str) and new_access_token


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
    _, first_refresh_token = await service.login(email="a@example.com", password="longenoughpassword")
    _, second_refresh_token = await service.login(email="a@example.com", password="longenoughpassword")

    await service.logout_all(user_id=user.id)

    for token in (first_refresh_token, second_refresh_token):
        try:
            await service.refresh(refresh_token=token)
            raise AssertionError("expected RefreshTokenReuseError")
        except RefreshTokenReuseError:
            pass
