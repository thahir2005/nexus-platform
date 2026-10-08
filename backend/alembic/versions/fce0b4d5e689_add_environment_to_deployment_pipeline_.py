
"""add environment to deployment pipeline runs

Revision ID: fce0b4d5e689

Revises: b21f7e0c2ffb

Create Date: 2026-10-08 15:51:13.496613

"""

from typing import Sequence, Union

from alembic import op

import sqlalchemy as sa

revision: str = "fce0b4d5e689"

down_revision: Union[str, Sequence[str], None] = "b21f7e0c2ffb"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:

    op.add_column(

        "deployment_pipeline_runs",

        sa.Column("environment_id", sa.Integer(), nullable=True),

    )

    op.create_foreign_key(

        "fk_deployment_pipeline_runs_environment",

        "deployment_pipeline_runs",

        "environments",

        ["environment_id"],

        ["id"],

    )

    op.execute(

        "UPDATE deployment_pipeline_runs "

        "SET environment_id = 1 "

        "WHERE environment_id IS NULL"

    )

    op.alter_column(

        "deployment_pipeline_runs",

        "environment_id",

        nullable=False,

    )

def downgrade() -> None:

    op.drop_constraint(

        "fk_deployment_pipeline_runs_environment",

        "deployment_pipeline_runs",

        type_="foreignkey",

    )

    op.drop_column(

        "deployment_pipeline_runs",

        "environment_id",

    )

