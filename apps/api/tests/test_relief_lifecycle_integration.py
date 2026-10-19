"""Live API-to-PostgreSQL relief lifecycle tests for local Supabase."""
from __future__ import annotations

import os
from contextlib import nullcontext
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict

from app.core import config
from app.core.auth import get_current_user
from app.main import app


class _TransactionConnection:
    """Keep API connection contexts inside the fixture's rollback transaction."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def __enter__(self) -> _TransactionConnection:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def __getattr__(self, name: str):
        if name == "transaction":
            return lambda: nullcontext(self)
        if name == "commit":
            return lambda: None
        if name == "rollback":
            return lambda: None
        if name == "close":
            return lambda: None
        return getattr(self._connection, name)


@pytest.fixture
def live_lifecycle(monkeypatch: pytest.MonkeyPatch):
    dsn = os.environ.get("IMPACTLEDGER_LIFECYCLE_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip(
            "Set IMPACTLEDGER_LIFECYCLE_TEST_DATABASE_URL to local Supabase PostgreSQL"
        )

    database = conninfo_to_dict(dsn)
    if (
        database.get("host") not in {"localhost", "127.0.0.1", "::1"}
        or database.get("port") != "54322"
        or database.get("dbname") != "postgres"
    ):
        pytest.fail(
            "Lifecycle tests require the local postgres database on loopback port 54322"
        )

    connection = psycopg.connect(dsn)
    monkeypatch.setattr(config.settings, "database_url", dsn)
    monkeypatch.setattr(psycopg, "connect", lambda *_args, **_kwargs: _TransactionConnection(connection))

    organization_id, other_organization_id = uuid4(), uuid4()
    user_id, other_user_id = uuid4(), uuid4()
    other_contribution_id, other_resource_type_id = uuid4(), uuid4()
    vendor_id = uuid4()

    connection.execute("BEGIN")
    connection.execute(
        """
        INSERT INTO organizations (id, name, slug)
        VALUES (%s, 'Lifecycle integration org', %s),
               (%s, 'Lifecycle integration other org', %s)
        """,
        (
            organization_id,
            f"lifecycle-{organization_id}",
            other_organization_id,
            f"lifecycle-{other_organization_id}",
        ),
    )
    connection.execute(
        """
        INSERT INTO auth.users (
            id, aud, role, email, encrypted_password,
            raw_app_meta_data, raw_user_meta_data
        )
        VALUES
            (%s, 'authenticated', 'authenticated', %s, '', '{}'::jsonb, '{}'::jsonb),
            (%s, 'authenticated', 'authenticated', %s, '', '{}'::jsonb, '{}'::jsonb)
        """,
        (
            user_id,
            f"{user_id}@lifecycle.integration.invalid",
            other_user_id,
            f"{other_user_id}@lifecycle.integration.invalid",
        ),
    )
    connection.execute(
        """
        INSERT INTO organization_members (organization_id, user_id, role)
        VALUES (%s, %s, 'ADMIN'), (%s, %s, 'ADMIN')
        """,
        (organization_id, user_id, other_organization_id, other_user_id),
    )
    connection.execute(
        """
        INSERT INTO contributions (
            id, organization_id, contributor_user_id, amount, status
        ) VALUES (%s, %s, %s, 3, 'CONFIRMED')
        """,
        (other_contribution_id, other_organization_id, other_user_id),
    )
    connection.execute(
        """
        INSERT INTO resource_types (id, organization_id, name, unit)
        VALUES (%s, %s, 'Other organization kits', 'kit')
        """,
        (other_resource_type_id, other_organization_id),
    )
    connection.execute(
        """
        INSERT INTO vendors (id, organization_id, name)
        VALUES (%s, %s, 'Lifecycle test vendor')
        """,
        (vendor_id, organization_id),
    )

    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: user_id)
    yield {
        "connection": connection,
        "organization_id": organization_id,
        "other_organization_id": other_organization_id,
        "user_id": user_id,
        "other_contribution_id": other_contribution_id,
        "other_resource_type_id": other_resource_type_id,
        "vendor_id": vendor_id,
    }
    app.dependency_overrides.clear()
    connection.rollback()
    connection.close()


def _headers(organization_id: UUID) -> dict[str, str]:
    return {"X-Organization-ID": str(organization_id)}


def test_lifecycle_routers_are_mounted():
    assert {
        "/api/v1/contributions",
        "/api/v1/allocations",
        "/api/v1/resource-types",
        "/api/v1/resource-batches",
        "/api/v1/resource-events",
        "/api/v1/distributions",
        "/api/v1/trace/contribution/{contribution_id}",
    } <= set(app.openapi()["paths"])


def test_relief_lifecycle_is_tenant_scoped_and_traceable(live_lifecycle):
    organization_id = live_lifecycle["organization_id"]
    connection = live_lifecycle["connection"]
    client = TestClient(app)

    contribution_response = client.post(
        "/api/v1/contributions",
        headers=_headers(organization_id),
        json={
            "amount": 100,
            "currency": "INR",
            "visibility": "PRIVATE",
            "status": "CONFIRMED",
        },
    )
    assert contribution_response.status_code == 200, contribution_response.text
    contribution_id = UUID(contribution_response.json()["id"])

    allocation_response = client.post(
        "/api/v1/allocations",
        headers=_headers(organization_id),
        json={
            "contribution_id": str(contribution_id),
            "amount": 100,
            "purpose": "Emergency relief kits",
            "status": "APPROVED",
        },
    )
    assert allocation_response.status_code == 200, allocation_response.text
    allocation_id = UUID(allocation_response.json()["id"])

    over_allocation = client.post(
        "/api/v1/allocations",
        headers=_headers(organization_id),
        json={
            "contribution_id": str(contribution_id),
            "amount": 0.01,
            "purpose": "Must exceed available contribution",
            "status": "APPROVED",
        },
    )
    assert over_allocation.status_code == 400

    resource_type_response = client.post(
        "/api/v1/resource-types",
        headers=_headers(organization_id),
        json={"name": "Emergency kits", "unit": "kit"},
    )
    assert resource_type_response.status_code == 200, resource_type_response.text
    resource_type_id = UUID(resource_type_response.json()["id"])

    commitment_id, purchase_order_id = uuid4(), uuid4()
    connection.execute(
        """
        INSERT INTO commitments (
            id, organization_id, allocation_id, vendor_id, amount,
            description, created_by
        ) VALUES (%s, %s, %s, %s, 100, 'Emergency kits', %s)
        """,
        (
            commitment_id,
            organization_id,
            allocation_id,
            live_lifecycle["vendor_id"],
            live_lifecycle["user_id"],
        ),
    )
    connection.execute(
        """
        INSERT INTO purchase_orders (
            id, organization_id, commitment_id, vendor_id, po_number,
            status, total_amount, created_by, approved_by, approved_at
        ) VALUES (%s, %s, %s, %s, %s, 'APPROVED', 100, %s, %s, NOW())
        """,
        (
            purchase_order_id,
            organization_id,
            commitment_id,
            live_lifecycle["vendor_id"],
            f"LIFECYCLE-{purchase_order_id}",
            live_lifecycle["user_id"],
            live_lifecycle["user_id"],
        ),
    )

    batch_response = client.post(
        "/api/v1/resource-batches",
        headers=_headers(organization_id),
        json={
            "resource_type_id": str(resource_type_id),
            "purchase_order_id": str(purchase_order_id),
            "batch_code": f"linked-{uuid4()}",
            "quantity": 20,
            "location": "Warehouse",
        },
    )
    assert batch_response.status_code == 200, batch_response.text
    batch = batch_response.json()
    batch_id = UUID(batch["id"])
    assert batch["purchase_order_id"] == str(purchase_order_id)

    unrelated_batch_response = client.post(
        "/api/v1/resource-batches",
        headers=_headers(organization_id),
        json={
            "resource_type_id": str(resource_type_id),
            "batch_code": f"unlinked-{uuid4()}",
            "quantity": 5,
            "location": "Warehouse",
        },
    )
    assert unrelated_batch_response.status_code == 200, unrelated_batch_response.text
    unrelated_batch_id = UUID(unrelated_batch_response.json()["id"])

    relief_event_id, unrelated_relief_event_id = uuid4(), uuid4()
    connection.execute(
        """
        INSERT INTO relief_events (id, organization_id, name, location, created_by)
        VALUES (%s, %s, 'Lifecycle relief event', 'District A', %s),
               (%s, %s, 'Unrelated relief event', 'District B', %s)
        """,
        (
            relief_event_id,
            organization_id,
            live_lifecycle["user_id"],
            unrelated_relief_event_id,
            organization_id,
            live_lifecycle["user_id"],
        ),
    )
    distribution_response = client.post(
        "/api/v1/distributions",
        headers=_headers(organization_id),
        json={
            "relief_event_id": str(relief_event_id),
            "resource_batch_id": str(batch_id),
            "quantity": 12,
            "destination": "District A",
            "beneficiary_count": 8,
        },
    )
    assert distribution_response.status_code == 200, distribution_response.text
    distribution_id = UUID(distribution_response.json()["distribution_id"])

    unrelated_distribution = client.post(
        "/api/v1/distributions",
        headers=_headers(organization_id),
        json={
            "relief_event_id": str(unrelated_relief_event_id),
            "resource_batch_id": str(unrelated_batch_id),
            "quantity": 1,
            "destination": "District B",
            "beneficiary_count": 1,
        },
    )
    assert unrelated_distribution.status_code == 200, unrelated_distribution.text

    over_distribution = client.post(
        "/api/v1/distributions",
        headers=_headers(organization_id),
        json={
            "relief_event_id": str(relief_event_id),
            "resource_batch_id": str(batch_id),
            "quantity": 9,
            "destination": "District A",
            "beneficiary_count": 1,
        },
    )
    assert over_distribution.status_code == 400

    inventory_response = client.get(
        f"/api/v1/inventory/{batch_id}",
        headers=_headers(organization_id),
    )
    assert inventory_response.status_code == 200
    assert inventory_response.json()["available_quantity"] == 8

    trace_response = client.get(
        f"/api/v1/trace/contribution/{contribution_id}",
        headers=_headers(organization_id),
    )
    assert trace_response.status_code == 200, trace_response.text
    trace = trace_response.json()
    assert trace["contribution"]["id"] == str(contribution_id)
    assert [row["id"] for row in trace["allocations"]] == [str(allocation_id)]
    assert [row["id"] for row in trace["resource_batches"]] == [str(batch_id)]
    assert {row["event_type"] for row in trace["resource_events"]} == {
        "RECEIVED",
        "DISTRIBUTED",
    }
    assert [row["id"] for row in trace["distributions"]] == [str(distribution_id)]
    assert all(row["resource_batch_id"] == str(batch_id) for row in trace["distributions"])

    audit_response = client.get("/api/v1/audit", headers=_headers(organization_id))
    assert audit_response.status_code == 200, audit_response.text
    actions = {row["details"]["action"] for row in audit_response.json()}
    assert {
        "CONTRIBUTION_RECORDED",
        "ALLOCATION_RECORDED",
        "RESOURCE_RECEIVED",
        "RESOURCE_DISTRIBUTED",
    } <= actions

    assert client.get(
        f"/api/v1/contributions/{live_lifecycle['other_contribution_id']}",
        headers=_headers(organization_id),
    ).status_code == 404
    assert client.get(
        f"/api/v1/resource-types/{live_lifecycle['other_resource_type_id']}",
        headers=_headers(organization_id),
    ).status_code == 404
    assert client.get(
        f"/api/v1/trace/contribution/{live_lifecycle['other_contribution_id']}",
        headers=_headers(organization_id),
    ).status_code == 404
