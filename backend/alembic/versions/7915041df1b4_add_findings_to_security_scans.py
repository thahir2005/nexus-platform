"""add findings to security scans

Revision ID: 7915041df1b4
Revises: fce0b4d5e689
Create Date: 2026-10-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7915041df1b4"
down_revision: Union[str, Sequence[str], None] = "fce0b4d5e689"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "security_scans",
        sa.Column(
            "findings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("security_scans", "findings")
