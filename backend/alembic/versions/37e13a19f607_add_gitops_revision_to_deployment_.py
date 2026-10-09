"""add gitops revision to deployment pipeline runs

Revision ID: 37e13a19f607
Revises: cde2412b5903
Create Date: 2026-10-09 01:18:12.461363

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "37e13a19f607"
down_revision: Union[str, Sequence[str], None] = "cde2412b5903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deployment_pipeline_runs",
        sa.Column(
            "gitops_revision",
            sa.String(length=100),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("deployment_pipeline_runs", "gitops_revision")