"""cascade delete workspace members

Revision ID: 1831be91de81
Revises: 1cf0f1845ed7
Create Date: 2026-10-02 22:08:57.298190
"""

from alembic import op

revision = '1831be91de81'
down_revision = '1cf0f1845ed7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("workspace_members_workspace_id_fkey"), "workspace_members", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("workspace_members_workspace_id_fkey"),
        "workspace_members",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("workspace_members_workspace_id_fkey"), "workspace_members", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("workspace_members_workspace_id_fkey"),
        "workspace_members",
        "workspaces",
        ["workspace_id"],
        ["id"],
    )
