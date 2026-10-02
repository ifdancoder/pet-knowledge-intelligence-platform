from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api import get_current_user_id
from app.shared.db import get_db
from app.workspaces.permissions import Permission, Role, require_permission
from app.workspaces.repository import (
    SqlAlchemyWorkspaceMemberRepository,
    SqlAlchemyWorkspaceRepository,
)
from app.workspaces.schemas import (
    CreateWorkspaceRequest,
    InviteMemberRequest,
    MemberResponse,
    UpdateMemberRoleRequest,
    WorkspaceResponse,
)
from app.workspaces.service import WorkspaceService

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


def get_workspace_service(session: AsyncSession = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(
        workspaces=SqlAlchemyWorkspaceRepository(session),
        members=SqlAlchemyWorkspaceMemberRepository(session),
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: CreateWorkspaceRequest,
    user_id: str = Depends(get_current_user_id),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceResponse:
    workspace = await service.create_workspace(name=payload.name, owner_id=user_id)
    return WorkspaceResponse(id=workspace.id, name=workspace.name, slug=workspace.slug)


@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: str,
    payload: InviteMemberRequest,
    user_id: str = Depends(get_current_user_id),
    _role: Role = Depends(require_permission(Permission.MANAGE_MEMBERS)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    await service.invite_member(
        workspace_id=workspace_id, user_id=payload.user_id, role=payload.role, invited_by=user_id
    )


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
async def list_members(
    workspace_id: str,
    _role: Role = Depends(require_permission(Permission.VIEW_WORKSPACE)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> list[MemberResponse]:
    members = await service.list_members(workspace_id=workspace_id)
    return [MemberResponse(user_id=m.user_id, role=Role(m.role)) for m in members]


@router.patch("/{workspace_id}/members/{member_user_id}")
async def update_member_role(
    workspace_id: str,
    member_user_id: str,
    payload: UpdateMemberRoleRequest,
    _role: Role = Depends(require_permission(Permission.MANAGE_MEMBERS)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    await service.change_role(workspace_id=workspace_id, user_id=member_user_id, role=payload.role)


@router.delete("/{workspace_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: str,
    member_user_id: str,
    _role: Role = Depends(require_permission(Permission.MANAGE_MEMBERS)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    await service.remove_member(workspace_id=workspace_id, user_id=member_user_id)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    _role: Role = Depends(require_permission(Permission.DELETE_WORKSPACE)),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    await service.delete_workspace(workspace_id=workspace_id)
