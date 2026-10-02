import datetime

from app.auth.email_sender import EmailSender
from app.auth.repository import (
    EmailVerificationTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.auth.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.shared.exceptions import AppError

VERIFICATION_TOKEN_TTL = datetime.timedelta(hours=24)
REFRESH_TOKEN_TTL = datetime.timedelta(days=30)


class EmailAlreadyRegisteredError(AppError):
    code = "email_already_registered"
    status_code = 409


class InvalidOrExpiredTokenError(AppError):
    code = "invalid_or_expired_token"
    status_code = 400


class InvalidCredentialsError(AppError):
    code = "invalid_credentials"
    status_code = 401


class AccountNotActiveError(AppError):
    code = "account_not_active"
    status_code = 403


class RefreshTokenReuseError(AppError):
    code = "refresh_token_reuse_detected"
    status_code = 401


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        verification_tokens: EmailVerificationTokenRepository,
        refresh_tokens: RefreshTokenRepository,
        email_sender: EmailSender,
    ) -> None:
        self._users = users
        self._verification_tokens = verification_tokens
        self._refresh_tokens = refresh_tokens
        self._email_sender = email_sender

    async def register(self, *, email: str, password: str) -> str:
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise EmailAlreadyRegisteredError(f"{email} is already registered")

        user = await self._users.create(email=email, hashed_password=hash_password(password))

        raw_token = generate_opaque_token()
        expires_at = datetime.datetime.now(datetime.UTC) + VERIFICATION_TOKEN_TTL
        await self._verification_tokens.create(
            user_id=user.id, token_hash=hash_opaque_token(raw_token), expires_at=expires_at
        )
        await self._email_sender.send_verification_email(to=email, token=raw_token)
        return user.id

    async def verify_email(self, *, token: str) -> None:
        record = await self._verification_tokens.get_by_hash(hash_opaque_token(token))
        now = datetime.datetime.now(datetime.UTC)
        if record is None or record.used_at is not None or record.expires_at < now:
            raise InvalidOrExpiredTokenError("verification token is invalid or expired")

        user = await self._users.get_by_id(record.user_id)
        assert user is not None
        await self._users.activate(user)
        await self._verification_tokens.mark_used(record)

    async def login(self, *, email: str, password: str) -> tuple[str, str]:
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("invalid email or password")
        if not user.is_active:
            raise AccountNotActiveError("account is not verified")

        access_token = create_access_token(user_id=user.id)
        raw_refresh_token = generate_opaque_token()
        expires_at = datetime.datetime.now(datetime.UTC) + REFRESH_TOKEN_TTL
        await self._refresh_tokens.create(
            user_id=user.id, token_hash=hash_opaque_token(raw_refresh_token), expires_at=expires_at
        )
        return access_token, raw_refresh_token

    async def refresh(self, *, refresh_token: str) -> tuple[str, str]:
        token_hash = hash_opaque_token(refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        if record is None:
            raise InvalidOrExpiredTokenError("refresh token is invalid")
        if record.revoked_at is not None:
            await self._refresh_tokens.revoke_all_for_user(record.user_id)
            raise RefreshTokenReuseError("refresh token reuse detected")
        if record.expires_at < datetime.datetime.now(datetime.UTC):
            raise InvalidOrExpiredTokenError("refresh token has expired")

        access_token = create_access_token(user_id=record.user_id)
        raw_new_refresh_token = generate_opaque_token()
        expires_at = datetime.datetime.now(datetime.UTC) + REFRESH_TOKEN_TTL
        new_record = await self._refresh_tokens.create(
            user_id=record.user_id,
            token_hash=hash_opaque_token(raw_new_refresh_token),
            expires_at=expires_at,
        )
        await self._refresh_tokens.revoke(record, replaced_by_id=new_record.id)
        return access_token, raw_new_refresh_token

    async def logout(self, *, refresh_token: str) -> None:
        record = await self._refresh_tokens.get_by_hash(hash_opaque_token(refresh_token))
        if record is not None and record.revoked_at is None:
            await self._refresh_tokens.revoke(record)

    async def logout_all(self, *, user_id: str) -> None:
        await self._refresh_tokens.revoke_all_for_user(user_id)
