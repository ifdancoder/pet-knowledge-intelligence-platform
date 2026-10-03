import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.api import router as auth_router
from app.shared.exceptions import register_exception_handlers
from app.workspaces.api import router as workspaces_router
from infrastructure.database.session import build_session_factory, session_holder
from presentation.api.shared.error_handlers import register_domain_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    session_holder.factory = build_session_factory(os.environ["DATABASE_URL"])
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge Intelligence Platform", lifespan=lifespan)
    register_exception_handlers(app)
    register_domain_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(workspaces_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
