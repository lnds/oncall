from datetime import UTC, datetime

import pytest

from incidents import domain
from incidents.domain import Incident, InvalidTransition, Status

NOW = datetime(2026, 10, 6, 22, 0, tzinfo=UTC)


def incident(status=Status.OPEN, resolved_at=None):
    return Incident(
        id=1,
        service_id=1,
        service_name="checkout",
        title="Latencia alta",
        severity=2,
        status=status,
        started_at=NOW,
        resolved_at=resolved_at,
        created_by="ana",
    )


@pytest.mark.parametrize("severity", [1, 2, 3, 4])
def test_valid_severities(severity):
    assert domain.is_valid_severity(severity)


@pytest.mark.parametrize("severity", [0, 5])
def test_invalid_severities(severity):
    assert not domain.is_valid_severity(severity)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (Status.OPEN, Status.INVESTIGATING),
        (Status.INVESTIGATING, Status.MITIGATED),
        (Status.MITIGATED, Status.RESOLVED),
        (Status.RESOLVED, Status.INVESTIGATING),
    ],
)
def test_allowed_transitions(current, target):
    assert domain.can_transition(current, target)


def test_cannot_reopen_resolved_incident_as_open():
    with pytest.raises(InvalidTransition):
        domain.check_transition(Status.RESOLVED, Status.OPEN)


def test_open_incident_can_be_resolved_directly():
    domain.check_transition(Status.OPEN, Status.RESOLVED)


def test_resolving_sets_resolved_at():
    assert domain.resolved_at_after(None, Status.RESOLVED, NOW) == NOW


def test_moving_to_investigating_keeps_resolved_at_empty():
    assert domain.resolved_at_after(None, Status.INVESTIGATING, NOW) is None


def test_postmortem_requires_resolved_incident():
    assert domain.can_write_postmortem(incident(Status.RESOLVED, NOW))
    assert not domain.can_write_postmortem(incident(Status.MITIGATED))


def test_notification_message():
    message = domain.notification_message(1, "Caída total", "checkout")
    assert "SEV1" in message
