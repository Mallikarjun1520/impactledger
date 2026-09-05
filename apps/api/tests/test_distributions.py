from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1 import distributions as distributions_api
from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app


client = TestClient(app)


def _distribution_payload(organization_id):
    return {
        "relief_event_id": str(uuid4()),
        "resource_batch_id": str(uuid4()),
        "organization_id": str(organization_id),
        "quantity": 10,
        "destination": "Shelter A",
        "beneficiary_count": 4,
        "notes": None,
    }


def _override_member(user_id, organization_id, role: str, monkeypatch) -> None:
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
    )
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: membership,
    )


def test_create_distribution_allowed_role_succeeds(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "OPERATOR", monkeypatch)
    monkeypatch.setattr(
        distributions_api,
        "create_distribution",
        lambda data, created_by: "distribution-id",
    )

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(organization_id),
            headers={"X-Organization-ID": str(organization_id)},
        )
        assert response.status_code == 200
        assert response.json() == {
            "status": "distribution created",
            "distribution_id": "distribution-id",
        }
    finally:
        app.dependency_overrides.clear()


def test_create_distribution_insufficient_quantity_returns_400(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "ADMIN", monkeypatch)

    def raise_insufficient(data, created_by):
        raise ValueError("Insufficient resource quantity. Available: 1, Requested: 10")

    monkeypatch.setattr(distributions_api, "create_distribution", raise_insufficient)

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(organization_id),
            headers={"X-Organization-ID": str(organization_id)},
        )
        assert response.status_code == 400
        assert "Insufficient resource quantity" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_create_distribution_viewer_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "VIEWER", monkeypatch)

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(organization_id),
            headers={"X-Organization-ID": str(organization_id)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient role for this operation"
    finally:
        app.dependency_overrides.clear()


def test_create_distribution_non_member_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: None,
    )

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(organization_id),
            headers={"X-Organization-ID": str(organization_id)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "User is not a member of this organization"
    finally:
        app.dependency_overrides.clear()


def test_create_distribution_organization_mismatch_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    other_organization_id = uuid4()
    _override_member(user_id, organization_id, "FIELD_AGENT", monkeypatch)

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(other_organization_id),
            headers={"X-Organization-ID": str(organization_id)},
        )
        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "Distribution organization does not match X-Organization-ID"
        )
    finally:
        app.dependency_overrides.clear()
