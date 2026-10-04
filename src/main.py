import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.database.session import build_session_factory, session_holder
from presentation.api.auth.router import router as auth_router
from presentation.api.search.router import router as search_router
from presentation.api.shared.error_handlers import register_domain_exception_handlers
from presentation.api.sources.router import router as sources_router
from presentation.api.workspaces.router import router as workspaces_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    session_holder.factory = build_session_factory(os.environ["DATABASE_URL"])
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge Intelligence Platform", lifespan=lifespan)
    register_domain_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(workspaces_router)
    app.include_router(sources_router)
    app.include_router(search_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
