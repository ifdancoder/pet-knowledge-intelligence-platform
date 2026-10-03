import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.workspaces.models import Workspace, WorkspaceMember
from infrastructure.database.auth.models import UserModel as User


async def test_workspace_member_composite_key_is_unique(db_session: AsyncSession) -> None:
    user = User(email="owner@example.com", hashed_password="x", is_active=True)
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(name="Acme", slug="acme")
    db_session.add(workspace)
    await db_session.flush()

    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner"))
    await db_session.flush()

    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_workspace_slug_must_be_unique(db_session: AsyncSession) -> None:
    db_session.add(Workspace(name="Acme", slug="dup-slug"))
    await db_session.flush()
    db_session.add(Workspace(name="Acme 2", slug="dup-slug"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
