import logging
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.ingestion.models import ChunkModel, DocumentModel, SourceModel

pytestmark = pytest.mark.integration

async def _register_and_verify(client: AsyncClient, email: str, caplog: logging.LogCaptureFixture) -> str:
    with caplog.at_level(logging.INFO):
        response = await client.post(
            "/api/v1/auth/register", json={"email": email, "password": "longenoughpassword"}
        )
    user_id = response.json()["user_id"]
    token = None
    for record in caplog.records:
        if email in record.getMessage():
            token = record.getMessage().rsplit("token=", 1)[1]
    assert token is not None
    await client.post("/api/v1/auth/verify-email", json={"token": token})
    return str(user_id)


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "longenoughpassword"}
    )
    return str(response.json()["access_token"])


def _auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def test_search_returns_a_chunk_found_by_either_source(
    client: AsyncClient,
    caplog: logging.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    import presentation.api.search.router as search_router

    fake_keyword = MagicMock()
    fake_keyword.search.return_value = [{"chunk_id": "c1", "score": 9.0}]
    monkeypatch.setattr(search_router, "_keyword_search", fake_keyword)
    monkeypatch.setattr(search_router, "_embedding_provider", MagicMock(embed=lambda texts: [[0.1] * 1536]))
    fake_reranker = MagicMock()
    fake_reranker.rerank.side_effect = lambda *, query, results, limit: results[:limit]
    monkeypatch.setattr(search_router, "_reranker", fake_reranker)

    await _register_and_verify(client, "owner@example.com", caplog)
    owner_token = await _login(client, "owner@example.com")
    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Acme"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_response.json()["id"]

    # Flushed separately — SQLAlchemy's automatic FK-dependency insert ordering does not
    # reliably apply across mixed-mapper add_all() batches with the asyncpg driver.
    db_session.add(SourceModel(id="s1", workspace_id=workspace_id, type="markdown", storage_key="w/a.md"))
    await db_session.flush()
    db_session.add(DocumentModel(id="d1", source_id="s1", raw_text="irrelevant"))
    await db_session.flush()
    db_session.add(
        ChunkModel(
            id="c1", source_id="s1", document_id="d1", workspace_id=workspace_id,
            order_index=0, text="hello world", embedding=[0.1] * 1536,
        )
    )
    await db_session.flush()

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/search",
        params={"q": "hello"},
        headers=_auth_header(owner_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["chunk_id"] == "c1"
    assert body[0]["text"] == "hello world"


async def test_search_rejects_invalid_source_type(
    client: AsyncClient, caplog: logging.LogCaptureFixture
) -> None:
    await _register_and_verify(client, "owner2@example.com", caplog)
    owner_token = await _login(client, "owner2@example.com")
    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Beta"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/search",
        params={"q": "hello", "source_type": "docx"},
        headers=_auth_header(owner_token),
    )

    assert response.status_code == 422
