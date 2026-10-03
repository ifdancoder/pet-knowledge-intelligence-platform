from domain.workspaces.entities import Role, Workspace, WorkspaceMember
from domain.workspaces.exceptions import WorkspaceNotFoundError
from domain.workspaces.ports import WorkspaceRepository


class WorkspaceService:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def create_workspace(self, *, name: str, owner_id: str) -> Workspace:
        workspace = Workspace.create(name=name, owner_id=owner_id)
        await self._workspaces.add(workspace)
        return workspace

    async def invite_member(self, *, workspace_id: str, user_id: str, role: Role, invited_by: str) -> None:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        workspace.invite_member(user_id=user_id, role=role, invited_by=invited_by)
        await self._workspaces.save(workspace)

    async def list_members(self, *, workspace_id: str) -> list[WorkspaceMember]:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        return workspace.members

    async def change_role(self, *, workspace_id: str, user_id: str, role: Role) -> None:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        workspace.change_member_role(user_id, role)
        await self._workspaces.save(workspace)

    async def remove_member(self, *, workspace_id: str, user_id: str) -> None:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        workspace.remove_member(user_id)
        await self._workspaces.save(workspace)

    async def delete_workspace(self, *, workspace_id: str) -> None:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(workspace_id)
        await self._workspaces.delete(workspace)
