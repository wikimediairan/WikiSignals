from pathlib import Path

import yaml

from app.config import get_settings


def test_project_yamls_exist_and_fa_is_default():
    settings = get_settings()
    # Prefer repo config
    config = Path(__file__).resolve().parents[3] / "config" / "projects"
    if not config.is_dir():
        config = settings.resolved_config_dir / "projects"
    files = list(config.glob("*.yaml"))
    assert files, "expected project YAML files"
    defaults = []
    for f in files:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert "id" in data and "domain" in data
        assert "aqs_project" in data
        # no metric logic — just config
        if data.get("default_for_workspace"):
            defaults.append(data["id"])
    assert defaults == ["fa.wikipedia"]


def test_metric_catalog_has_active_editors():
    catalog = Path(__file__).resolve().parents[3] / "config" / "metrics" / "catalog.yaml"
    data = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    ids = {m["id"] for m in data["metrics"]}
    assert "editors.active" in ids
    assert "edits.total" in ids
    # funnel metrics documented
    assert "funnel.first_edit" in ids
