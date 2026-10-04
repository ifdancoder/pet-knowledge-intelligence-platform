from unittest.mock import patch

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from domain.auth.exceptions import EmailAlreadyRegisteredError
from domain.workspaces.exceptions import NotAWorkspaceMemberError
from presentation.api.shared.error_handlers import register_domain_exception_handlers


async def test_known_domain_error_maps_to_its_status_code() -> None:
    app = FastAPI()
    register_domain_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise EmailAlreadyRegisteredError("a@example.com is already registered")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 409
    assert response.json() == {
        "error": {"code": "email_already_registered", "message": "a@example.com is already registered"}
    }


async def test_workspace_domain_error_maps_to_its_status_code() -> None:
    app = FastAPI()
    register_domain_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise NotAWorkspaceMemberError("not a member of this workspace")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_a_workspace_member"


async def test_unhandled_exception_becomes_generic_500() -> None:
    app = FastAPI()
    register_domain_exception_handlers(app)

    @app.get("/explode")
    async def explode() -> None:
        raise ValueError("unexpected")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/explode")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Internal server error"}}


async def test_unhandled_exception_is_reported_to_sentry() -> None:
    app = FastAPI()
    register_domain_exception_handlers(app)

    @app.get("/explode")
    async def explode() -> None:
        raise ValueError("unexpected")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    with patch("presentation.api.shared.error_handlers.sentry_sdk.capture_exception") as mock_capture:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/explode")

    mock_capture.assert_called_once()
    assert isinstance(mock_capture.call_args[0][0], ValueError)


async def test_domain_error_is_not_reported_to_sentry() -> None:
    app = FastAPI()
    register_domain_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise EmailAlreadyRegisteredError("a@example.com is already registered")

    with patch("presentation.api.shared.error_handlers.sentry_sdk.capture_exception") as mock_capture:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.get("/boom")

    mock_capture.assert_not_called()
