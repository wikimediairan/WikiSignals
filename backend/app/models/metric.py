from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    methodology: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="count")
    intervals: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    caveats: Mapped[str | None] = mapped_column(Text, nullable=True)
    privacy_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="stable")
    module: Mapped[str] = mapped_column(String(64), nullable=False, default="overview")
    sort_order: Mapped[int] = mapped_column(default=100)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, default="context")
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="official_context")
    numerator: Mapped[str | None] = mapped_column(Text, nullable=True)
    denominator: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    source_endpoint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provenance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deprecation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class MetricPoint(Base):
    __tablename__ = "metric_points"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "metric_id",
            "interval",
            "period_start",
            "dimensions_hash",
            name="uq_metric_point",
        ),
        Index("ix_metric_points_lookup", "project_id", "metric_id", "interval", "period_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metric_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    dimensions_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="aqs")
    quality_flags: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metric_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    source_retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PageSnapshot(Base):
    __tablename__ = "page_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "snapshot_type",
            "interval",
            "period_start",
            name="uq_page_snapshot",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(64), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="aqs")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
