from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1 import trace as trace_api
from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.infrastructure.database.contribution_trace import get_contribution_resources
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app

client = TestClient(app)


def test_trace_route_only_uses_authenticated_org_and_related_rows(monkeypatch):
    user_id = uuid4()
    org_id = uuid4()
    contribution_id = uuid4()
    membership = OrganizationMembership(org_id, user_id, "VIEWER")
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: membership
        if current_user_id == user_id and current_org_id == org_id
        else None,
    )
    contribution_reader = MagicMock(return_value={"id": contribution_id})
    allocation_reader = MagicMock(return_value=[{"id": uuid4()}])
    resource_reader = MagicMock(
        return_value={
            "resource_batches": [{"id": uuid4()}],
            "resource_events": [{"id": uuid4()}],
            "distributions": [{"id": uuid4()}],
        }
    )
    monkeypatch.setattr(trace_api, "get_contribution", contribution_reader)
    monkeypatch.setattr(trace_api, "list_allocations", allocation_reader)
    monkeypatch.setattr(trace_api, "get_contribution_resources", resource_reader)

    try:
        response = client.get(
            f"/api/v1/trace/contribution/{contribution_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()["resource_batches"]) == 1
    resource_reader.assert_called_once_with(
        organization_id=org_id,
        contribution_id=contribution_id,
    )


def test_related_resource_queries_follow_contribution_to_purchase_order(monkeypatch):
    cursor = MagicMock()
    queries = []
    descriptions = [
        ("id", "resource_type_id", "organization_id", "batch_code", "quantity",
         "source_description", "received_at", "location", "created_at", "updated_at"),
        ("id", "resource_batch_id", "event_type", "quantity", "location",
         "performed_by", "reason", "transfer_id", "created_at"),
        ("id", "relief_event_id", "resource_batch_id", "organization_id",
         "quantity", "destination", "beneficiary_count", "notes", "created_by",
         "created_at"),
    ]
    rows = [
        [(uuid4(), uuid4(), uuid4(), "batch-1", 2, None, None, None, None, None)],
        [(uuid4(), uuid4(), "RECEIVED", 2, "warehouse", None, None, None, None)],
        [],
    ]

    def execute(sql, params):
        queries.append((sql, params))
        index = len(queries) - 1
        cursor.description = [MagicMock(name=name) for name in descriptions[index]]
        for column, name in zip(cursor.description, descriptions[index], strict=False):
            column.name = name
        cursor.fetchall.return_value = rows[index]

    cursor.execute.side_effect = execute
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    with patch("psycopg.connect", return_value=connection):
        result = get_contribution_resources(uuid4(), uuid4())

    assert len(result["resource_batches"]) == 1
    assert len(result["resource_events"]) == 1
    assert result["distributions"] == []
    first_sql = queries[0][0]
    assert "JOIN purchase_orders" in first_sql
    assert "JOIN commitments" in first_sql
    assert "JOIN allocations" in first_sql
    assert "a.contribution_id = %s" in first_sql
    assert all("organization_id = %s" in sql for sql, _ in queries)
