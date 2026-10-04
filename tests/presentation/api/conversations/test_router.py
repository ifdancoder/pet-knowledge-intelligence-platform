import logging
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient


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


async def test_send_message_streams_deltas_and_persists_the_reply(
    client: AsyncClient, caplog: logging.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    import presentation.api.conversations.router as conversations_router
    import presentation.api.search.router as search_router

    fake_llm = MagicMock()

    async def fake_stream(*, system: str, messages: list[dict[str, str]]):
        yield "Hello"
        yield " there"

    fake_llm.stream = fake_stream
    monkeypatch.setattr(conversations_router, "_llm", fake_llm)

    # the service's retrieval step goes through the same module-level search
    # components as presentation.api.search.router; no real Elasticsearch/embedding
    # infra is running in this test, so these are faked exactly as search's own
    # router test fakes them.
    fake_keyword = MagicMock()
    fake_keyword.search.return_value = []
    monkeypatch.setattr(search_router, "_keyword_search", fake_keyword)
    monkeypatch.setattr(search_router, "_embedding_provider", MagicMock(embed=lambda texts: [[0.1] * 1536]))
    fake_reranker = MagicMock()
    fake_reranker.rerank.side_effect = lambda *, query, results, limit: results[:limit]
    monkeypatch.setattr(search_router, "_reranker", fake_reranker)

    await _register_and_verify(client, "owner@example.com", caplog)
    owner_token = await _login(client, "owner@example.com")
    create_workspace = await client.post(
        "/api/v1/workspaces", json={"name": "Acme"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_workspace.json()["id"]

    create_conversation = await client.post(
        f"/api/v1/workspaces/{workspace_id}/conversations", headers=_auth_header(owner_token)
    )
    assert create_conversation.status_code == 201
    conversation_id = create_conversation.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
        json={"content": "what do you know?"},
        headers=_auth_header(owner_token),
    ) as response:
        assert response.status_code == 200
        body = "".join([chunk async for chunk in response.aiter_text()])

    assert 'data: {"delta": "Hello"}' in body
    assert 'data: {"delta": " there"}' in body
    assert '"done": true' in body

    messages_response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
        headers=_auth_header(owner_token),
    )
    messages = messages_response.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello there"


async def test_a_non_owner_cannot_read_another_user_s_conversation(
    client: AsyncClient, caplog: logging.LogCaptureFixture
) -> None:
    owner_id = await _register_and_verify(client, "owner2@example.com", caplog)
    owner_token = await _login(client, "owner2@example.com")
    create_workspace = await client.post(
        "/api/v1/workspaces", json={"name": "Beta"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_workspace.json()["id"]
    create_conversation = await client.post(
        f"/api/v1/workspaces/{workspace_id}/conversations", headers=_auth_header(owner_token)
    )
    conversation_id = create_conversation.json()["id"]

    intruder_id = await _register_and_verify(client, "intruder@example.com", caplog)
    intruder_token = await _login(client, "intruder@example.com")
    # invite the intruder as a real workspace member so the request reaches
    # GetConversationMessagesQueryHandler and the assertion exercises the
    # conversation-ownership check specifically, not workspace membership.
    await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": intruder_id, "role": "viewer"},
        headers=_auth_header(owner_token),
    )
    assert owner_id != intruder_id

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/messages",
        headers=_auth_header(intruder_token),
    )
    assert response.status_code in (403, 404)
