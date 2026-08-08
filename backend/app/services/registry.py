"""Load project and metric definitions from YAML into the database."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.annotation import Annotation
from app.models.metric import MetricDefinition
from app.models.project import Project

logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def health_config_version(health: dict[str, Any] | None) -> str:
    payload = json.dumps(health or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


async def seed_projects(session: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    projects_dir = settings.resolved_config_dir / "projects"
    if not projects_dir.is_dir():
        logger.warning("Projects config dir missing: %s", projects_dir)
        return 0
    count = 0
    for path in sorted(projects_dir.glob("*.yaml")):
        data = _load_yaml(path) or {}
        project_id = data["id"]
        existing = await session.get(Project, project_id)
        fields = {
            "domain": data["domain"],
            "dbname": data.get("dbname"),
            "language": data.get("language", "en"),
            "language_script": data.get("language_script"),
            "text_direction": data.get("text_direction", "ltr"),
            "family": data.get("family", "wikipedia"),
            "display_name": data.get("display_name", project_id),
            "content_namespaces": data.get("content_namespaces") or [0],
            "default_for_workspace": bool(data.get("default_for_workspace", False)),
            "features": data.get("features") or {},
            "related_projects": data.get("related_projects") or [],
            "campaign_filters": data.get("campaign_filters") or {},
            "health_config": data.get("health") or {},
            "aqs_project": data.get("aqs_project") or data["domain"],
            "pageviews_project": data.get("pageviews_project") or project_id,
            "enabled": bool(data.get("enabled", True)),
            "notes": data.get("notes"),
            "sort_order": int(data.get("sort_order", 100)),
        }
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
        else:
            session.add(Project(id=project_id, **fields))
        count += 1
    await session.commit()
    return count


async def seed_metrics(session: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    catalog = settings.resolved_config_dir / "metrics" / "catalog.yaml"
    if not catalog.is_file():
        logger.warning("Metric catalog missing: %s", catalog)
        return 0
    data = _load_yaml(catalog) or {}
    metrics = data.get("metrics") or []
    count = 0
    for m in metrics:
        mid = m["id"]
        existing = await session.get(MetricDefinition, mid)
        definition = m["definition"]
        methodology = m["methodology"]
        if isinstance(definition, str):
            definition = definition.strip()
        if isinstance(methodology, str):
            methodology = methodology.strip()
        fields = {
            "display_name": m["display_name"],
            "definition": definition,
            "methodology": methodology,
            "source": m.get("source", "aqs"),
            "unit": m.get("unit", "count"),
            "intervals": m.get("intervals") or ["month"],
            "caveats": (m.get("caveats") or "").strip() or None if isinstance(m.get("caveats"), str) else m.get("caveats"),
            "privacy_notes": (m.get("privacy_notes") or "").strip() or None
            if isinstance(m.get("privacy_notes"), str)
            else m.get("privacy_notes"),
            "status": m.get("status", "stable"),
            "module": m.get("module", "overview"),
            "sort_order": int(m.get("sort_order", 100)),
            "domain": m.get("domain", "context"),
            "role": m.get("role", "official_context"),
            "numerator": m.get("numerator"),
            "denominator": m.get("denominator"),
            "formula": m.get("formula"),
            "metric_version": m.get("metric_version", "1.0.0"),
            "source_endpoint": m.get("source_endpoint"),
            "provenance_notes": m.get("provenance_notes"),
            "deprecation": m.get("deprecation"),
        }
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
        else:
            session.add(MetricDefinition(id=mid, **fields))
        count += 1
    await session.commit()
    return count


async def seed_annotations(session: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    path = settings.resolved_config_dir / "annotations" / "examples.yaml"
    if not path.is_file():
        return 0
    data = _load_yaml(path) or {}
    items = data.get("annotations") or []
    existing = (await session.execute(select(Annotation))).scalars().all()
    keys = {(a.project_id, a.start_date.isoformat(), a.title) for a in existing}
    count = 0
    for item in items:
        key = (item.get("project_id"), item["start_date"], item["title"])
        if key in keys:
            continue
        session.add(
            Annotation(
                project_id=item.get("project_id"),
                start_date=date.fromisoformat(item["start_date"]),
                end_date=date.fromisoformat(item["end_date"]) if item.get("end_date") else None,
                title=item["title"],
                description=item.get("description"),
                source_url=item.get("source_url"),
                category=item.get("category"),
                visibility=item.get("visibility") or "public",
                created_by=item.get("created_by") or "seed",
            )
        )
        count += 1
    await session.commit()
    return count


async def bootstrap_registry(session: AsyncSession, settings: Settings | None = None) -> dict[str, int]:
    return {
        "projects": await seed_projects(session, settings),
        "metrics": await seed_metrics(session, settings),
        "annotations": await seed_annotations(session, settings),
    }
