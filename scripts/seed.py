"""Carga datos de ejemplo en un entorno recién levantado.

Crea tres servicios con su turno de guardia y abre un incidente, que recorre la
cadena completa: incidents → catalog (turno vigente) → notifications.

Uso: python scripts/seed.py
Solo usa la biblioteca estándar, así que corre igual en macOS, Linux y Windows.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

INCIDENTS = os.environ.get("INCIDENTS_URL", "http://localhost:8080")
CATALOG = os.environ.get("CATALOG_URL", "http://localhost:8081")

SERVICES = [
    ("checkout", "payments", 99.95, "Ana Soto", "ana@example.com"),
    ("search", "discovery", 99.9, "Bruno Díaz", "bruno@example.com"),
    ("notificaciones-push", "engagement", 99.5, "Carla Rojas", "carla@example.com"),
]


def post(url: str, body: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        return {"status": e.code, **json.load(e)}


def main() -> int:
    start = date.today() - timedelta(days=7)
    end = date.today() + timedelta(days=30)

    try:
        for name, team, slo, person, email in SERVICES:
            service = post(f"{CATALOG}/services", {"name": name, "team": team, "slo_target": slo})
            print(f"servicio {name}: {service}")
            if "id" not in service:
                continue
            shift = post(
                f"{CATALOG}/oncall",
                {
                    "service_id": service["id"],
                    "person": person,
                    "email": email,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                },
            )
            print(f"  turno de {person}: {shift}")

        incident = post(
            f"{INCIDENTS}/incidents",
            {"service_id": 1, "title": "Latencia alta en checkout", "severity": 2, "created_by": "ana"},
        )
        print(f"incidente: {incident}")
    except urllib.error.URLError as e:
        print(f"No pude conectarme ({e.reason}). ¿Está levantado el entorno?", file=sys.stderr)
        return 1

    print(f"\nListo. Abre {INCIDENTS} en el navegador.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
