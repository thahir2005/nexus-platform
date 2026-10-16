"""add clerk user id

Revision ID: d37ad933f2e9
Revises: 37e13a19f607
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d37ad933f2e9"
down_revision: Union[str, Sequence[str], None] = "37e13a19f607"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("clerk_user_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_users_clerk_user_id",
        "users",
        ["clerk_user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_column("users", "clerk_user_id")
