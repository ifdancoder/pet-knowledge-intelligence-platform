import pytest

from domain.workspaces.entities import Permission, Role, Workspace, check_permission
from domain.workspaces.exceptions import LastOwnerError, MemberNotFoundError


def test_workspace_create_adds_owner() -> None:
    workspace = Workspace.create(name="Acme", owner_id="user-1")
    assert len(workspace.id) == 26
    assert workspace.slug == "acme"
    member = workspace.get_member("user-1")
    assert member is not None
    assert member.role == Role.OWNER


def test_workspace_create_slugifies_special_characters() -> None:
    workspace = Workspace.create(name="Acme & Co.", owner_id="user-1")
    assert workspace.slug == "acme-co"


def test_invite_member_adds_membership() -> None:
    workspace = Workspace.create(name="Acme", owner_id="user-1")
    workspace.invite_member(user_id="user-2", role=Role.VIEWER, invited_by="user-1")
    member = workspace.get_member("user-2")
    assert member is not None
    assert member.role == Role.VIEWER
    assert member.invited_by == "user-1"


def test_change_member_role_rejects_demoting_last_owner() -> None:
    workspace = Workspace.create(name="Acme", owner_id="user-1")
    with pytest.raises(LastOwnerError):
        workspace.change_member_role("user-1", Role.ADMIN)


def test_change_member_role_allows_demoting_when_another_owner_exists() -> None:
    workspace = Workspace.create(name="Acme", owner_id="user-1")
    workspace.invite_member(user_id="user-2", role=Role.OWNER, invited_by="user-1")
    workspace.change_member_role("user-1", Role.ADMIN)
    member = workspace.get_member("user-1")
    assert member is not None
    assert member.role == Role.ADMIN


def test_change_member_role_rejects_unknown_member() -> None:
    workspace = Workspace.create(name="Acme", owner_id="user-1")
    with pytest.raises(MemberNotFoundError):
        workspace.change_member_role("ghost", Role.ADMIN)


def test_remove_member_rejects_removing_last_owner() -> None:
    workspace = Workspace.create(name="Acme", owner_id="user-1")
    with pytest.raises(LastOwnerError):
        workspace.remove_member("user-1")


def test_remove_member_removes_non_owner() -> None:
    workspace = Workspace.create(name="Acme", owner_id="user-1")
    workspace.invite_member(user_id="user-2", role=Role.VIEWER, invited_by="user-1")
    workspace.remove_member("user-2")
    assert workspace.get_member("user-2") is None


def test_owner_has_every_permission() -> None:
    for permission in Permission:
        assert check_permission(Role.OWNER, permission) is True


def test_viewer_only_has_view_permission() -> None:
    assert check_permission(Role.VIEWER, Permission.VIEW_WORKSPACE) is True
    assert check_permission(Role.VIEWER, Permission.MANAGE_SOURCES) is False
    assert check_permission(Role.VIEWER, Permission.MANAGE_MEMBERS) is False
    assert check_permission(Role.VIEWER, Permission.DELETE_WORKSPACE) is False


def test_admin_can_manage_members_but_not_delete_workspace() -> None:
    assert check_permission(Role.ADMIN, Permission.MANAGE_MEMBERS) is True
    assert check_permission(Role.ADMIN, Permission.DELETE_WORKSPACE) is False


def test_member_can_manage_sources_but_not_members() -> None:
    assert check_permission(Role.MEMBER, Permission.MANAGE_SOURCES) is True
    assert check_permission(Role.MEMBER, Permission.MANAGE_MEMBERS) is False
