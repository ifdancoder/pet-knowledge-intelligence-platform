import re

from app.shared.exceptions import AppError
from app.workspaces.models import Workspace, WorkspaceMember
from app.workspaces.permissions import Role
from app.workspaces.repository import WorkspaceMemberRepository, WorkspaceRepository


class WorkspaceNotFoundError(AppError):
    code = "workspace_not_found"
    status_code = 404


class MemberNotFoundError(AppError):
    code = "member_not_found"
    status_code = 404


class LastOwnerError(AppError):
    code = "cannot_remove_last_owner"
    status_code = 409


def slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "workspace"


class WorkspaceService:
    def __init__(self, workspaces: WorkspaceRepository, members: WorkspaceMemberRepository) -> None:
        self._workspaces = workspaces
        self._members = members

    async def create_workspace(self, *, name: str, owner_id: str) -> Workspace:
        workspace = await self._workspaces.create(name=name, slug=slugify(name))
        await self._members.add(
            workspace_id=workspace.id, user_id=owner_id, role=Role.OWNER.value, invited_by=None
        )
        return workspace

    async def invite_member(
        self, *, workspace_id: str, user_id: str, role: Role, invited_by: str
    ) -> None:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        await self._members.add(
            workspace_id=workspace_id, user_id=user_id, role=role.value, invited_by=invited_by
        )

    async def list_members(self, *, workspace_id: str) -> list[WorkspaceMember]:
        return await self._members.list_for_workspace(workspace_id)

    async def change_role(self, *, workspace_id: str, user_id: str, role: Role) -> None:
        member = await self._members.get(workspace_id=workspace_id, user_id=user_id)
        if member is None:
            raise MemberNotFoundError(user_id)
        if (
            member.role == Role.OWNER.value
            and role != Role.OWNER
            and await self._members.count_owners(workspace_id) <= 1
        ):
            raise LastOwnerError(workspace_id)
        await self._members.update_role(member, role=role.value)

    async def remove_member(self, *, workspace_id: str, user_id: str) -> None:
        member = await self._members.get(workspace_id=workspace_id, user_id=user_id)
        if member is None:
            raise MemberNotFoundError(user_id)
        if member.role == Role.OWNER.value and await self._members.count_owners(workspace_id) <= 1:
            raise LastOwnerError(workspace_id)
        await self._members.remove(member)

    async def delete_workspace(self, *, workspace_id: str) -> None:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        await self._workspaces.delete(workspace)
