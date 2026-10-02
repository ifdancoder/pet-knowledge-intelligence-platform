import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User


async def test_user_email_must_be_unique(db_session: AsyncSession) -> None:
    db_session.add(User(email="a@example.com", hashed_password="x", is_active=False))
    await db_session.flush()
    db_session.add(User(email="a@example.com", hashed_password="y", is_active=False))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_user_gets_a_ulid_and_timestamps(db_session: AsyncSession) -> None:
    user = User(email="b@example.com", hashed_password="x", is_active=False)
    db_session.add(user)
    await db_session.flush()
    assert len(user.id) == 26
    assert isinstance(user.created_at, datetime.datetime)
