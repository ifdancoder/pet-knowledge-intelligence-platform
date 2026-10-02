from pydantic import BaseModel, Field

from app.workspaces.permissions import Role


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str


class MemberResponse(BaseModel):
    user_id: str
    role: Role


class InviteMemberRequest(BaseModel):
    user_id: str
    role: Role


class UpdateMemberRoleRequest(BaseModel):
    role: Role
