from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.shared.exceptions import AppError, register_exception_handlers


class _DummyError(AppError):
    code = "dummy_error"
    status_code = 418


async def test_app_error_is_mapped_to_json_response() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise _DummyError("boom happened")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 418
    assert response.json() == {"error": {"code": "dummy_error", "message": "boom happened"}}


async def test_unhandled_exception_becomes_generic_500() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/explode")
    async def explode() -> None:
        raise ValueError("unexpected")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/explode")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "Internal server error"}}
