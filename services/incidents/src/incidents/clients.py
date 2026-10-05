"""Clientes HTTP hacia catalog y notifications."""

from __future__ import annotations

from typing import Any, Protocol

import httpx


class ServiceUnavailable(Exception):
    pass


class Catalog(Protocol):
    def list_services(self) -> list[dict[str, Any]]: ...

    def get_service(self, service_id: int) -> dict[str, Any] | None: ...

    def current_oncall(self, service_id: int) -> dict[str, Any] | None: ...


class Notifications(Protocol):
    def notify(self, notification: dict[str, Any]) -> None: ...


class HttpCatalog:
    def __init__(self, base_url: str, timeout: float = 3.0):
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    def list_services(self) -> list[dict[str, Any]]:
        return self._get("/services") or []

    def get_service(self, service_id: int) -> dict[str, Any] | None:
        return self._get(f"/services/{service_id}")

    def current_oncall(self, service_id: int) -> dict[str, Any] | None:
        return self._get(f"/oncall/current/{service_id}")

    def _get(self, path: str) -> Any:
        try:
            response = self._http.get(path)
        except httpx.HTTPError as e:
            raise ServiceUnavailable("catalog") from e
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise ServiceUnavailable("catalog")
        return response.json()


class HttpNotifications:
    def __init__(self, base_url: str, timeout: float = 3.0):
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    def notify(self, notification: dict[str, Any]) -> None:
        try:
            response = self._http.post("/notify", json=notification)
        except httpx.HTTPError as e:
            raise ServiceUnavailable("notifications") from e
        if response.status_code >= 400:
            raise ServiceUnavailable("notifications")
