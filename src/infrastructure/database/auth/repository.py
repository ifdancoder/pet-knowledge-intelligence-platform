import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.entities import EmailVerificationToken, RefreshToken, User
from infrastructure.database.auth.models import (
    EmailVerificationTokenModel,
    RefreshTokenModel,
    UserModel,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        model = UserModel(
            id=user.id, email=user.email, hashed_password=user.hashed_password, is_active=user.is_active
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _user_to_entity(model) if model is not None else None

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return _user_to_entity(model) if model is not None else None

    async def update(self, user: User) -> None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user.id))
        model = result.scalar_one()
        model.email = user.email
        model.hashed_password = user.hashed_password
        model.is_active = user.is_active
        await self._session.flush()


def _user_to_entity(model: UserModel) -> User:
    return User(
        id=model.id, email=model.email, hashed_password=model.hashed_password, is_active=model.is_active
    )


class SqlAlchemyEmailVerificationTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: EmailVerificationToken) -> None:
        model = EmailVerificationTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self._session.execute(
            select(EmailVerificationTokenModel).where(EmailVerificationTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _verification_token_to_entity(model) if model is not None else None

    async def update(self, token: EmailVerificationToken) -> None:
        result = await self._session.execute(
            select(EmailVerificationTokenModel).where(EmailVerificationTokenModel.id == token.id)
        )
        model = result.scalar_one()
        model.used_at = token.used_at
        await self._session.flush()


def _verification_token_to_entity(model: EmailVerificationTokenModel) -> EmailVerificationToken:
    return EmailVerificationToken(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        used_at=model.used_at,
    )


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        model = RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            replaced_by_id=token.replaced_by_id,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _refresh_token_to_entity(model) if model is not None else None

    async def update(self, token: RefreshToken) -> None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.id == token.id)
        )
        model = result.scalar_one()
        model.revoked_at = token.revoked_at
        model.replaced_by_id = token.replaced_by_id
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: str, now: datetime.datetime) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self._session.flush()


def _refresh_token_to_entity(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
        replaced_by_id=model.replaced_by_id,
    )
