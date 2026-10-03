from application.workspaces.command_handlers import (
    ChangeMemberRoleCommandHandler,
    CreateWorkspaceCommandHandler,
    DeleteWorkspaceCommandHandler,
    InviteMemberCommandHandler,
    RemoveMemberCommandHandler,
)
from application.workspaces.commands import (
    ChangeMemberRoleCommand,
    CreateWorkspaceCommand,
    DeleteWorkspaceCommand,
    InviteMemberCommand,
    RemoveMemberCommand,
)
from domain.workspaces.entities import Role, Workspace
from domain.workspaces.exceptions import LastOwnerError, MemberNotFoundError, WorkspaceNotFoundError


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


def make_handlers() -> tuple[
    CreateWorkspaceCommandHandler,
    InviteMemberCommandHandler,
    ChangeMemberRoleCommandHandler,
    RemoveMemberCommandHandler,
    DeleteWorkspaceCommandHandler,
    FakeWorkspaceRepository,
]:
    workspaces = FakeWorkspaceRepository()
    return (
        CreateWorkspaceCommandHandler(workspaces),
        InviteMemberCommandHandler(workspaces),
        ChangeMemberRoleCommandHandler(workspaces),
        RemoveMemberCommandHandler(workspaces),
        DeleteWorkspaceCommandHandler(workspaces),
        workspaces,
    )


async def test_create_workspace_adds_creator_as_owner() -> None:
    create, _, _, _, _, workspaces = make_handlers()
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    stored = await workspaces.get_by_id(workspace_id)
    assert stored is not None
    member = stored.get_member("user-1")
    assert member is not None
    assert member.role == Role.OWNER


async def test_invite_member_rejects_unknown_workspace() -> None:
    _, invite, _, _, _, _ = make_handlers()
    try:
        await invite.handle(
            InviteMemberCommand(workspace_id="missing", user_id="u2", role=Role.VIEWER, invited_by="u1")
        )
        raise AssertionError("expected WorkspaceNotFoundError")
    except WorkspaceNotFoundError:
        pass


async def test_invite_member_adds_membership() -> None:
    create, invite, _, _, _, workspaces = make_handlers()
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    await invite.handle(
        InviteMemberCommand(workspace_id=workspace_id, user_id="user-2", role=Role.VIEWER, invited_by="user-1")
    )
    stored = await workspaces.get_by_id(workspace_id)
    assert stored is not None
    assert stored.get_member("user-2") is not None


async def test_change_role_rejects_demoting_last_owner() -> None:
    create, _, change_role, _, _, _ = make_handlers()
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    try:
        await change_role.handle(
            ChangeMemberRoleCommand(workspace_id=workspace_id, user_id="user-1", role=Role.ADMIN)
        )
        raise AssertionError("expected LastOwnerError")
    except LastOwnerError:
        pass


async def test_change_role_rejects_unknown_member() -> None:
    create, _, change_role, _, _, _ = make_handlers()
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    try:
        await change_role.handle(
            ChangeMemberRoleCommand(workspace_id=workspace_id, user_id="ghost", role=Role.ADMIN)
        )
        raise AssertionError("expected MemberNotFoundError")
    except MemberNotFoundError:
        pass


async def test_remove_member_rejects_removing_last_owner() -> None:
    create, _, _, remove, _, _ = make_handlers()
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    try:
        await remove.handle(RemoveMemberCommand(workspace_id=workspace_id, user_id="user-1"))
        raise AssertionError("expected LastOwnerError")
    except LastOwnerError:
        pass


async def test_remove_member_removes_non_owner() -> None:
    create, invite, _, remove, _, workspaces = make_handlers()
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    await invite.handle(
        InviteMemberCommand(workspace_id=workspace_id, user_id="user-2", role=Role.VIEWER, invited_by="user-1")
    )
    await remove.handle(RemoveMemberCommand(workspace_id=workspace_id, user_id="user-2"))
    stored = await workspaces.get_by_id(workspace_id)
    assert stored is not None
    assert stored.get_member("user-2") is None


async def test_delete_workspace_removes_it() -> None:
    create, _, _, _, delete, workspaces = make_handlers()
    workspace_id = await create.handle(CreateWorkspaceCommand(name="Acme", owner_id="user-1"))
    await delete.handle(DeleteWorkspaceCommand(workspace_id=workspace_id))
    assert await workspaces.get_by_id(workspace_id) is None


async def test_delete_workspace_rejects_unknown_workspace() -> None:
    _, _, _, _, delete, _ = make_handlers()
    try:
        await delete.handle(DeleteWorkspaceCommand(workspace_id="missing"))
        raise AssertionError("expected WorkspaceNotFoundError")
    except WorkspaceNotFoundError:
        pass
