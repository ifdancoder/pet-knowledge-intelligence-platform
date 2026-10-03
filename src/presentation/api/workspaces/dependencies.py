from collections.abc import Awaitable, Callable

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from domain.workspaces.entities import Permission, Role, check_permission
from domain.workspaces.exceptions import InsufficientPermissionError, NotAWorkspaceMemberError
from infrastructure.database.session import get_db
from infrastructure.database.workspaces.repository import SqlAlchemyWorkspaceRepository
from presentation.api.auth.dependencies import get_current_user_id


def require_permission(permission: Permission) -> Callable[..., Awaitable[Role]]:
    async def dependency(
        workspace_id: str = Path(...),
        user_id: str = Depends(get_current_user_id),
        session: AsyncSession = Depends(get_db),
    ) -> Role:
        workspaces = SqlAlchemyWorkspaceRepository(session)
        workspace = await workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise NotAWorkspaceMemberError("not a member of this workspace")

        member = workspace.get_member(user_id)
        if member is None:
            raise NotAWorkspaceMemberError("not a member of this workspace")

        if not check_permission(member.role, permission):
            raise InsufficientPermissionError(f"missing permission: {permission.value}")
        return member.role

    return dependency
