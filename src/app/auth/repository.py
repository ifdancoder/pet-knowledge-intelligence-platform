import datetime
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import EmailVerificationToken, RefreshToken, User


class UserRepository(Protocol):
    async def create(self, *, email: str, hashed_password: str) -> User: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: str) -> User | None: ...
    async def activate(self, user: User) -> None: ...


class EmailVerificationTokenRepository(Protocol):
    async def create(
        self, *, user_id: str, token_hash: str, expires_at: datetime.datetime
    ) -> EmailVerificationToken: ...
    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None: ...
    async def mark_used(self, token: EmailVerificationToken) -> None: ...


class RefreshTokenRepository(Protocol):
    async def create(
        self, *, user_id: str, token_hash: str, expires_at: datetime.datetime
    ) -> RefreshToken: ...
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...
    async def revoke(self, token: RefreshToken, *, replaced_by_id: str | None = None) -> None: ...
    async def revoke_all_for_user(self, user_id: str) -> None: ...


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password, is_active=False)
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def activate(self, user: User) -> None:
        user.is_active = True
        await self._session.flush()


class SqlAlchemyEmailVerificationTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: str, token_hash: str, expires_at: datetime.datetime
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self._session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: EmailVerificationToken) -> None:
        token.used_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, user_id: str, token_hash: str, expires_at: datetime.datetime
    ) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken, *, replaced_by_id: str | None = None) -> None:
        token.revoked_at = datetime.datetime.now(datetime.UTC)
        token.replaced_by_id = replaced_by_id
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.datetime.now(datetime.UTC))
        )
        await self._session.flush()
