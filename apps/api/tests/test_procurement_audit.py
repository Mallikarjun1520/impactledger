from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1 import procurement as procurement_api
from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.domain.invariants import InvariantViolation
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app

client = TestClient(app)


def _set_membership(user_id, org_id, role, monkeypatch):
    membership = OrganizationMembership(org_id, user_id, role)
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: membership
        if current_user_id == user_id and current_org_id == org_id
        else None,
    )


def test_po_approval_attempt_writes_typed_audit_event(monkeypatch):
    user_id = uuid4()
    org_id = uuid4()
    po_id = uuid4()
    _set_membership(user_id, org_id, "ADMIN", monkeypatch)
    audit_writer = MagicMock()
    monkeypatch.setattr(procurement_api, "create_audit_event", audit_writer)
    monkeypatch.setattr(procurement_api.finance_db, "approve_purchase_order", MagicMock())

    try:
        response = client.post(
            f"/api/v1/organizations/{org_id}/purchase-orders/{po_id}/approve",
            headers={"X-Organization-ID": str(org_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    audit_writer.assert_called_once()
    assert audit_writer.call_args.kwargs["event_type"] == "PO_APPROVAL_ATTEMPTED"
    assert audit_writer.call_args.kwargs["organization_id"] == org_id
    assert audit_writer.call_args.kwargs["user_id"] == user_id


def test_self_approval_denial_is_recorded_as_audit_event(monkeypatch):
    user_id = uuid4()
    org_id = uuid4()
    po_id = uuid4()
    _set_membership(user_id, org_id, "ADMIN", monkeypatch)
    audit_writer = MagicMock()
    monkeypatch.setattr(procurement_api, "create_audit_event", audit_writer)

    def deny_self_approval(**kwargs):
        raise InvariantViolation("S.1", "Creator cannot approve their own PO")

    monkeypatch.setattr(
        procurement_api.finance_db,
        "approve_purchase_order",
        deny_self_approval,
    )
    try:
        response = client.post(
            f"/api/v1/organizations/{org_id}/purchase-orders/{po_id}/approve",
            headers={"X-Organization-ID": str(org_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    event_types = [
        call.kwargs["event_type"]
        for call in audit_writer.call_args_list
    ]
    assert event_types == ["PO_APPROVAL_ATTEMPTED", "PO_APPROVAL_DENIED_SELF"]
