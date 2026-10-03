import datetime

from application.auth.commands import (
    LoginCommand,
    LogoutAllCommand,
    LogoutCommand,
    RefreshCommand,
    RegisterUserCommand,
    TokenPair,
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
from domain.auth.ports import (
    EmailSender,
    EmailVerificationTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from infrastructure.security.tokens import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)

VERIFICATION_TOKEN_TTL = datetime.timedelta(hours=24)
REFRESH_TOKEN_TTL = datetime.timedelta(days=30)


class RegisterUserCommandHandler:
    def __init__(
        self,
        users: UserRepository,
        verification_tokens: EmailVerificationTokenRepository,
        email_sender: EmailSender,
    ) -> None:
        self._users = users
        self._verification_tokens = verification_tokens
        self._email_sender = email_sender

    async def handle(self, command: RegisterUserCommand) -> str:
        if await self._users.get_by_email(command.email) is not None:
            raise EmailAlreadyRegisteredError(f"{command.email} is already registered")

        user = User.register(email=command.email, hashed_password=hash_password(command.password))
        await self._users.add(user)

        raw_token = generate_opaque_token()
        now = datetime.datetime.now(datetime.UTC)
        token = EmailVerificationToken.issue(
            user_id=user.id, token_hash=hash_opaque_token(raw_token), ttl=VERIFICATION_TOKEN_TTL, now=now
        )
        await self._verification_tokens.add(token)
        await self._email_sender.send_verification_email(to=command.email, token=raw_token)
        return user.id


class VerifyEmailCommandHandler:
    def __init__(
        self, users: UserRepository, verification_tokens: EmailVerificationTokenRepository
    ) -> None:
        self._users = users
        self._verification_tokens = verification_tokens

    async def handle(self, command: VerifyEmailCommand) -> None:
        now = datetime.datetime.now(datetime.UTC)
        record = await self._verification_tokens.get_by_hash(hash_opaque_token(command.token))
        if record is None or not record.is_valid(now):
            raise InvalidOrExpiredTokenError("verification token is invalid or expired")

        user = await self._users.get_by_id(record.user_id)
        assert user is not None
        user.activate()
        await self._users.update(user)

        record.mark_used(now)
        await self._verification_tokens.update(record)


class LoginCommandHandler:
    def __init__(self, users: UserRepository, refresh_tokens: RefreshTokenRepository) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens

    async def handle(self, command: LoginCommand) -> TokenPair:
        user = await self._users.get_by_email(command.email)
        if user is None or not verify_password(command.password, user.hashed_password):
            raise InvalidCredentialsError("invalid email or password")
        if not user.is_active:
            raise AccountNotActiveError("account is not verified")

        access_token = create_access_token(user_id=user.id)
        raw_refresh_token = generate_opaque_token()
        now = datetime.datetime.now(datetime.UTC)
        refresh_token = RefreshToken.issue(
            user_id=user.id, token_hash=hash_opaque_token(raw_refresh_token), ttl=REFRESH_TOKEN_TTL, now=now
        )
        await self._refresh_tokens.add(refresh_token)
        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)


class RefreshCommandHandler:
    def __init__(self, refresh_tokens: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_tokens

    async def handle(self, command: RefreshCommand) -> TokenPair:
        now = datetime.datetime.now(datetime.UTC)
        record = await self._refresh_tokens.get_by_hash(hash_opaque_token(command.refresh_token))
        if record is None:
            raise InvalidOrExpiredTokenError("refresh token is invalid")
        if record.revoked_at is not None:
            await self._refresh_tokens.revoke_all_for_user(record.user_id, now)
            raise RefreshTokenReuseError("refresh token reuse detected")
        if not record.is_usable(now):
            raise InvalidOrExpiredTokenError("refresh token has expired")

        access_token = create_access_token(user_id=record.user_id)
        raw_new_refresh_token = generate_opaque_token()
        new_record = RefreshToken.issue(
            user_id=record.user_id,
            token_hash=hash_opaque_token(raw_new_refresh_token),
            ttl=REFRESH_TOKEN_TTL,
            now=now,
        )
        await self._refresh_tokens.add(new_record)

        record.revoke(now, replaced_by_id=new_record.id)
        await self._refresh_tokens.update(record)
        return TokenPair(access_token=access_token, refresh_token=raw_new_refresh_token)


class LogoutCommandHandler:
    def __init__(self, refresh_tokens: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_tokens

    async def handle(self, command: LogoutCommand) -> None:
        record = await self._refresh_tokens.get_by_hash(hash_opaque_token(command.refresh_token))
        if record is not None and record.revoked_at is None:
            record.revoke(datetime.datetime.now(datetime.UTC))
            await self._refresh_tokens.update(record)


class LogoutAllCommandHandler:
    def __init__(self, refresh_tokens: RefreshTokenRepository) -> None:
        self._refresh_tokens = refresh_tokens

    async def handle(self, command: LogoutAllCommand) -> None:
        await self._refresh_tokens.revoke_all_for_user(
            command.user_id, datetime.datetime.now(datetime.UTC)
        )
