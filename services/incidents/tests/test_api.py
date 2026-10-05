def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_index_serves_web_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Oncall" in response.text


def test_metrics(client):
    client.get("/health")
    assert "http_requests_total" in client.get("/metrics").text


# --- Crear incidentes ---


def test_create_incident(client, notifications):
    response = client.post(
        "/incidents", json={"title": "Caída de checkout", "service_id": 1, "severity": 1}
    )
    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert len(notifications.sent) == 1


def test_create_incident_copies_service_name(client, new_incident):
    incident_id = new_incident()
    incident = client.get(f"/incidents/{incident_id}").json()
    assert incident["service_name"] == "checkout"
    assert incident["status"] == "open"


def test_create_incident_requires_title(client):
    response = client.post("/incidents", json={"service_id": 1, "severity": 2})
    assert response.status_code == 400


def test_create_incident_rejects_invalid_severity(client):
    response = client.post("/incidents", json={"title": "x", "service_id": 1, "severity": 7})
    assert response.status_code == 400
    assert "severity" in response.json()["error"]


def test_create_incident_for_unknown_service(client):
    response = client.post("/incidents", json={"title": "x", "service_id": 99, "severity": 2})
    assert response.status_code == 404


def test_create_incident_when_catalog_is_down(client, catalog):
    catalog.down = True
    response = client.post("/incidents", json={"title": "x", "service_id": 1, "severity": 2})
    assert response.status_code == 502


def test_incident_without_oncall_is_still_created(client, catalog, notifications):
    catalog.oncall.clear()
    response = client.post("/incidents", json={"title": "x", "service_id": 1, "severity": 3})
    assert response.status_code == 201
    assert response.json()["notification"] is None
    assert notifications.sent == []


def test_incident_when_notifications_are_down(client, notifications, new_incident):
    notifications.down = True
    incident_id = new_incident()
    timeline = client.get(f"/incidents/{incident_id}").json()["timeline"]
    assert len(timeline) == 2


def test_notification_goes_to_oncall(notifications, new_incident):
    new_incident(severity=1)
    sent = notifications.sent[0]
    assert sent["email"] == "ana@example.com"


# --- Consultar incidentes ---


def test_list_incidents(client, new_incident):
    new_incident()
    new_incident()
    assert len(client.get("/incidents").json()) == 2


def test_list_incidents_by_status(client, new_incident):
    first = new_incident()
    new_incident()
    client.patch(f"/incidents/{first}", json={"status": "investigating"})
    investigating = client.get("/incidents?status=investigating").json()
    assert [i["id"] for i in investigating] == [first]


def test_list_incidents_with_invalid_status(client):
    assert client.get("/incidents?status=closed").status_code == 400


def test_get_unknown_incident(client):
    assert client.get("/incidents/42").status_code == 404


def test_timestamps_are_utc_iso(client, new_incident):
    incident = client.get(f"/incidents/{new_incident()}").json()
    assert incident["started_at"] == "2026-10-06T22:00:00Z"


# --- Actualizar incidentes ---


def test_change_status(client, new_incident):
    incident_id = new_incident()
    response = client.patch(f"/incidents/{incident_id}", json={"status": "investigating"})
    assert response.status_code == 200
    assert client.get(f"/incidents/{incident_id}").json()["status"] == "investigating"


def test_resolve_incident(client, clock, new_incident):
    incident_id = new_incident()
    clock.advance(minutes=45)
    client.patch(f"/incidents/{incident_id}", json={"status": "resolved"})
    incident = client.get(f"/incidents/{incident_id}").json()
    assert incident["resolved_at"] is not None


def test_invalid_transition_is_rejected(client, new_incident):
    incident_id = new_incident()
    client.patch(f"/incidents/{incident_id}", json={"status": "resolved"})
    response = client.patch(f"/incidents/{incident_id}", json={"status": "mitigated"})
    assert response.status_code == 409


def test_unknown_status_is_rejected(client, new_incident):
    response = client.patch(f"/incidents/{new_incident()}", json={"status": "closed"})
    assert response.status_code == 400


def test_add_message(client, new_incident):
    incident_id = new_incident()
    client.patch(
        f"/incidents/{incident_id}", json={"message": "Rollback en curso", "author": "ana"}
    )
    timeline = client.get(f"/incidents/{incident_id}").json()["timeline"]
    assert timeline[-1]["message"] == "Rollback en curso"


def test_update_requires_status_or_message(client, new_incident):
    response = client.patch(f"/incidents/{new_incident()}", json={"author": "ana"})
    assert response.status_code == 400


def test_update_unknown_incident(client):
    response = client.patch("/incidents/42", json={"status": "investigating"})
    assert response.status_code == 404


# --- Post-mortems ---


POSTMORTEM = {
    "summary": "Checkout no respondió durante 45 minutos",
    "root_cause": "Pool de conexiones agotado",
    "impact": "12% de las compras fallaron",
    "action_items": "Alarma sobre el pool; aumentar el límite",
}


def resolved_incident(client, new_incident):
    incident_id = new_incident()
    client.patch(f"/incidents/{incident_id}", json={"status": "resolved"})
    return incident_id


def test_create_postmortem(client, new_incident):
    incident_id = resolved_incident(client, new_incident)
    response = client.post("/postmortems", json={"incident_id": incident_id, **POSTMORTEM})
    assert response.status_code == 201


def test_postmortem_requires_resolved_incident(client, new_incident):
    response = client.post("/postmortems", json={"incident_id": new_incident(), **POSTMORTEM})
    assert response.status_code == 409


def test_only_one_postmortem_per_incident(client, new_incident):
    incident_id = resolved_incident(client, new_incident)
    client.post("/postmortems", json={"incident_id": incident_id, **POSTMORTEM})
    response = client.post("/postmortems", json={"incident_id": incident_id, **POSTMORTEM})
    assert response.status_code == 409


def test_postmortem_for_unknown_incident(client):
    response = client.post("/postmortems", json={"incident_id": 42, **POSTMORTEM})
    assert response.status_code == 404


def test_postmortem_requires_all_fields(client, new_incident):
    incident_id = resolved_incident(client, new_incident)
    response = client.post("/postmortems", json={"incident_id": incident_id, "summary": "x"})
    assert response.status_code == 400


def test_list_and_get_postmortems(client, new_incident):
    incident_id = resolved_incident(client, new_incident)
    postmortem_id = client.post(
        "/postmortems", json={"incident_id": incident_id, **POSTMORTEM}
    ).json()["id"]
    assert len(client.get("/postmortems").json()) == 1
    postmortem = client.get(f"/postmortems/{postmortem_id}").json()
    assert postmortem["incident_title"] == "Latencia alta en checkout"


def test_get_unknown_postmortem(client):
    assert client.get("/postmortems/42").status_code == 404


# --- Proxy al catálogo ---


def test_catalog_services_proxy(client):
    assert client.get("/catalog/services").json()[0]["name"] == "checkout"


def test_catalog_services_proxy_when_catalog_is_down(client, catalog):
    catalog.down = True
    assert client.get("/catalog/services").status_code == 502
