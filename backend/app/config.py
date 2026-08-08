from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ is CWD in Docker; repo root may hold config/
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", _REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "WikiSignals"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Must include a real contact URL or email — @localhost is often blocked with 403.
    # https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
    user_agent: str = (
        "WikiSignals/0.1 "
        "(https://github.com/wikimediairan/WikiSignals; "
        "contact@wikimediairan.org)"
    )

    database_url: str = "mysql+aiomysql://observatory:observatory@127.0.0.1:3308/observatory"
    db_pool_recycle_seconds: int = 180
    db_pool_size: int = 5
    db_max_overflow: int = 5

    redis_url: str = ""
    redis_key_prefix: str = "observatory:"

    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    default_project_id: str = "fa.wikipedia"
    public_cache_max_age_seconds: int = 3600

    # OpenAPI /docs — disable in production on Toolforge
    docs_enabled: bool = True

    http_timeout_seconds: float = 60.0
    http_max_retries: int = 5
    # Be polite to Wikimedia edges; increase if you still see 429/403 bursts
    http_min_interval_seconds: float = 0.5

    aqs_base_url: str = "https://wikimedia.org/api/rest_v1/metrics"
    ingest_default_months: int = 24
    ingest_lookback_periods: int = 3

    # Daily job budgets (protect Toolforge / AQS / replicas)
    daily_aqs_lookback_months: int = 3
    daily_admin_log_days: int = 35
    daily_admin_log_max_pages: int = 8
    daily_project_pause_seconds: float = 2.0
    daily_max_projects: int = 8
    daily_use_mediawiki_logs: bool = True
    daily_use_replicas: bool = True

    wiki_replicas_enabled: bool = False
    # e.g. fawiki.analytics.db.svc.wikimedia.cloud (per-wiki host) or analytics cluster
    wiki_replicas_host: str = ""
    wiki_replicas_user: str = ""
    wiki_replicas_password: str = ""
    wiki_replicas_port: int = 3306
    # Abort long replica statements (seconds). Keeps shared replicas healthy.
    wiki_replicas_max_statement_time: float = 30.0
    wiki_replicas_connect_timeout: float = 10.0
    # Skip replica work if heartbeat lag exceeds this (seconds); 0 = do not check
    wiki_replicas_max_lag_seconds: int = 600

    # Paths: prefer /config mount in Docker, else repo config/
    config_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_config_dir(self) -> Path:
        if self.config_dir:
            return Path(self.config_dir)
        docker_mount = Path("/config")
        if docker_mount.is_dir() and any(docker_mount.iterdir()):
            return docker_mount
        repo_config = _REPO_ROOT / "config"
        if repo_config.is_dir():
            return repo_config
        return _BACKEND_DIR / "config"


@lru_cache
def get_settings() -> Settings:
    return Settings()
