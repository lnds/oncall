"""Repositorio en memoria, con el mismo comportamiento que el de PostgreSQL.

Lo usan las pruebas para correr sin base de datos.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from itertools import count

from incidents.domain import Incident, Postmortem, Status, TimelineEntry
from incidents.repository import DuplicatePostmortem


class InMemoryRepository:
    def __init__(self) -> None:
        self._incidents: dict[int, Incident] = {}
        self._timeline: list[TimelineEntry] = []
        self._postmortems: dict[int, dict] = {}
        self._incident_ids = count(1)
        self._timeline_ids = count(1)
        self._postmortem_ids = count(1)

    def list_incidents(self, status: Status | None = None) -> list[Incident]:
        incidents = [i for i in self._incidents.values() if status is None or i.status == status]
        return sorted(incidents, key=lambda i: i.started_at, reverse=True)

    def get_incident(self, incident_id: int) -> Incident | None:
        return self._incidents.get(incident_id)

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
        incident_id = next(self._incident_ids)
        self._incidents[incident_id] = Incident(
            id=incident_id,
            service_id=service_id,
            service_name=service_name,
            title=title,
            severity=severity,
            status=Status.OPEN,
            started_at=at,
            resolved_at=None,
            created_by=created_by,
        )
        self.add_timeline(
            incident_id, author=created_by, message=f"Incident created: {title}", at=at
        )
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
        incident = self._incidents[incident_id]
        self._incidents[incident_id] = replace(incident, status=status, resolved_at=resolved_at)
        self.add_timeline(incident_id, author=author, message=f"Status changed to {status}", at=at)

    def add_timeline(self, incident_id: int, *, author: str, message: str, at: datetime) -> None:
        self._timeline.append(
            TimelineEntry(
                id=next(self._timeline_ids),
                incident_id=incident_id,
                timestamp=at,
                author=author,
                message=message,
            )
        )

    def timeline(self, incident_id: int) -> list[TimelineEntry]:
        entries = [t for t in self._timeline if t.incident_id == incident_id]
        return sorted(entries, key=lambda t: (t.timestamp, t.id))

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
        if any(p["incident_id"] == incident_id for p in self._postmortems.values()):
            raise DuplicatePostmortem()
        postmortem_id = next(self._postmortem_ids)
        self._postmortems[postmortem_id] = {
            "id": postmortem_id,
            "incident_id": incident_id,
            "summary": summary,
            "root_cause": root_cause,
            "impact": impact,
            "action_items": action_items,
            "lessons": lessons,
            "created_at": at,
        }
        self.add_timeline(incident_id, author=author, message="Post-mortem published", at=at)
        return postmortem_id

    def list_postmortems(self) -> list[Postmortem]:
        postmortems = [self._postmortem(p) for p in self._postmortems.values()]
        return sorted(postmortems, key=lambda p: p.created_at, reverse=True)

    def get_postmortem(self, postmortem_id: int) -> Postmortem | None:
        row = self._postmortems.get(postmortem_id)
        return self._postmortem(row) if row else None

    def _postmortem(self, row: dict) -> Postmortem:
        incident = self._incidents[row["incident_id"]]
        return Postmortem(
            **row,
            incident_title=incident.title,
            severity=incident.severity,
            service_name=incident.service_name,
        )
