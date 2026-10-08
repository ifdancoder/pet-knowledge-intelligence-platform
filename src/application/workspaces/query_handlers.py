from application.workspaces.queries import (
    GetWorkspaceByIdQuery,
    GetWorkspaceMembersQuery,
    GetWorkspacesForUserQuery,
)
from domain.workspaces.entities import Workspace, WorkspaceMember
from domain.workspaces.exceptions import WorkspaceNotFoundError
from domain.workspaces.ports import WorkspaceRepository


class GetWorkspaceByIdQueryHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, query: GetWorkspaceByIdQuery) -> Workspace | None:
        return await self._workspaces.get_by_id(query.workspace_id)


class GetWorkspaceMembersQueryHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, query: GetWorkspaceMembersQuery) -> list[WorkspaceMember]:
        workspace = await self._workspaces.get_by_id(query.workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(query.workspace_id)
        return workspace.members


class GetWorkspacesForUserQueryHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, query: GetWorkspacesForUserQuery) -> list[Workspace]:
        return await self._workspaces.list_by_user_id(query.user_id)
