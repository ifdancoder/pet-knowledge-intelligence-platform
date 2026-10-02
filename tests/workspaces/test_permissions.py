from app.workspaces.permissions import Permission, Role, check_permission


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
