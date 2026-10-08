import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from infrastructure.observability.bootstrap import configure_observability

# Configure tracing before imports that transitively load the Celery worker.
configure_observability(service_name="kip-api")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import default as default_metrics

from infrastructure.database.session import build_session_factory, session_holder
from presentation.api.auth.router import router as auth_router
from presentation.api.conversations.router import router as conversations_router
from presentation.api.search.router import router as search_router
from presentation.api.shared.error_handlers import register_domain_exception_handlers
from presentation.api.sources.router import router as sources_router
from presentation.api.workspaces.router import router as workspaces_router

_instrumentator = Instrumentator()
_instrumentator.add(default_metrics())
_instrumented = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    session_holder.factory = build_session_factory(os.environ["DATABASE_URL"])
    yield


def create_app() -> FastAPI:
    global _instrumented
    app = FastAPI(title="Knowledge Intelligence Platform", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_domain_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(workspaces_router)
    app.include_router(sources_router)
    app.include_router(search_router)
    app.include_router(conversations_router)
    FastAPIInstrumentor.instrument_app(app)

    if not _instrumented:
        _instrumentator.instrument(app)
        _instrumented = True
    _instrumentator.expose(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
