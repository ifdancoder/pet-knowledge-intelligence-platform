import logging

from httpx import AsyncClient


def _extract_verification_token(caplog: logging.LogCaptureFixture, email: str) -> str:
    for record in caplog.records:
        if email in record.getMessage():
            return record.getMessage().rsplit("token=", 1)[1]
    raise AssertionError(f"no verification email logged for {email}")


async def test_register_verify_login_refresh_logout_flow(
    client: AsyncClient, caplog: logging.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "a@example.com", "password": "longenoughpassword"},
        )
    assert register_response.status_code == 201
    user_id = register_response.json()["user_id"]
    assert user_id

    token = _extract_verification_token(caplog, "a@example.com")

    verify_response = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_response.status_code == 204

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "longenoughpassword"}
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    reuse_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert reuse_response.status_code == 401


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register", json={"email": "dup@example.com", "password": "longenoughpassword"}
    )
    response = await client.post(
        "/api/v1/auth/register", json={"email": "dup@example.com", "password": "anotherpassword"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register", json={"email": "b@example.com", "password": "longenoughpassword"}
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": "b@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
