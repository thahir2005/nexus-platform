"""add rollback reference to kubernetes deployments

Revision ID: cde2412b5903
Revises: 7915041df1b4
Create Date: 2026-10-08 22:55:01.982556

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cde2412b5903"
down_revision: Union[str, Sequence[str], None] = "7915041df1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kubernetes_deployments",
        sa.Column("rollback_of_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_kubernetes_deployments_rollback_of_id",
        "kubernetes_deployments",
        ["rollback_of_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_kubernetes_deployments_rollback_of_id",
        "kubernetes_deployments",
        "kubernetes_deployments",
        ["rollback_of_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_kubernetes_deployments_rollback_of_id",
        "kubernetes_deployments",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_kubernetes_deployments_rollback_of_id",
        table_name="kubernetes_deployments",
    )

    op.drop_column(
        "kubernetes_deployments",
        "rollback_of_id",
    )
