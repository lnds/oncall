"""API HTTP del servicio de incidentes."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

from incidents import domain
from incidents.clients import Catalog, Notifications, ServiceUnavailable
from incidents.domain import InvalidTransition, Status
from incidents.repository import DuplicatePostmortem, Repository

STATIC_DIR = Path(__file__).parent / "static"

log = logging.getLogger("incidents")


def utcnow() -> datetime:
    return datetime.now(UTC)


class NewIncident(BaseModel):
    title: str = Field(min_length=1)
    service_id: int
    severity: int
    created_by: str = "system"


class IncidentUpdate(BaseModel):
    status: str | None = None
    message: str | None = None
    author: str = "system"


class NewPostmortem(BaseModel):
    incident_id: int
    summary: str
    root_cause: str
    impact: str
    action_items: str
    lessons: str = ""
    author: str = "system"


class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def to_json(value: Any) -> Any:
    """Convierte dataclasses, enums y fechas a JSON con instantes en UTC y sufijo Z."""
    if is_dataclass(value) and not isinstance(value, type):
        return to_json(asdict(value))
    if isinstance(value, dict):
        return {k: to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_json(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def create_app(
    repo: Repository,
    catalog: Catalog,
    notifications: Notifications,
    clock: Callable[[], datetime] = utcnow,
) -> FastAPI:
    app = FastAPI(title="Oncall · incidents")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    registry = CollectorRegistry()
    request_count = Counter(
        "http_requests_total",
        "Requests HTTP atendidas",
        ["method", "endpoint", "status"],
        registry=registry,
    )
    request_latency = Histogram(
        "http_request_duration_seconds",
        "Latencia de las requests HTTP",
        ["endpoint"],
        registry=registry,
    )

    @app.middleware("http")
    async def record_metrics(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        endpoint = getattr(route, "path", "unknown")
        if endpoint != "/metrics":
            request_latency.labels(endpoint=endpoint).observe(time.perf_counter() - start)
            request_count.labels(request.method, endpoint, response.status_code).inc()
        return response

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError):
        return JSONResponse({"error": exc.message}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"] if p != "body")
        message = f"{field}: {first['msg']}" if field else first["msg"]
        return JSONResponse({"error": message}, status_code=400)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/catalog/services")
    def catalog_services():
        try:
            return catalog.list_services()
        except ServiceUnavailable as e:
            raise ApiError(502, "catalog-service unavailable") from e

    # --- Incidentes ---

    @app.get("/incidents")
    def list_incidents(status: str | None = None):
        if status is not None and status not in Status:
            raise ApiError(400, "invalid status")
        return to_json(repo.list_incidents(Status(status) if status else None))

    @app.post("/incidents", status_code=201)
    def create_incident(body: NewIncident):
        if not domain.is_valid_severity(body.severity):
            raise ApiError(400, "severity must be between 1 and 4")

        try:
            service = catalog.get_service(body.service_id)
        except ServiceUnavailable as e:
            raise ApiError(502, "catalog-service unavailable") from e
        if service is None:
            raise ApiError(404, "service not found")

        now = clock()
        incident_id = repo.create_incident(
            service_id=body.service_id,
            service_name=service["name"],
            title=body.title,
            severity=body.severity,
            created_by=body.created_by,
            at=now,
        )
        notification = notify_oncall(incident_id, body, service["name"])
        log.info(
            "incident_created",
            extra={"incident_id": incident_id, "service_id": body.service_id},
        )
        return {"id": incident_id, "notification": notification}

    def notify_oncall(incident_id: int, body: NewIncident, service_name: str) -> dict | None:
        try:
            oncall = catalog.current_oncall(body.service_id)
        except ServiceUnavailable:
            repo.add_timeline(
                incident_id,
                author="system",
                message="WARNING: catalog-service unavailable for on-call",
                at=clock(),
            )
            return None
        if oncall is None:
            repo.add_timeline(
                incident_id,
                author="system",
                message="WARNING: no on-call found for this service",
                at=clock(),
            )
            return None

        notification = {
            "person": oncall["person"],
            "email": oncall["email"],
            "message": domain.notification_message(body.severity, body.title, service_name),
            "incident_id": incident_id,
            "severity": body.severity,
        }
        try:
            notifications.notify(notification)
        except ServiceUnavailable:
            repo.add_timeline(
                incident_id,
                author="system",
                message="WARNING: notifications-service unavailable",
                at=clock(),
            )
            return None
        repo.add_timeline(
            incident_id,
            author="system",
            message=f"Notified {oncall['person']} ({oncall['email']})",
            at=clock(),
        )
        return notification

    @app.get("/incidents/{incident_id}")
    def get_incident(incident_id: int):
        incident = repo.get_incident(incident_id)
        if incident is None:
            raise ApiError(404, "incident not found")
        return to_json({**asdict(incident), "timeline": repo.timeline(incident_id)})

    @app.patch("/incidents/{incident_id}")
    def update_incident(incident_id: int, body: IncidentUpdate):
        if body.status is None and body.message is None:
            raise ApiError(400, "status or message is required")
        if body.status is not None and body.status not in Status:
            raise ApiError(400, "invalid status")

        incident = repo.get_incident(incident_id)
        if incident is None:
            raise ApiError(404, "incident not found")

        now = clock()
        if body.status is not None:
            target = Status(body.status)
            try:
                domain.check_transition(incident.status, target)
            except InvalidTransition as e:
                raise ApiError(409, str(e)) from e
            repo.change_status(
                incident_id,
                status=target,
                resolved_at=domain.resolved_at_after(incident.resolved_at, target, now),
                author=body.author,
                at=now,
            )
        if body.message:
            repo.add_timeline(incident_id, author=body.author, message=body.message, at=now)
        return {"ok": True}

    # --- Post-mortems ---

    @app.post("/postmortems", status_code=201)
    def create_postmortem(body: NewPostmortem):
        incident = repo.get_incident(body.incident_id)
        if incident is None:
            raise ApiError(404, "incident not found")
        if not domain.can_write_postmortem(incident):
            raise ApiError(409, "incident must be resolved before writing a post-mortem")
        try:
            postmortem_id = repo.create_postmortem(
                incident_id=body.incident_id,
                summary=body.summary,
                root_cause=body.root_cause,
                impact=body.impact,
                action_items=body.action_items,
                lessons=body.lessons,
                author=body.author,
                at=clock(),
            )
        except DuplicatePostmortem as e:
            raise ApiError(409, "post-mortem already exists for this incident") from e
        return {"id": postmortem_id}

    @app.get("/postmortems")
    def list_postmortems():
        return to_json(repo.list_postmortems())

    @app.get("/postmortems/{postmortem_id}")
    def get_postmortem(postmortem_id: int):
        postmortem = repo.get_postmortem(postmortem_id)
        if postmortem is None:
            raise ApiError(404, "post-mortem not found")
        return to_json(postmortem)

    return app
