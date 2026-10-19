from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.v1 import audit as audit_api
from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.infrastructure.database import audit_logs
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app

client = TestClient(app)


def _override_membership(user_id, organization_id, role, monkeypatch):
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
    )
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: (
            membership
            if current_user_id == user_id and current_org_id == organization_id
            else None
        ),
    )


def test_audit_route_is_mounted_and_limits_reads_to_auditors(monkeypatch):
    paths = set(app.openapi()["paths"])
    assert "/api/v1/audit" in paths
    assert "/api/v1/dashboard/summary" in paths
    assert "/api/v1/trace/contribution/{contribution_id}" in paths

    user_id = uuid4()
    org_id = uuid4()
    _override_membership(user_id, org_id, "VIEWER", monkeypatch)
    reader = MagicMock()
    monkeypatch.setattr(audit_api, "list_audit_logs", reader)

    try:
        response = client.get("/api/v1/audit", headers={"X-Organization-ID": str(org_id)})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        reader.assert_not_called()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("role", ["ADMIN", "AUDITOR"])
def test_audit_reader_uses_authenticated_org_and_typed_event_shape(monkeypatch, role):
    user_id = uuid4()
    org_id = uuid4()
    _override_membership(user_id, org_id, role, monkeypatch)
    event_id = uuid4()
    event = {
        "id": event_id,
        "organization_id": org_id,
        "event_type": "MEMBER_ADDED",
        "user_id": user_id,
        "subject_user_id": uuid4(),
        "ip": None,
        "user_agent": None,
        "details": {"entity_type": "organization_member"},
        "created_at": datetime.now(UTC),
    }
    reader = MagicMock(return_value=[event])
    monkeypatch.setattr(audit_api, "list_audit_logs", reader)

    try:
        response = client.get(
            "/api/v1/audit?action=MEMBER_ADDED",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()[0]["event_type"] == "MEMBER_ADDED"
        assert "actor_id" not in response.json()[0]
        reader.assert_called_once()
        assert reader.call_args.kwargs["organization_id"] == org_id
        assert reader.call_args.kwargs["action"] == "MEMBER_ADDED"
    finally:
        app.dependency_overrides.clear()


def test_audit_reader_rejects_cross_organization_header(monkeypatch):
    user_id = uuid4()
    member_org_id = uuid4()
    other_org_id = uuid4()
    _override_membership(user_id, member_org_id, "ADMIN", monkeypatch)
    reader = MagicMock()
    monkeypatch.setattr(audit_api, "list_audit_logs", reader)

    try:
        response = client.get(
            "/api/v1/audit",
            headers={"X-Organization-ID": str(other_org_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    reader.assert_not_called()


def test_audit_reader_rejects_unauthenticated_requests():
    app.dependency_overrides.clear()

    response = client.get(
        "/api/v1/audit",
        headers={"X-Organization-ID": str(uuid4())},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_legacy_audit_writer_maps_fields_into_admin_action():
    cursor = MagicMock()
    cursor.description = [
        SimpleNamespace(name=name)
        for name in (
            "id",
            "organization_id",
            "event_type",
            "user_id",
            "subject_user_id",
            "ip",
            "user_agent",
            "details",
            "created_at",
        )
    ]
    event_id = uuid4()
    org_id = uuid4()
    actor_id = uuid4()
    entity_id = uuid4()
    cursor.fetchone.return_value = (
        event_id,
        org_id,
        "ADMIN_ACTION",
        actor_id,
        None,
        None,
        None,
        {
            "action": "REVIEWED",
            "entity_type": "invoice",
            "entity_id": str(entity_id),
            "metadata": {"source": "manual"},
        },
        datetime.now(UTC),
    )
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor

    with patch("psycopg.connect", return_value=nullcontext(connection)):
        record = audit_logs.create_audit_log(
            organization_id=org_id,
            actor_id=actor_id,
            action="REVIEWED",
            entity_type="invoice",
            entity_id=entity_id,
            metadata={"source": "manual"},
        )

    query = cursor.execute.call_args.args[0]
    params = cursor.execute.call_args.args[1]
    assert "INSERT INTO audit_events" in query
    assert params[0:4] == (org_id, "ADMIN_ACTION", actor_id, None)
    assert record["event_type"] == "ADMIN_ACTION"
    assert record["details"]["entity_id"] == str(entity_id)


def test_audit_list_queries_audit_events_with_tenant_and_legacy_filters():
    cursor = MagicMock()
    cursor.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="organization_id"),
        SimpleNamespace(name="event_type"),
        SimpleNamespace(name="user_id"),
        SimpleNamespace(name="subject_user_id"),
        SimpleNamespace(name="ip"),
        SimpleNamespace(name="user_agent"),
        SimpleNamespace(name="details"),
        SimpleNamespace(name="created_at"),
    ]
    cursor.fetchall.return_value = []
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    org_id = uuid4()
    actor_id = uuid4()
    entity_id = uuid4()

    with patch("psycopg.connect", return_value=nullcontext(connection)):
        rows = audit_logs.list_audit_logs(
            organization_id=org_id,
            action="MEMBER_ADDED",
            entity_type="organization_member",
            actor_id=actor_id,
            entity_id=entity_id,
        )

    sql = cursor.execute.call_args.args[0]
    params = cursor.execute.call_args.args[1]
    assert "FROM audit_events" in sql
    assert "organization_id = %s" in sql
    assert "details->>'entity_type' = %s" in sql
    assert str(entity_id) in params
    assert actor_id in params
    assert rows == []
