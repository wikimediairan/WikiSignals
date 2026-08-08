from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectOut(BaseModel):
    id: str
    domain: str
    dbname: str | None = None
    language: str
    language_script: str | None = None
    text_direction: str
    family: str
    display_name: str
    content_namespaces: list[Any] = Field(default_factory=list)
    default_for_workspace: bool = False
    features: dict[str, Any] = Field(default_factory=dict)
    related_projects: list[Any] = Field(default_factory=list)
    health_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    notes: str | None = None
    sort_order: int = 100

    model_config = {"from_attributes": True}


class MetricDefinitionOut(BaseModel):
    id: str
    display_name: str
    definition: str
    methodology: str
    source: str
    unit: str
    intervals: list[Any] = Field(default_factory=list)
    caveats: str | None = None
    privacy_notes: str | None = None
    status: str
    module: str
    sort_order: int = 100
    domain: str = "context"
    role: str = "official_context"
    numerator: str | None = None
    denominator: str | None = None
    formula: str | None = None
    metric_version: str = "1.0.0"
    source_endpoint: str | None = None
    provenance_notes: str | None = None
    deprecation: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class SeriesPointOut(BaseModel):
    period_start: date
    value: float
    source: str | None = None


class MetricSeriesOut(BaseModel):
    project_id: str
    metric_id: str
    interval: str
    start: date
    end: date
    status: str
    definition: MetricDefinitionOut | None = None
    points: list[SeriesPointOut]
    unavailable_reason: str | None = None


class BatchMetricsOut(BaseModel):
    project_id: str
    interval: str
    start: date
    end: date
    series: dict[str, MetricSeriesOut]


class CompareOut(BaseModel):
    metric_id: str
    interval: str
    start: date
    end: date
    normalize: str | None = None
    disclaimer: str
    series: dict[str, list[SeriesPointOut]]


class AnnotationOut(BaseModel):
    id: int
    project_id: str | None
    start_date: date
    end_date: date | None
    title: str
    description: str | None
    source_url: str | None
    created_by: str | None

    model_config = {"from_attributes": True}


class TopPagesOut(BaseModel):
    project_id: str
    snapshot_type: str
    period_start: date | None
    items: list[dict[str, Any]]
    source: str | None = None


class CohortStageOut(BaseModel):
    stage: str
    value: float


class CohortOut(BaseModel):
    project_id: str
    cohort_month: date
    stages: list[CohortStageOut]


class CohortsResponse(BaseModel):
    project_id: str
    available: bool
    reason: str | None = None
    cohorts: list[CohortOut]


class HealthOut(BaseModel):
    status: str
    service: str
    version: str
    frontend: str
    default_project_id: str
    last_successful_ingest: datetime | None = None


class MethodologyOut(BaseModel):
    timezone: str
    intervals: dict[str, str]
    privacy_summary: str
    metrics: list[MetricDefinitionOut]
