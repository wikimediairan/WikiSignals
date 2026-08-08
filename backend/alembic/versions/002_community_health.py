"""community health schema extensions

Revision ID: 002
Revises: 001
Create Date: 2026-03-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("metric_definitions") as batch:
        batch.add_column(sa.Column("domain", sa.String(length=64), nullable=False, server_default="context"))
        batch.add_column(sa.Column("role", sa.String(length=64), nullable=False, server_default="official_context"))
        batch.add_column(sa.Column("numerator", sa.Text(), nullable=True))
        batch.add_column(sa.Column("denominator", sa.Text(), nullable=True))
        batch.add_column(sa.Column("formula", sa.Text(), nullable=True))
        batch.add_column(sa.Column("metric_version", sa.String(length=32), nullable=False, server_default="1.0.0"))
        batch.add_column(sa.Column("source_endpoint", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("provenance_notes", sa.Text(), nullable=True))
        batch.add_column(sa.Column("deprecation", sa.JSON(), nullable=True))

    with op.batch_alter_table("metric_points") as batch:
        batch.add_column(sa.Column("metric_version", sa.String(length=32), nullable=False, server_default="1"))
        batch.add_column(sa.Column("config_version", sa.String(length=64), nullable=False, server_default=""))
        batch.add_column(sa.Column("source_retrieved_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("health_config", sa.JSON(), nullable=False, server_default="{}"))

    with op.batch_alter_table("annotations") as batch:
        batch.add_column(sa.Column("category", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"))

    op.create_table(
        "backlog_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("track_id", sa.String(length=128), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("open_count", sa.Float(), nullable=False),
        sa.Column("entered", sa.Float(), nullable=True),
        sa.Column("left", sa.Float(), nullable=True),
        sa.Column("net", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("config_version", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "track_id",
            "interval",
            "period_start",
            name="uq_backlog_snapshot",
        ),
    )
    op.create_index("ix_backlog_snapshots_project", "backlog_snapshots", ["project_id"])

    op.create_table(
        "process_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("track_id", sa.String(length=128), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("open_count", sa.Float(), nullable=False),
        sa.Column("opened", sa.Float(), nullable=True),
        sa.Column("closed", sa.Float(), nullable=True),
        sa.Column("median_days", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("config_version", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "track_id",
            "interval",
            "period_start",
            name="uq_process_snapshot",
        ),
    )
    op.create_index("ix_process_snapshots_project", "process_snapshots", ["project_id"])


def downgrade() -> None:
    op.drop_table("process_snapshots")
    op.drop_table("backlog_snapshots")
    with op.batch_alter_table("annotations") as batch:
        batch.drop_column("visibility")
        batch.drop_column("category")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("health_config")
    with op.batch_alter_table("metric_points") as batch:
        batch.drop_column("source_retrieved_at")
        batch.drop_column("config_version")
        batch.drop_column("metric_version")
    with op.batch_alter_table("metric_definitions") as batch:
        batch.drop_column("deprecation")
        batch.drop_column("provenance_notes")
        batch.drop_column("source_endpoint")
        batch.drop_column("metric_version")
        batch.drop_column("formula")
        batch.drop_column("denominator")
        batch.drop_column("numerator")
        batch.drop_column("role")
        batch.drop_column("domain")
