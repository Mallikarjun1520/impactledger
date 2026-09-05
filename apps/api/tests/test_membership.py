from uuid import uuid4

from fastapi.testclient import TestClient

from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app


client = TestClient(app)


def test_membership_without_token_returns_401() -> None:
    response = client.get(
        "/api/v1/auth/membership",
        headers={"X-Organization-ID": str(uuid4())},
    )
    assert response.status_code == 401


def test_membership_with_invalid_organization_id_returns_422() -> None:
    user_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id
    try:
        response = client.get(
            "/api/v1/auth/membership",
            headers={"X-Organization-ID": "not-a-uuid"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_membership_for_member_returns_role(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()
    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user_id,
        role="ADMIN",
    )

    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: membership,
    )

    try:
        response = client.get(
            "/api/v1/auth/membership",
            headers={"X-Organization-ID": str(organization_id)},
        )
        assert response.status_code == 200
        assert response.json() == {
            "organization_id": str(organization_id),
            "user_id": str(user_id),
            "role": "ADMIN",
        }
    finally:
        app.dependency_overrides.clear()


def test_membership_for_non_member_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    organization_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: None,
    )

    try:
        response = client.get(
            "/api/v1/auth/membership",
            headers={"X-Organization-ID": str(organization_id)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "User is not a member of this organization"
    finally:
        app.dependency_overrides.clear()
