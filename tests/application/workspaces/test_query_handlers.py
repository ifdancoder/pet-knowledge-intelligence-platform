from application.workspaces.command_handlers import (
    CreateWorkspaceCommandHandler,
    InviteMemberCommandHandler,
)
from application.workspaces.commands import CreateWorkspaceCommand, InviteMemberCommand
from application.workspaces.queries import GetWorkspaceByIdQuery, GetWorkspaceMembersQuery
from application.workspaces.query_handlers import (
    GetWorkspaceByIdQueryHandler,
    GetWorkspaceMembersQueryHandler,
)
from domain.workspaces.entities import Role, Workspace


class FakeWorkspaceRepository:
    def __init__(self) -> None:
        self.workspaces_by_id: dict[str, Workspace] = {}

    async def add(self, workspace: Workspace) -> None:
        self.workspaces_by_id[workspace.id] = workspace

    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        return self.workspaces_by_id.get(workspace_id)

    async def save(self, workspace: Workspace) -> None:
        self.workspaces_by_id[workspace.id] = workspace

    async def delete(self, workspace: Workspace) -> None:
        self.workspaces_by_id.pop(workspace.id, None)


async def test_get_workspace_by_id_returns_the_workspace() -> None:
    workspaces = FakeWorkspaceRepository()
    create = CreateWorkspaceCommandHandler(workspaces)
    query_handler = GetWorkspaceByIdQueryHandler(workspaces)
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))

    workspace = await query_handler.handle(GetWorkspaceByIdQuery(workspace_id))

    assert workspace is not None
    assert workspace.name == "Acme"
    assert workspace.slug == "acme"


async def test_get_workspace_by_id_returns_none_for_unknown_id() -> None:
    workspaces = FakeWorkspaceRepository()
    query_handler = GetWorkspaceByIdQueryHandler(workspaces)
    assert await query_handler.handle(GetWorkspaceByIdQuery("missing")) is None


async def test_get_workspace_members_returns_all_members() -> None:
    workspaces = FakeWorkspaceRepository()
    create = CreateWorkspaceCommandHandler(workspaces)
    invite = InviteMemberCommandHandler(workspaces)
    query_handler = GetWorkspaceMembersQueryHandler(workspaces)
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    await invite.handle(
        InviteMemberCommand(workspace_id=workspace_id, user_id="user-2", role=Role.VIEWER, invited_by="user-1")
    )

    members = await query_handler.handle(GetWorkspaceMembersQuery(workspace_id))

    assert {m.user_id for m in members} == {"user-1", "user-2"}
