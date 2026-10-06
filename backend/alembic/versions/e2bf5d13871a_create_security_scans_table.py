"""create security scans table

Revision ID: e2bf5d13871a
Revises: 2bc773df7bd4
Create Date: 2026-10-06 21:19:44.242441
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2bf5d13871a"
down_revision: Union[str, Sequence[str], None] = "2bc773df7bd4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "security_scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("build_id", sa.Integer(), nullable=True),
        sa.Column("image_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("unknown_count", sa.Integer(), nullable=False),
        sa.Column("low_count", sa.Integer(), nullable=False),
        sa.Column("medium_count", sa.Integer(), nullable=False),
        sa.Column("high_count", sa.Integer(), nullable=False),
        sa.Column("critical_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["build_id"],
            ["builds.id"],
            name="fk_security_scans_build_id_builds",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_security_scans_project_id_projects",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_security_scans_project_id",
        "security_scans",
        ["project_id"],
        unique=False,
    )

    op.create_index(
        "ix_security_scans_build_id",
        "security_scans",
        ["build_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_scans_build_id",
        table_name="security_scans",
    )

    op.drop_index(
        "ix_security_scans_project_id",
        table_name="security_scans",
    )

    op.drop_table("security_scans")
