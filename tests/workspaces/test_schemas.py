import pytest
from pydantic import ValidationError

from app.workspaces.permissions import Role
from app.workspaces.schemas import CreateWorkspaceRequest, InviteMemberRequest


def test_create_workspace_request_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        CreateWorkspaceRequest(name="")


def test_create_workspace_request_accepts_valid_name() -> None:
    assert CreateWorkspaceRequest(name="Acme").name == "Acme"


def test_invite_member_request_accepts_role_enum_value() -> None:
    request = InviteMemberRequest(user_id="user-1", role="viewer")
    assert request.role is Role.VIEWER
