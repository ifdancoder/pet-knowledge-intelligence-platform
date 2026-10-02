from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_can_query_postgres(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1
