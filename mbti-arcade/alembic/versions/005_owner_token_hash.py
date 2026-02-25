"""owner token hash on sessions

Revision ID: 005
Revises: 004
Create Date: 2026-02-25 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(
            sa.Column("owner_token_hash", sa.String(length=64), nullable=True)
        )
        batch_op.create_index(
            "ix_sessions_owner_token_hash",
            ["owner_token_hash"],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_index("ix_sessions_owner_token_hash")
        batch_op.drop_column("owner_token_hash")
