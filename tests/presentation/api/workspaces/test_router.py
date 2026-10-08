import logging

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


async def test_owner_can_invite_member_and_viewer_is_blocked(
    client: AsyncClient, caplog: logging.LogCaptureFixture
) -> None:
    owner_id = await _register_and_verify(client, "owner@example.com", caplog)
    viewer_id = await _register_and_verify(client, "viewer@example.com", caplog)
    owner_token = await _login(client, "owner@example.com")
    viewer_token = await _login(client, "viewer@example.com")

    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Acme"}, headers=_auth_header(owner_token)
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["id"]

    invite_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": viewer_id, "role": "viewer"},
        headers=_auth_header(owner_token),
    )
    assert invite_response.status_code == 201

    members_response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/members", headers=_auth_header(viewer_token)
    )
    assert members_response.status_code == 200
    assert len(members_response.json()) == 2

    blocked_response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_id": "someone-else", "role": "member"},
        headers=_auth_header(viewer_token),
    )
    assert blocked_response.status_code == 403
    assert blocked_response.json()["error"]["code"] == "insufficient_permission"

    delete_blocked = await client.delete(
        f"/api/v1/workspaces/{workspace_id}", headers=_auth_header(viewer_token)
    )
    assert delete_blocked.status_code == 403

    delete_allowed = await client.delete(
        f"/api/v1/workspaces/{workspace_id}", headers=_auth_header(owner_token)
    )
    assert delete_allowed.status_code == 204
    assert owner_id


async def test_non_member_cannot_view_workspace(
    client: AsyncClient, caplog: logging.LogCaptureFixture
) -> None:
    await _register_and_verify(client, "owner2@example.com", caplog)
    await _register_and_verify(client, "outsider@example.com", caplog)
    owner_token = await _login(client, "owner2@example.com")
    outsider_token = await _login(client, "outsider@example.com")

    create_response = await client.post(
        "/api/v1/workspaces", json={"name": "Beta"}, headers=_auth_header(owner_token)
    )
    workspace_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}/members", headers=_auth_header(outsider_token)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_a_workspace_member"


async def test_list_my_workspaces_returns_only_my_workspaces(
    client: AsyncClient, caplog: logging.LogCaptureFixture
) -> None:
    await _register_and_verify(client, "lister@example.com", caplog)
    await _register_and_verify(client, "other@example.com", caplog)
    my_token = await _login(client, "lister@example.com")
    other_token = await _login(client, "other@example.com")

    await client.post("/api/v1/workspaces", json={"name": "Mine"}, headers=_auth_header(my_token))
    await client.post("/api/v1/workspaces", json={"name": "Theirs"}, headers=_auth_header(other_token))

    response = await client.get("/api/v1/workspaces", headers=_auth_header(my_token))

    assert response.status_code == 200
    names = [w["name"] for w in response.json()]
    assert names == ["Mine"]
