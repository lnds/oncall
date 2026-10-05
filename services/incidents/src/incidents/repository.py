"""Persistencia de incidentes, bitácora y post-mortems."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from psycopg import errors
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from incidents.domain import Incident, Postmortem, Status, TimelineEntry


class DuplicatePostmortem(Exception):
    pass


class Repository(Protocol):
    def list_incidents(self, status: Status | None = None) -> list[Incident]: ...

    def get_incident(self, incident_id: int) -> Incident | None: ...

    def create_incident(
        self,
        *,
        service_id: int,
        service_name: str,
        title: str,
        severity: int,
        created_by: str,
        at: datetime,
    ) -> int: ...

    def change_status(
        self,
        incident_id: int,
        *,
        status: Status,
        resolved_at: datetime | None,
        author: str,
        at: datetime,
    ) -> None: ...

    def add_timeline(
        self, incident_id: int, *, author: str, message: str, at: datetime
    ) -> None: ...

    def timeline(self, incident_id: int) -> list[TimelineEntry]: ...

    def create_postmortem(
        self,
        *,
        incident_id: int,
        summary: str,
        root_cause: str,
        impact: str,
        action_items: str,
        lessons: str,
        author: str,
        at: datetime,
    ) -> int: ...

    def list_postmortems(self) -> list[Postmortem]: ...

    def get_postmortem(self, postmortem_id: int) -> Postmortem | None: ...


_POSTMORTEM_SELECT = """
    SELECT p.*, i.title AS incident_title, i.severity, i.service_name
    FROM postmortems p JOIN incidents i ON p.incident_id = i.id
"""


def _incident(row: dict) -> Incident:
    return Incident(**{**row, "status": Status(row["status"])})


def _postmortem(row: dict) -> Postmortem:
    return Postmortem(**{**row, "lessons": row["lessons"] or ""})


class PostgresRepository:
    def __init__(self, database_url: str):
        self._pool = ConnectionPool(
            database_url, kwargs={"row_factory": dict_row}, min_size=1, max_size=10, open=True
        )

    def close(self) -> None:
        self._pool.close()

    def list_incidents(self, status: Status | None = None) -> list[Incident]:
        with self._pool.connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM incidents WHERE status = %s ORDER BY started_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM incidents ORDER BY started_at DESC").fetchall()
        return [_incident(r) for r in rows]

    def get_incident(self, incident_id: int) -> Incident | None:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT * FROM incidents WHERE id = %s", (incident_id,)).fetchone()
        return _incident(row) if row else None

    def create_incident(
        self,
        *,
        service_id: int,
        service_name: str,
        title: str,
        severity: int,
        created_by: str,
        at: datetime,
    ) -> int:
        with self._pool.connection() as conn:
            incident_id = conn.execute(
                "INSERT INTO incidents"
                " (service_id, service_name, title, severity, status, started_at, created_by)"
                " VALUES (%s, %s, %s, %s, 'open', %s, %s) RETURNING id",
                (service_id, service_name, title, severity, at, created_by),
            ).fetchone()["id"]
            self._insert_timeline(conn, incident_id, created_by, f"Incident created: {title}", at)
        return incident_id

    def change_status(
        self,
        incident_id: int,
        *,
        status: Status,
        resolved_at: datetime | None,
        author: str,
        at: datetime,
    ) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE incidents SET status = %s, resolved_at = %s WHERE id = %s",
                (status, resolved_at, incident_id),
            )
            self._insert_timeline(conn, incident_id, author, f"Status changed to {status}", at)

    def add_timeline(self, incident_id: int, *, author: str, message: str, at: datetime) -> None:
        with self._pool.connection() as conn:
            self._insert_timeline(conn, incident_id, author, message, at)

    def timeline(self, incident_id: int) -> list[TimelineEntry]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM incident_timeline WHERE incident_id = %s ORDER BY timestamp, id",
                (incident_id,),
            ).fetchall()
        return [TimelineEntry(**r) for r in rows]

    def create_postmortem(
        self,
        *,
        incident_id: int,
        summary: str,
        root_cause: str,
        impact: str,
        action_items: str,
        lessons: str,
        author: str,
        at: datetime,
    ) -> int:
        try:
            with self._pool.connection() as conn:
                postmortem_id = conn.execute(
                    "INSERT INTO postmortems"
                    " (incident_id, summary, root_cause, impact, action_items, lessons, created_at)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (incident_id, summary, root_cause, impact, action_items, lessons, at),
                ).fetchone()["id"]
                self._insert_timeline(conn, incident_id, author, "Post-mortem published", at)
        except errors.UniqueViolation as e:
            raise DuplicatePostmortem() from e
        return postmortem_id

    def list_postmortems(self) -> list[Postmortem]:
        with self._pool.connection() as conn:
            rows = conn.execute(_POSTMORTEM_SELECT + " ORDER BY p.created_at DESC").fetchall()
        return [_postmortem(r) for r in rows]

    def get_postmortem(self, postmortem_id: int) -> Postmortem | None:
        with self._pool.connection() as conn:
            row = conn.execute(_POSTMORTEM_SELECT + " WHERE p.id = %s", (postmortem_id,)).fetchone()
        return _postmortem(row) if row else None

    @staticmethod
    def _insert_timeline(conn, incident_id: int, author: str, message: str, at: datetime) -> None:
        conn.execute(
            "INSERT INTO incident_timeline (incident_id, timestamp, author, message)"
            " VALUES (%s, %s, %s, %s)",
            (incident_id, at, author, message),
        )
