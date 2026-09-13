
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1 import distributions as distributions_api
from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app


client = TestClient(app)


def _distribution_payload():
    return {
        "relief_event_id": str(uuid4()),
        "resource_batch_id": str(uuid4()),
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

    captured_args = {}

    def mock_create(data, created_by, organization_id=None):
        captured_args["data"] = data
        captured_args["created_by"] = created_by
        captured_args["organization_id"] = organization_id
        return "distribution-id"

    monkeypatch.setattr(
        distributions_api,
        "create_distribution",
        mock_create,
    )

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(),
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "distribution created",
            "distribution_id": "distribution-id",
        }

        assert captured_args["organization_id"] == organization_id
        assert captured_args["created_by"] == user_id

        # Organization identity must come from authenticated membership,
        # not from the client request body.
        assert "organization_id" not in type(captured_args["data"]).model_fields

    finally:
        app.dependency_overrides.clear()


def test_create_distribution_ignores_client_organization_identity(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "ADMIN", monkeypatch)

    captured_args = {}

    def mock_create(data, created_by, organization_id=None):
        captured_args["data"] = data
        captured_args["created_by"] = created_by
        captured_args["organization_id"] = organization_id
        return "distribution-id"

    monkeypatch.setattr(
        distributions_api,
        "create_distribution",
        mock_create,
    )

    try:
        payload = _distribution_payload()

        # A client may attempt to supply another organization ID,
        # but the request schema does not define or trust that field.
        payload["organization_id"] = str(uuid4())

        response = client.post(
            "/api/v1/distributions",
            json=payload,
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 200
        assert captured_args["organization_id"] == organization_id
        assert "organization_id" not in type(captured_args["data"]).model_fields

    finally:
        app.dependency_overrides.clear()


def test_create_distribution_insufficient_quantity_returns_400(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "ADMIN", monkeypatch)

    def raise_insufficient(data, created_by, organization_id=None):
        raise ValueError("Insufficient resource quantity. Available: 1, Requested: 10")

    monkeypatch.setattr(
        distributions_api,
        "create_distribution",
        raise_insufficient,
    )

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(),
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 400
        assert "Insufficient resource quantity" in response.json()["detail"]

    finally:
        app.dependency_overrides.clear()


def test_create_distribution_cross_org_batch_rejected(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "ADMIN", monkeypatch)

    def raise_cross_org(data, created_by, organization_id=None):
        raise ValueError("Resource batch not found or does not belong to organization")

    monkeypatch.setattr(
        distributions_api,
        "create_distribution",
        raise_cross_org,
    )

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(),
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 400
        assert (
            "Resource batch not found or does not belong to organization"
            in response.json()["detail"]
        )

    finally:
        app.dependency_overrides.clear()


def test_create_distribution_viewer_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "VIEWER", monkeypatch)

    try:
        response = client.post(
            "/api/v1/distributions",
            json=_distribution_payload(),
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
            json=_distribution_payload(),
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "User is not a member of this organization"

    finally:
        app.dependency_overrides.clear()


def test_list_distributions_scoped_to_organization(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    _override_member(user_id, organization_id, "VIEWER", monkeypatch)

    captured_org_id = []

    def mock_get_distributions(organization_id):
        captured_org_id.append(organization_id)
        return [{"id": "dist-1", "organization_id": str(organization_id)}]

    monkeypatch.setattr(
        distributions_api,
        "get_distributions",
        mock_get_distributions,
    )

    try:
        response = client.get(
            "/api/v1/distributions",
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 200
        assert captured_org_id == [organization_id]
        assert len(response.json()) == 1

    finally:
        app.dependency_overrides.clear()


def test_list_distributions_unauthenticated_returns_401() -> None:
    response = client.get(
        "/api/v1/distributions",
        headers={"X-Organization-ID": str(uuid4())},
    )

    assert response.status_code == 401


def test_inventory_scoped_to_organization_succeeds(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    batch_id = uuid4()
    _override_member(user_id, organization_id, "VIEWER", monkeypatch)

    monkeypatch.setattr(
        distributions_api,
        "get_inventory",
        lambda resource_batch_id, organization_id: 42.5,
    )

    try:
        response = client.get(
            f"/api/v1/inventory/{batch_id}",
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 200
        assert response.json()["available_quantity"] == 42.5
        assert response.json()["resource_batch_id"] == str(batch_id)

    finally:
        app.dependency_overrides.clear()


def test_inventory_not_found_or_wrong_org_returns_404(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    batch_id = uuid4()
    _override_member(user_id, organization_id, "VIEWER", monkeypatch)

    monkeypatch.setattr(
        distributions_api,
        "get_inventory",
        lambda resource_batch_id, organization_id: None,
    )

    try:
        response = client.get(
            f"/api/v1/inventory/{batch_id}",
            headers={"X-Organization-ID": str(organization_id)},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Resource batch not found"

    finally:
        app.dependency_overrides.clear()