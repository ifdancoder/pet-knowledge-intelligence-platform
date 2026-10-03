from sqlalchemy.ext.asyncio import AsyncSession

from app.workspaces.repository import (
    SqlAlchemyWorkspaceMemberRepository,
    SqlAlchemyWorkspaceRepository,
)
from infrastructure.database.auth.models import UserModel as User


async def _make_user(db_session: AsyncSession, email: str) -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.flush()
    return user


async def test_workspace_repository_create_get_delete(db_session: AsyncSession) -> None:
    repo = SqlAlchemyWorkspaceRepository(db_session)
    workspace = await repo.create(name="Acme", slug="acme")
    assert await repo.get_by_id(workspace.id) == workspace
    await repo.delete(workspace)
    assert await repo.get_by_id(workspace.id) is None


async def test_workspace_member_repository(db_session: AsyncSession) -> None:
    owner = await _make_user(db_session, "owner@example.com")
    other = await _make_user(db_session, "other@example.com")
    workspaces = SqlAlchemyWorkspaceRepository(db_session)
    workspace = await workspaces.create(name="Acme", slug="acme")

    members = SqlAlchemyWorkspaceMemberRepository(db_session)
    owner_membership = await members.add(
        workspace_id=workspace.id, user_id=owner.id, role="owner", invited_by=None
    )
    await members.add(workspace_id=workspace.id, user_id=other.id, role="viewer", invited_by=owner.id)

    assert await members.get(workspace_id=workspace.id, user_id=owner.id) == owner_membership
    assert len(await members.list_for_workspace(workspace.id)) == 2
    assert await members.count_owners(workspace.id) == 1

    await members.update_role(owner_membership, role="admin")
    assert await members.count_owners(workspace.id) == 0

    other_membership = await members.get(workspace_id=workspace.id, user_id=other.id)
    assert other_membership is not None
    await members.remove(other_membership)
    assert len(await members.list_for_workspace(workspace.id)) == 1
