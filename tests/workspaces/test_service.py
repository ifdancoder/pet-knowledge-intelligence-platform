from app.workspaces.models import Workspace, WorkspaceMember
from app.workspaces.permissions import Role
from app.workspaces.service import (
    LastOwnerError,
    MemberNotFoundError,
    WorkspaceNotFoundError,
    WorkspaceService,
)


class FakeWorkspaceRepository:
    def __init__(self) -> None:
        self.workspaces_by_id: dict[str, Workspace] = {}
        self._next_id = 0

    async def create(self, *, name: str, slug: str) -> Workspace:
        self._next_id += 1
        workspace = Workspace(id=str(self._next_id), name=name, slug=slug)
        self.workspaces_by_id[workspace.id] = workspace
        return workspace

    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        return self.workspaces_by_id.get(workspace_id)

    async def delete(self, workspace: Workspace) -> None:
        self.workspaces_by_id.pop(workspace.id, None)


class FakeWorkspaceMemberRepository:
    def __init__(self) -> None:
        self.members: dict[tuple[str, str], WorkspaceMember] = {}

    async def add(
        self, *, workspace_id: str, user_id: str, role: str, invited_by: str | None
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id, user_id=user_id, role=role, invited_by=invited_by
        )
        self.members[(workspace_id, user_id)] = member
        return member

    async def get(self, *, workspace_id: str, user_id: str) -> WorkspaceMember | None:
        return self.members.get((workspace_id, user_id))

    async def list_for_workspace(self, workspace_id: str) -> list[WorkspaceMember]:
        return [m for (wid, _), m in self.members.items() if wid == workspace_id]

    async def update_role(self, member: WorkspaceMember, *, role: str) -> None:
        member.role = role

    async def remove(self, member: WorkspaceMember) -> None:
        self.members.pop((member.workspace_id, member.user_id), None)

    async def count_owners(self, workspace_id: str) -> int:
        return sum(
            1
            for (wid, _), m in self.members.items()
            if wid == workspace_id and m.role == Role.OWNER.value
        )


def make_service() -> tuple[WorkspaceService, FakeWorkspaceRepository, FakeWorkspaceMemberRepository]:
    workspaces = FakeWorkspaceRepository()
    members = FakeWorkspaceMemberRepository()
    return WorkspaceService(workspaces, members), workspaces, members


async def test_create_workspace_adds_creator_as_owner() -> None:
    service, _, members = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    membership = await members.get(workspace_id=workspace.id, user_id="user-1")
    assert membership is not None
    assert membership.role == Role.OWNER.value


async def test_invite_member_rejects_unknown_workspace() -> None:
    service, _, _ = make_service()
    try:
        await service.invite_member(
            workspace_id="missing", user_id="user-2", role=Role.VIEWER, invited_by="user-1"
        )
        raise AssertionError("expected WorkspaceNotFoundError")
    except WorkspaceNotFoundError:
        pass


async def test_invite_member_adds_membership() -> None:
    service, _, members = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    await service.invite_member(
        workspace_id=workspace.id, user_id="user-2", role=Role.VIEWER, invited_by="user-1"
    )
    membership = await members.get(workspace_id=workspace.id, user_id="user-2")
    assert membership is not None
    assert membership.role == Role.VIEWER.value


async def test_change_role_rejects_demoting_last_owner() -> None:
    service, _, _ = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    try:
        await service.change_role(workspace_id=workspace.id, user_id="user-1", role=Role.ADMIN)
        raise AssertionError("expected LastOwnerError")
    except LastOwnerError:
        pass


async def test_change_role_allows_demoting_when_another_owner_exists() -> None:
    service, _, members = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    await service.invite_member(
        workspace_id=workspace.id, user_id="user-2", role=Role.OWNER, invited_by="user-1"
    )
    await service.change_role(workspace_id=workspace.id, user_id="user-1", role=Role.ADMIN)
    membership = await members.get(workspace_id=workspace.id, user_id="user-1")
    assert membership is not None
    assert membership.role == Role.ADMIN.value


async def test_change_role_rejects_unknown_member() -> None:
    service, _, _ = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    try:
        await service.change_role(workspace_id=workspace.id, user_id="ghost", role=Role.ADMIN)
        raise AssertionError("expected MemberNotFoundError")
    except MemberNotFoundError:
        pass


async def test_remove_member_rejects_removing_last_owner() -> None:
    service, _, _ = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    try:
        await service.remove_member(workspace_id=workspace.id, user_id="user-1")
        raise AssertionError("expected LastOwnerError")
    except LastOwnerError:
        pass


async def test_remove_member_removes_non_owner() -> None:
    service, _, members = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    await service.invite_member(
        workspace_id=workspace.id, user_id="user-2", role=Role.VIEWER, invited_by="user-1"
    )
    await service.remove_member(workspace_id=workspace.id, user_id="user-2")
    assert await members.get(workspace_id=workspace.id, user_id="user-2") is None


async def test_delete_workspace_removes_it() -> None:
    service, workspaces, _ = make_service()
    workspace = await service.create_workspace(name="Acme", owner_id="user-1")
    await service.delete_workspace(workspace_id=workspace.id)
    assert await workspaces.get_by_id(workspace.id) is None


async def test_delete_workspace_rejects_unknown_workspace() -> None:
    service, _, _ = make_service()
    try:
        await service.delete_workspace(workspace_id="missing")
        raise AssertionError("expected WorkspaceNotFoundError")
    except WorkspaceNotFoundError:
        pass
