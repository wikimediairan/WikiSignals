from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    dbname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="en")
    language_script: Mapped[str | None] = mapped_column(String(32), nullable=True)
    text_direction: Mapped[str] = mapped_column(String(8), nullable=False, default="ltr")
    family: Mapped[str] = mapped_column(String(64), nullable=False, default="wikipedia")
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_namespaces: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    default_for_workspace: Mapped[bool] = mapped_column(Boolean, default=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    related_projects: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    campaign_filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    health_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    aqs_project: Mapped[str] = mapped_column(String(255), nullable=False)
    pageviews_project: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
