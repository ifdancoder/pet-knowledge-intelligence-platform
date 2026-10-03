from dataclasses import dataclass


@dataclass(frozen=True)
class GetWorkspaceByIdQuery:
    workspace_id: str


@dataclass(frozen=True)
class GetWorkspaceMembersQuery:
    workspace_id: str
