import datetime

from app.auth.email_sender import EmailSender
from app.auth.repository import (
    EmailVerificationTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.auth.security import generate_opaque_token, hash_opaque_token, hash_password
from app.shared.exceptions import AppError

VERIFICATION_TOKEN_TTL = datetime.timedelta(hours=24)


class EmailAlreadyRegisteredError(AppError):
    code = "email_already_registered"
    status_code = 409


class InvalidOrExpiredTokenError(AppError):
    code = "invalid_or_expired_token"
    status_code = 400


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
