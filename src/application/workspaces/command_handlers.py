from application.workspaces.commands import (
    ChangeMemberRoleCommand,
    CreateWorkspaceCommand,
    DeleteWorkspaceCommand,
    InviteMemberCommand,
    RemoveMemberCommand,
)
from domain.workspaces.entities import Workspace
from domain.workspaces.exceptions import WorkspaceNotFoundError
from domain.workspaces.ports import WorkspaceRepository


class CreateWorkspaceCommandHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, command: CreateWorkspaceCommand) -> str:
        workspace = Workspace.create(name=command.name, owner_id=command.owner_id)
        await self._workspaces.add(workspace)
        return workspace.id


class InviteMemberCommandHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, command: InviteMemberCommand) -> None:
        workspace = await self._workspaces.get_by_id(command.workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(command.workspace_id)
        workspace.invite_member(
            user_id=command.user_id, role=command.role, invited_by=command.invited_by
        )
        await self._workspaces.save(workspace)


class ChangeMemberRoleCommandHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, command: ChangeMemberRoleCommand) -> None:
        workspace = await self._workspaces.get_by_id(command.workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(command.workspace_id)
        workspace.change_member_role(command.user_id, command.role)
        await self._workspaces.save(workspace)


class RemoveMemberCommandHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, command: RemoveMemberCommand) -> None:
        workspace = await self._workspaces.get_by_id(command.workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(command.workspace_id)
        workspace.remove_member(command.user_id)
        await self._workspaces.save(workspace)


class DeleteWorkspaceCommandHandler:
    def __init__(self, workspaces: WorkspaceRepository) -> None:
        self._workspaces = workspaces

    async def handle(self, command: DeleteWorkspaceCommand) -> None:
        workspace = await self._workspaces.get_by_id(command.workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError(command.workspace_id)
        await self._workspaces.delete(workspace)
