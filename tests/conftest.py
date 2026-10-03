import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

from infrastructure.database.base import Base
from infrastructure.database.session import get_db
from main import create_app

os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-production")


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(image="pgvector/pgvector:pg16", driver="asyncpg") as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    url = postgres_container.get_connection_url()
    test_engine = create_async_engine(url)
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    session = session_factory()
    yield session
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture(scope="session")
def sync_engine(postgres_container: PostgresContainer):
    sync_url = postgres_container.get_connection_url().replace("+asyncpg", "+psycopg2")
    sync_test_engine = create_engine(sync_url)
    with sync_test_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(sync_test_engine)
    yield sync_test_engine
    sync_test_engine.dispose()


@pytest.fixture
def sync_db_session(sync_engine) -> Iterator[Session]:
    connection = sync_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = session_factory()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
