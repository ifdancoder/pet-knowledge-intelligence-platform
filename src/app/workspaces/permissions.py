from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api import get_current_user_id
from app.shared.db import get_db
from app.shared.exceptions import AppError


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(str, Enum):
    VIEW_WORKSPACE = "view_workspace"
    MANAGE_SOURCES = "manage_sources"
    MANAGE_MEMBERS = "manage_members"
    DELETE_WORKSPACE = "delete_workspace"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset(
        {Permission.VIEW_WORKSPACE, Permission.MANAGE_SOURCES, Permission.MANAGE_MEMBERS}
    ),
    Role.MEMBER: frozenset({Permission.VIEW_WORKSPACE, Permission.MANAGE_SOURCES}),
    Role.VIEWER: frozenset({Permission.VIEW_WORKSPACE}),
}


def check_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]


class NotAWorkspaceMemberError(AppError):
    code = "not_a_workspace_member"
    status_code = 403


class InsufficientPermissionError(AppError):
    code = "insufficient_permission"
    status_code = 403


def require_permission(permission: Permission) -> Callable[..., Coroutine[Any, Any, Role]]:
    async def dependency(
        workspace_id: str = Path(...),
        user_id: str = Depends(get_current_user_id),
        session: AsyncSession = Depends(get_db),
    ) -> Role:
        from app.workspaces.repository import SqlAlchemyWorkspaceMemberRepository

        members = SqlAlchemyWorkspaceMemberRepository(session)
        membership = await members.get(workspace_id=workspace_id, user_id=user_id)
        if membership is None:
            raise NotAWorkspaceMemberError("not a member of this workspace")

        role = Role(membership.role)
        if not check_permission(role, permission):
            raise InsufficientPermissionError(f"missing permission: {permission.value}")
        return role

    return dependency
