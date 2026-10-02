from fastapi import FastAPI

from app.auth.api import router as auth_router
from app.shared.exceptions import register_exception_handlers
from app.workspaces.api import router as workspaces_router


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge Intelligence Platform")
    register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(workspaces_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
