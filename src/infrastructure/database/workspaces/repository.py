from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.workspaces.entities import Role, Workspace, WorkspaceMember
from infrastructure.database.workspaces.models import WorkspaceMemberModel, WorkspaceModel


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workspace: Workspace) -> None:
        self._session.add(WorkspaceModel(id=workspace.id, name=workspace.name, slug=workspace.slug))
        await self._session.flush()
        for member in workspace.members:
            self._session.add(
                WorkspaceMemberModel(
                    workspace_id=workspace.id,
                    user_id=member.user_id,
                    role=member.role.value,
                    invited_by=member.invited_by,
                )
            )
        await self._session.flush()

    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        result = await self._session.execute(select(WorkspaceModel).where(WorkspaceModel.id == workspace_id))
        workspace_model = result.scalar_one_or_none()
        if workspace_model is None:
            return None

        member_result = await self._session.execute(
            select(WorkspaceMemberModel).where(WorkspaceMemberModel.workspace_id == workspace_id)
        )
        members = [
            WorkspaceMember(user_id=m.user_id, role=Role(m.role), invited_by=m.invited_by)
            for m in member_result.scalars().all()
        ]
        return Workspace(id=workspace_model.id, name=workspace_model.name, slug=workspace_model.slug, members=members)

    async def save(self, workspace: Workspace) -> None:
        result = await self._session.execute(
            select(WorkspaceMemberModel).where(WorkspaceMemberModel.workspace_id == workspace.id)
        )
        existing_by_user = {m.user_id: m for m in result.scalars().all()}
        current_user_ids = {m.user_id for m in workspace.members}

        for member in workspace.members:
            existing = existing_by_user.get(member.user_id)
            if existing is not None:
                existing.role = member.role.value
            else:
                self._session.add(
                    WorkspaceMemberModel(
                        workspace_id=workspace.id,
                        user_id=member.user_id,
                        role=member.role.value,
                        invited_by=member.invited_by,
                    )
                )

        for user_id, model in existing_by_user.items():
            if user_id not in current_user_ids:
                await self._session.delete(model)

        await self._session.flush()

    async def delete(self, workspace: Workspace) -> None:
        result = await self._session.execute(select(WorkspaceModel).where(WorkspaceModel.id == workspace.id))
        model = result.scalar_one()
        await self._session.delete(model)
        await self._session.flush()

    async def list_by_user_id(self, user_id: str) -> list[Workspace]:
        member_result = await self._session.execute(
            select(WorkspaceMemberModel.workspace_id).where(WorkspaceMemberModel.user_id == user_id)
        )
        workspace_ids = [row[0] for row in member_result.all()]
        if not workspace_ids:
            return []

        result = await self._session.execute(
            select(WorkspaceModel).where(WorkspaceModel.id.in_(workspace_ids)).order_by(WorkspaceModel.id)
        )
        return [Workspace(id=m.id, name=m.name, slug=m.slug) for m in result.scalars().all()]
