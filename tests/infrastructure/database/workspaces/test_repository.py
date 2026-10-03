from sqlalchemy.ext.asyncio import AsyncSession

from domain.workspaces.entities import Role, Workspace
from infrastructure.database.auth.models import UserModel
from infrastructure.database.workspaces.repository import SqlAlchemyWorkspaceRepository


async def _make_user(db_session: AsyncSession, user_id: str, email: str) -> None:
    db_session.add(UserModel(id=user_id, email=email, hashed_password="x", is_active=True))
    await db_session.flush()


async def test_add_and_get_by_id_round_trips_the_aggregate(db_session: AsyncSession) -> None:
    await _make_user(db_session, "owner-1", "owner@example.com")
    repo = SqlAlchemyWorkspaceRepository(db_session)
    workspace = Workspace.create(name="Acme", owner_id="owner-1")

    await repo.add(workspace)

    fetched = await repo.get_by_id(workspace.id)
    assert fetched is not None
    assert fetched.name == "Acme"
    assert fetched.slug == "acme"
    assert len(fetched.members) == 1
    member = fetched.get_member("owner-1")
    assert member is not None
    assert member.role == Role.OWNER


async def test_get_by_id_returns_none_for_unknown_workspace(db_session: AsyncSession) -> None:
    repo = SqlAlchemyWorkspaceRepository(db_session)
    assert await repo.get_by_id("missing") is None


async def test_save_persists_new_and_changed_and_removed_members(db_session: AsyncSession) -> None:
    await _make_user(db_session, "owner-2", "owner2@example.com")
    await _make_user(db_session, "member-2", "member2@example.com")
    await _make_user(db_session, "member-3", "member3@example.com")
    repo = SqlAlchemyWorkspaceRepository(db_session)
    workspace = Workspace.create(name="Beta", owner_id="owner-2")
    await repo.add(workspace)

    workspace.invite_member(user_id="member-2", role=Role.VIEWER, invited_by="owner-2")
    workspace.invite_member(user_id="member-3", role=Role.MEMBER, invited_by="owner-2")
    await repo.save(workspace)

    reloaded = await repo.get_by_id(workspace.id)
    assert reloaded is not None
    assert len(reloaded.members) == 3

    reloaded.change_member_role("member-2", Role.ADMIN)
    reloaded.remove_member("member-3")
    await repo.save(reloaded)

    final = await repo.get_by_id(workspace.id)
    assert final is not None
    assert len(final.members) == 2
    member_2 = final.get_member("member-2")
    assert member_2 is not None
    assert member_2.role == Role.ADMIN
    assert final.get_member("member-3") is None


async def test_delete_removes_the_workspace_and_cascades_members(db_session: AsyncSession) -> None:
    await _make_user(db_session, "owner-3", "owner3@example.com")
    repo = SqlAlchemyWorkspaceRepository(db_session)
    workspace = Workspace.create(name="Gamma", owner_id="owner-3")
    await repo.add(workspace)

    await repo.delete(workspace)

    assert await repo.get_by_id(workspace.id) is None
