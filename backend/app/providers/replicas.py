"""Toolforge wiki replicas provider — conservative, parameterized, lag-aware."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from app.config import Settings, get_settings
from app.providers.base import SeriesPoint, SeriesResult
from app.security import is_safe_dbname

logger = logging.getLogger(__name__)


class ReplicasUnavailable(RuntimeError):
    pass


class WikiReplicasProvider:
    """
    Read-only MediaWiki analytics replicas (Toolforge).

    Safety rules:
    - Only whitelisted dbname patterns
    - Parameterized queries (no string-built SQL values except validated dbname)
    - max_statement_time / short timeouts
    - Optional lag gate via heartbeat
    - Aggregate-only result shapes (no user lists stored)
    """

    name = "replicas"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._conn: Any = None

    @property
    def available(self) -> bool:
        s = self.settings
        return bool(s.wiki_replicas_enabled and s.wiki_replicas_host and s.wiki_replicas_user)

    async def __aenter__(self) -> WikiReplicasProvider:
        if not self.available:
            return self
        try:
            import aiomysql  # type: ignore
        except ImportError as exc:
            raise ReplicasUnavailable("aiomysql not installed") from exc

        self._conn = await aiomysql.connect(
            host=self.settings.wiki_replicas_host,
            port=self.settings.wiki_replicas_port,
            user=self.settings.wiki_replicas_user,
            password=self.settings.wiki_replicas_password or "",
            autocommit=True,
            connect_timeout=self.settings.wiki_replicas_connect_timeout,
            charset="utf8mb4",
        )
        # Cap statement runtime on the session (MariaDB)
        async with self._conn.cursor() as cur:
            try:
                await cur.execute(
                    "SET SESSION max_statement_time = %s",
                    (float(self.settings.wiki_replicas_max_statement_time),),
                )
            except Exception:  # noqa: BLE001
                logger.debug("max_statement_time not supported on this server", exc_info=True)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _require(self) -> None:
        if not self.available or self._conn is None:
            raise ReplicasUnavailable(
                "Wiki replicas not configured. On Toolforge set WIKI_REPLICAS_* from replica.my.cnf."
            )

    def _use_db(self, dbname: str) -> str:
        if not is_safe_dbname(dbname):
            raise ReplicasUnavailable(f"Refusing unsafe replica dbname: {dbname!r}")
        # Analytics replicas often use {wiki}_p
        if not dbname.endswith("_p"):
            return f"{dbname}_p"
        return dbname

    async def check_lag_seconds(self) -> float | None:
        """Return approximate replication lag if heartbeat is available."""
        self._require()
        assert self._conn is not None
        async with self._conn.cursor() as cur:
            try:
                await cur.execute(
                    "SELECT TIMESTAMPDIFF(SECOND, ts, UTC_TIMESTAMP()) "
                    "FROM heartbeat_p.heartbeat ORDER BY ts DESC LIMIT 1"
                )
                row = await cur.fetchone()
                if row and row[0] is not None:
                    return float(row[0])
            except Exception:  # noqa: BLE001
                logger.debug("heartbeat lag check unavailable", exc_info=True)
        return None

    async def ensure_lag_ok(self) -> None:
        max_lag = self.settings.wiki_replicas_max_lag_seconds
        if not max_lag:
            return
        lag = await self.check_lag_seconds()
        if lag is not None and lag > max_lag:
            raise ReplicasUnavailable(
                f"Replica lag {lag:.0f}s exceeds limit {max_lag}s; skipping replica work"
            )

    async def fetch_reverts_monthly(
        self,
        dbname: str,
        start: date,
        end: date,
    ) -> SeriesResult:
        """
        Count revisions tagged mw-reverted per calendar month (UTC).

        Aggregate-only. Does not return user names.
        """
        self._require()
        await self.ensure_lag_ok()
        schema = self._use_db(dbname)
        assert self._conn is not None

        # Date bounds as strings for parameterization
        start_ts = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).strftime(
            "%Y%m%d%H%M%S"
        )
        end_ts = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).strftime(
            "%Y%m%d%H%M%S"
        )

        # Schema name cannot be parameterized in MySQL — validated above.
        sql = f"""
            SELECT LEFT(rev_timestamp, 6) AS ym, COUNT(*) AS c
            FROM `{schema}`.revision
            JOIN `{schema}`.change_tag ON ct_rev_id = rev_id
            JOIN `{schema}`.change_tag_def ON ctd_id = ct_tag_id
            WHERE ctd_name = %s
              AND rev_timestamp >= %s
              AND rev_timestamp <= %s
            GROUP BY ym
            ORDER BY ym
        """
        points: list[SeriesPoint] = []
        async with self._conn.cursor() as cur:
            await cur.execute(sql, ("mw-reverted", start_ts, end_ts))
            rows = await cur.fetchall()
            for ym, count in rows:
                # ym is YYYYMM
                y = int(str(ym)[0:4])
                m = int(str(ym)[4:6])
                points.append(SeriesPoint(period_start=date(y, m, 1), value=float(count)))
        return SeriesResult(metric_id="reverts.count", points=points, source="replica")

    async def fetch_active_admins_monthly(
        self,
        dbname: str,
        start: date,
        end: date,
        admin_groups: list[str] | None = None,
    ) -> SeriesResult:
        """
        Count distinct users in admin groups who performed a logged action in the period.

        Lightweight approximation using logging table + user_groups.
        Aggregate-only (no usernames returned).
        """
        self._require()
        await self.ensure_lag_ok()
        schema = self._use_db(dbname)
        groups = admin_groups or ["sysop"]
        # Validate group names
        safe_groups = [g for g in groups if re_group(g)]
        if not safe_groups:
            return SeriesResult(metric_id="capacity.active_admins", points=[], source="replica")

        start_ts = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).strftime(
            "%Y%m%d%H%M%S"
        )
        end_ts = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).strftime(
            "%Y%m%d%H%M%S"
        )
        placeholders = ",".join(["%s"] * len(safe_groups))
        sql = f"""
            SELECT LEFT(log_timestamp, 6) AS ym, COUNT(DISTINCT log_actor) AS c
            FROM `{schema}`.logging
            JOIN `{schema}`.actor ON actor_id = log_actor
            JOIN `{schema}`.user_groups ON ug_user = actor_user
            WHERE ug_group IN ({placeholders})
              AND log_timestamp >= %s
              AND log_timestamp <= %s
              AND log_type IN ('block','protect','delete','rights','move')
            GROUP BY ym
            ORDER BY ym
        """
        params: list[Any] = [*safe_groups, start_ts, end_ts]
        points: list[SeriesPoint] = []
        assert self._conn is not None
        async with self._conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            for ym, count in rows:
                y = int(str(ym)[0:4])
                m = int(str(ym)[4:6])
                points.append(SeriesPoint(period_start=date(y, m, 1), value=float(count)))
        return SeriesResult(metric_id="capacity.active_admins", points=points, source="replica")


def re_group(name: str) -> bool:
    return bool(name) and bool(__import__("re").match(r"^[a-z0-9_-]{1,64}$", name))
