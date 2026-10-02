import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import (
    SqlAlchemyEmailVerificationTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)

FUTURE = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)


async def test_user_repository_create_and_get(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    created = await repo.create(email="a@example.com", hashed_password="hash")
    assert await repo.get_by_email("a@example.com") == created
    assert await repo.get_by_id(created.id) == created
    assert await repo.get_by_email("missing@example.com") is None


async def test_user_repository_activate(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserRepository(db_session)
    user = await repo.create(email="b@example.com", hashed_password="hash")
    assert user.is_active is False
    await repo.activate(user)
    assert user.is_active is True


async def test_verification_token_repository(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    user = await users.create(email="c@example.com", hashed_password="hash")
    tokens = SqlAlchemyEmailVerificationTokenRepository(db_session)
    created = await tokens.create(user_id=user.id, token_hash="h" * 64, expires_at=FUTURE)
    fetched = await tokens.get_by_hash("h" * 64)
    assert fetched == created
    assert fetched is not None
    assert fetched.used_at is None
    await tokens.mark_used(fetched)
    assert fetched.used_at is not None


async def test_refresh_token_repository(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    user = await users.create(email="d@example.com", hashed_password="hash")
    tokens = SqlAlchemyRefreshTokenRepository(db_session)
    first = await tokens.create(user_id=user.id, token_hash="a" * 64, expires_at=FUTURE)
    second = await tokens.create(user_id=user.id, token_hash="b" * 64, expires_at=FUTURE)

    await tokens.revoke(first, replaced_by_id=second.id)
    refetched = await tokens.get_by_hash("a" * 64)
    assert refetched is not None
    assert refetched.revoked_at is not None
    assert refetched.replaced_by_id == second.id

    await tokens.revoke_all_for_user(user.id)
    refetched_second = await tokens.get_by_hash("b" * 64)
    assert refetched_second is not None
    assert refetched_second.revoked_at is not None
