import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.auth.entities import EmailVerificationToken, RefreshToken, User
from infrastructure.database.auth.repository import (
    SqlAlchemyEmailVerificationTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)

pytestmark = pytest.mark.integration

NOW = datetime.datetime.now(datetime.UTC)
FUTURE = NOW + datetime.timedelta(hours=1)


async def test_user_repository_add_and_get(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = User.register(email="a@example.com", hashed_password="hash")
    await repo.add(user)

    fetched = await repo.get_by_email("a@example.com")
    assert fetched == user
    assert await repo.get_by_id(user.id) == user
    assert await repo.get_by_email("missing@example.com") is None


async def test_user_repository_update(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = User.register(email="b@example.com", hashed_password="hash")
    await repo.add(user)

    user.activate()
    await repo.update(user)

    fetched = await repo.get_by_id(user.id)
    assert fetched is not None
    assert fetched.is_active is True


async def test_verification_token_repository(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    user = User.register(email="c@example.com", hashed_password="hash")
    await users.add(user)

    tokens = SqlAlchemyEmailVerificationTokenRepository(db_session)
    token = EmailVerificationToken.issue(
        user_id=user.id, token_hash="h" * 64, ttl=datetime.timedelta(hours=24), now=NOW
    )
    await tokens.add(token)

    fetched = await tokens.get_by_hash("h" * 64)
    assert fetched == token
    assert fetched is not None

    token.mark_used(NOW)
    await tokens.update(token)
    refetched = await tokens.get_by_hash("h" * 64)
    assert refetched is not None
    assert refetched.used_at == NOW


async def test_refresh_token_repository(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    user = User.register(email="d@example.com", hashed_password="hash")
    await users.add(user)

    tokens = SqlAlchemyRefreshTokenRepository(db_session)
    first = RefreshToken.issue(user_id=user.id, token_hash="a" * 64, ttl=datetime.timedelta(days=30), now=NOW)
    second = RefreshToken.issue(user_id=user.id, token_hash="b" * 64, ttl=datetime.timedelta(days=30), now=NOW)
    await tokens.add(first)
    await tokens.add(second)

    first.revoke(NOW, replaced_by_id=second.id)
    await tokens.update(first)
    refetched = await tokens.get_by_hash("a" * 64)
    assert refetched is not None
    assert refetched.revoked_at == NOW
    assert refetched.replaced_by_id == second.id

    await tokens.revoke_all_for_user(user.id, NOW)
    refetched_second = await tokens.get_by_hash("b" * 64)
    assert refetched_second is not None
    assert refetched_second.revoked_at is not None
