import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.auth.models import UserModel


async def test_user_model_email_must_be_unique(db_session: AsyncSession) -> None:
    db_session.add(UserModel(id="u1", email="a@example.com", hashed_password="x", is_active=False))
    await db_session.flush()
    db_session.add(UserModel(id="u2", email="a@example.com", hashed_password="y", is_active=False))
    with pytest.raises(IntegrityError):
        await db_session.flush()
