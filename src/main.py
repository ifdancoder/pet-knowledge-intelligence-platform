from fastapi import FastAPI

from app.shared.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge Intelligence Platform")
    register_exception_handlers(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
