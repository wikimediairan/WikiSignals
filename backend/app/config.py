from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

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
    # Auto-filled on Toolforge if DATABASE_URL is unset (see model_post_init)
    tool_toolsdb_user: str = ""
    tool_toolsdb_password: str = ""
    toolsdb_host: str = "tools.db.svc.wikimedia.cloud"
    toolsdb_name: str = ""  # default: {user}__wikisignals

    db_pool_recycle_seconds: int = 180
    db_pool_size: int = 5
    db_max_overflow: int = 5

    redis_url: str = ""
    redis_key_prefix: str = "wikisignals:"

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
    # Toolforge injects these for wiki replicas
    tool_replica_user: str = ""
    tool_replica_password: str = ""
    wiki_replicas_port: int = 3306
    # Abort long replica statements (seconds). Keeps shared replicas healthy.
    wiki_replicas_max_statement_time: float = 30.0
    wiki_replicas_connect_timeout: float = 10.0
    # Skip replica work if heartbeat lag exceeds this (seconds); 0 = do not check
    wiki_replicas_max_lag_seconds: int = 600

    # Paths: prefer /config mount in Docker, else repo config/
    config_dir: str = ""

    def model_post_init(self, __context: object) -> None:
        # ToolsDB: prefer explicit non-local DATABASE_URL; else compose from Toolforge envvars
        defaultish = (
            not self.database_url
            or "127.0.0.1" in self.database_url
            or "localhost" in self.database_url
            or "observatory:observatory@" in self.database_url
        )
        if defaultish and self.tool_toolsdb_user and self.tool_toolsdb_password:
            db_name = self.toolsdb_name or f"{self.tool_toolsdb_user}__wikisignals"
            user = quote_plus(self.tool_toolsdb_user)
            password = quote_plus(self.tool_toolsdb_password)
            object.__setattr__(
                self,
                "database_url",
                f"mysql+aiomysql://{user}:{password}@{self.toolsdb_host}:3306/{db_name}",
            )
        # Replicas: fill user/password from Toolforge if not set
        if self.tool_replica_user and not self.wiki_replicas_user:
            object.__setattr__(self, "wiki_replicas_user", self.tool_replica_user)
        if self.tool_replica_password and not self.wiki_replicas_password:
            object.__setattr__(self, "wiki_replicas_password", self.tool_replica_password)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_config_dir(self) -> Path:
        """Find config/ containing projects/*.yaml (buildpack, docker, or local).

        Never trust CONFIG_DIR alone if it has no project YAMLs (Toolforge often
        still has CONFIG_DIR=/config from older Docker docs).
        """
        candidates: list[Path] = []
        if self.config_dir:
            candidates.append(Path(self.config_dir))
        candidates.extend(
            [
                _REPO_ROOT / "config",  # sibling of backend/ when app is backend/app
                Path("/workspace/config"),  # Toolforge buildpack workspace
                Path.cwd() / "config",
                Path.cwd().parent / "config",  # when cwd is backend/
                Path("/layers"),  # placeholder skipped below
                Path("/config"),  # only if it actually has YAMLs
                _BACKEND_DIR / "config",
            ]
        )
        # Prefer any candidate that has project YAML files
        for path in candidates:
            if path == Path("/layers"):
                continue
            try:
                projects = path / "projects"
                if path.is_dir() and projects.is_dir() and any(projects.glob("*.yaml")):
                    return path.resolve()
            except OSError:
                continue
        # Fall back to repo-root config even if empty (seed will fail loudly)
        return (_REPO_ROOT / "config").resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
