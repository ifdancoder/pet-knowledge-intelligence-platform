from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def build_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


class _SessionFactoryHolder:
    factory: async_sessionmaker[AsyncSession] | None = None


session_holder = _SessionFactoryHolder()


async def get_db() -> AsyncIterator[AsyncSession]:
    assert session_holder.factory is not None, "session factory not configured"
    async with session_holder.factory() as session, session.begin():
        yield session
