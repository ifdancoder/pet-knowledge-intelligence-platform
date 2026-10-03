from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from domain.workspaces.exceptions import LastOwnerError, MemberNotFoundError
from shared.ids import generate_id


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(str, Enum):
    VIEW_WORKSPACE = "view_workspace"
    MANAGE_SOURCES = "manage_sources"
    MANAGE_MEMBERS = "manage_members"
    DELETE_WORKSPACE = "delete_workspace"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset(
        {Permission.VIEW_WORKSPACE, Permission.MANAGE_SOURCES, Permission.MANAGE_MEMBERS}
    ),
    Role.MEMBER: frozenset({Permission.VIEW_WORKSPACE, Permission.MANAGE_SOURCES}),
    Role.VIEWER: frozenset({Permission.VIEW_WORKSPACE}),
}


def check_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]


def _slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "workspace"


@dataclass
class WorkspaceMember:
    user_id: str
    role: Role
    invited_by: str | None = None


@dataclass
class Workspace:
    id: str
    name: str
    slug: str
    members: list[WorkspaceMember] = field(default_factory=list)

    @classmethod
    def create(cls, *, name: str, owner_id: str) -> Workspace:
        workspace = cls(id=generate_id(), name=name, slug=_slugify(name), members=[])
        workspace.members.append(WorkspaceMember(user_id=owner_id, role=Role.OWNER))
        return workspace

    def get_member(self, user_id: str) -> WorkspaceMember | None:
        return next((m for m in self.members if m.user_id == user_id), None)

    def _count_owners(self) -> int:
        return sum(1 for m in self.members if m.role == Role.OWNER)

    def invite_member(self, *, user_id: str, role: Role, invited_by: str) -> None:
        self.members.append(WorkspaceMember(user_id=user_id, role=role, invited_by=invited_by))

    def change_member_role(self, user_id: str, new_role: Role) -> None:
        member = self.get_member(user_id)
        if member is None:
            raise MemberNotFoundError(user_id)
        if member.role == Role.OWNER and new_role != Role.OWNER and self._count_owners() <= 1:
            raise LastOwnerError(self.id)
        member.role = new_role

    def remove_member(self, user_id: str) -> None:
        member = self.get_member(user_id)
        if member is None:
            raise MemberNotFoundError(user_id)
        if member.role == Role.OWNER and self._count_owners() <= 1:
            raise LastOwnerError(self.id)
        self.members.remove(member)
