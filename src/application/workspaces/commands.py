from dataclasses import dataclass

from domain.workspaces.entities import Role


@dataclass(frozen=True)
class CreateWorkspaceCommand:
    name: str
    owner_id: str


@dataclass(frozen=True)
class InviteMemberCommand:
    workspace_id: str
    user_id: str
    role: Role
    invited_by: str


@dataclass(frozen=True)
class ChangeMemberRoleCommand:
    workspace_id: str
    user_id: str
    role: Role


@dataclass(frozen=True)
class RemoveMemberCommand:
    workspace_id: str
    user_id: str


@dataclass(frozen=True)
class DeleteWorkspaceCommand:
    workspace_id: str
