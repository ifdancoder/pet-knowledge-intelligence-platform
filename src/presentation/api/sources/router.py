import os

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from application.ingestion.command_handlers import UploadSourceCommandHandler
from application.ingestion.commands import UploadSourceCommand
from application.ingestion.queries import GetSourceStatusQuery, ListSourcesByWorkspaceQuery
from application.ingestion.query_handlers import (
    GetSourceStatusQueryHandler,
    ListSourcesByWorkspaceQueryHandler,
)
from domain.ingestion.exceptions import SourceNotFoundError
from domain.workspaces.entities import Permission, Role
from infrastructure.database.session import get_db
from infrastructure.ingestion.async_repository import SqlAlchemyAsyncSourceRepository
from infrastructure.ingestion.storage import S3Storage
from presentation.api.sources.schemas import SourceResponse
from presentation.api.workspaces.dependencies import require_permission
from presentation.tasks.ingestion import extract_document

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/sources", tags=["sources"])

_storage = S3Storage(
    endpoint_url=os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000"),
    access_key=os.environ.get("S3_ACCESS_KEY", "kip"),
    secret_key=os.environ.get("S3_SECRET_KEY", "kipkipkip"),
    bucket=os.environ.get("S3_BUCKET", "sources"),
)

_EXTENSION_TO_TYPE = {"pdf": "pdf", "md": "markdown", "markdown": "markdown"}


def get_upload_handler(session: AsyncSession = Depends(get_db)) -> UploadSourceCommandHandler:
    return UploadSourceCommandHandler(SqlAlchemyAsyncSourceRepository(session), _storage)


def get_status_handler(session: AsyncSession = Depends(get_db)) -> GetSourceStatusQueryHandler:
    return GetSourceStatusQueryHandler(SqlAlchemyAsyncSourceRepository(session))


def get_list_sources_handler(
    session: AsyncSession = Depends(get_db),
) -> ListSourcesByWorkspaceQueryHandler:
    return ListSourcesByWorkspaceQueryHandler(SqlAlchemyAsyncSourceRepository(session))


@router.post("", response_model=SourceResponse, status_code=201)
async def upload_source(
    workspace_id: str,
    file: UploadFile = File(...),
    _role: Role = Depends(require_permission(Permission.MANAGE_SOURCES)),
    handler: UploadSourceCommandHandler = Depends(get_upload_handler),
) -> SourceResponse:
    extension = (file.filename or "").rsplit(".", 1)[-1].lower()
    source_type = _EXTENSION_TO_TYPE.get(extension, "markdown")
    file_bytes = await file.read()

    source_id = await handler.handle(
        UploadSourceCommand(
            workspace_id=workspace_id,
            type=source_type,
            filename=file.filename or "upload",
            file_bytes=file_bytes,
        )
    )
    extract_document.delay(source_id)
    return SourceResponse(source_id=source_id, status="queued", error=None)


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    workspace_id: str,
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    handler: ListSourcesByWorkspaceQueryHandler = Depends(get_list_sources_handler),
) -> list[SourceResponse]:
    sources = await handler.handle(ListSourcesByWorkspaceQuery(workspace_id=workspace_id))
    return [SourceResponse(source_id=s.id, status=s.status, error=s.error) for s in sources]


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source_status(
    workspace_id: str,
    source_id: str,
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    handler: GetSourceStatusQueryHandler = Depends(get_status_handler),
) -> SourceResponse:
    source = await handler.handle(GetSourceStatusQuery(source_id))
    if source is None:
        raise SourceNotFoundError(source_id)
    return SourceResponse(source_id=source.id, status=source.status, error=source.error)
