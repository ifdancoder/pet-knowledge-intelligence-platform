import logging
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

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


async def test_upload_creates_a_queued_source_and_enqueues_extraction(
    client: AsyncClient, caplog: logging.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    import presentation.api.sources.router as sources_router

    fake_delay = MagicMock()
    monkeypatch.setattr(sources_router.extract_document, "delay", fake_delay)
    monkeypatch.setattr(sources_router, "_storage", MagicMock(upload=MagicMock()))

    await _register_and_verify(client, "owner@example.com", caplog)
    owner_token = await _login(client, "owner@example.com")

    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Acme"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_response.json()["id"]

    upload_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/sources",
        files={"file": ("notes.md", b"# hello", "text/markdown")},
        headers=_auth_header(owner_token),
    )
    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["status"] == "queued"
    fake_delay.assert_called_once_with(body["source_id"])

    status_response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/sources/{body['source_id']}",
        headers=_auth_header(owner_token),
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "queued"


async def test_get_status_rejects_unknown_source(
    client: AsyncClient, caplog: logging.LogCaptureFixture
) -> None:
    await _register_and_verify(client, "owner2@example.com", caplog)
    owner_token = await _login(client, "owner2@example.com")
    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Beta"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/sources/missing", headers=_auth_header(owner_token)
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "source_not_found"


async def test_list_sources_returns_only_that_workspaces_sources(
    client: AsyncClient, caplog: logging.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    import presentation.api.sources.router as sources_router

    monkeypatch.setattr(sources_router.extract_document, "delay", MagicMock())
    monkeypatch.setattr(sources_router, "_storage", MagicMock(upload=MagicMock()))

    await _register_and_verify(client, "lister2@example.com", caplog)
    owner_token = await _login(client, "lister2@example.com")
    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Acme"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/workspaces/{workspace_id}/sources",
        files={"file": ("notes.md", b"# hello", "text/markdown")},
        headers=_auth_header(owner_token),
    )

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/sources", headers=_auth_header(owner_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "queued"
