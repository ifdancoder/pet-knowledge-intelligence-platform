from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workspaces.models import Workspace, WorkspaceMember
from app.workspaces.permissions import Role


class WorkspaceRepository(Protocol):
    async def create(self, *, name: str, slug: str) -> Workspace: ...
    async def get_by_id(self, workspace_id: str) -> Workspace | None: ...
    async def delete(self, workspace: Workspace) -> None: ...


class WorkspaceMemberRepository(Protocol):
    async def add(
        self, *, workspace_id: str, user_id: str, role: str, invited_by: str | None
    ) -> WorkspaceMember: ...
    async def get(self, *, workspace_id: str, user_id: str) -> WorkspaceMember | None: ...
    async def list_for_workspace(self, workspace_id: str) -> list[WorkspaceMember]: ...
    async def update_role(self, member: WorkspaceMember, *, role: str) -> None: ...
    async def remove(self, member: WorkspaceMember) -> None: ...
    async def count_owners(self, workspace_id: str) -> int: ...


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str, slug: str) -> Workspace:
        workspace = Workspace(name=name, slug=slug)
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        result = await self._session.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()

    async def delete(self, workspace: Workspace) -> None:
        await self._session.delete(workspace)
        await self._session.flush()


class SqlAlchemyWorkspaceMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, *, workspace_id: str, user_id: str, role: str, invited_by: str | None
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id, user_id=user_id, role=role, invited_by=invited_by
        )
        self._session.add(member)
        await self._session.flush()
        return member

    async def get(self, *, workspace_id: str, user_id: str) -> WorkspaceMember | None:
        result = await self._session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_workspace(self, workspace_id: str) -> list[WorkspaceMember]:
        result = await self._session.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def update_role(self, member: WorkspaceMember, *, role: str) -> None:
        member.role = role
        await self._session.flush()

    async def remove(self, member: WorkspaceMember) -> None:
        await self._session.delete(member)
        await self._session.flush()

    async def count_owners(self, workspace_id: str) -> int:
        members = await self.list_for_workspace(workspace_id)
        return sum(1 for member in members if member.role == Role.OWNER.value)
