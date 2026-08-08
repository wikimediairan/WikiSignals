from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BacklogSnapshot(Base):
    __tablename__ = "backlog_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "track_id",
            "interval",
            "period_start",
            name="uq_backlog_snapshot",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    track_id: Mapped[str] = mapped_column(String(128), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    open_count: Mapped[float] = mapped_column(Float, nullable=False)
    entered: Mapped[float | None] = mapped_column(Float, nullable=True)
    left: Mapped[float | None] = mapped_column(Float, nullable=True)
    net: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="mediawiki")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessSnapshot(Base):
    __tablename__ = "process_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "track_id",
            "interval",
            "period_start",
            name="uq_process_snapshot",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    track_id: Mapped[str] = mapped_column(String(128), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    open_count: Mapped[float] = mapped_column(Float, nullable=False)
    opened: Mapped[float | None] = mapped_column(Float, nullable=True)
    closed: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="mediawiki")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
