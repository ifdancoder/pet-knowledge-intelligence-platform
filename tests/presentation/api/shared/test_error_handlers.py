from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from domain.auth.exceptions import EmailAlreadyRegisteredError
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
