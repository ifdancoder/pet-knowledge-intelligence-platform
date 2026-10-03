import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.auth.models import UserModel
from infrastructure.database.workspaces.models import WorkspaceMemberModel, WorkspaceModel


async def test_workspace_member_composite_key_is_unique(db_session: AsyncSession) -> None:
    user = UserModel(id="u1", email="owner@example.com", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.flush()

    workspace = WorkspaceModel(id="w1", name="Acme", slug="acme")
    db_session.add(workspace)
    await db_session.flush()

    db_session.add(WorkspaceMemberModel(workspace_id="w1", user_id="u1", role="owner"))
    await db_session.flush()

    db_session.add(WorkspaceMemberModel(workspace_id="w1", user_id="u1", role="admin"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_workspace_slug_must_be_unique(db_session: AsyncSession) -> None:
    db_session.add(WorkspaceModel(id="w2", name="Acme", slug="dup-slug"))
    await db_session.flush()
    db_session.add(WorkspaceModel(id="w3", name="Acme 2", slug="dup-slug"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
