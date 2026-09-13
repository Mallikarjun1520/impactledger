from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1 import organizations as organizations_api
from app.core import authorization as authorization_module
from app.core.auth import get_current_user
from app.core.exceptions import (
    DuplicateSlugError,
    LastAdminError,
    MemberAlreadyExistsError,
    OrganizationNotFoundError,
)
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app

client = TestClient(app)


def _override_membership(user_id, organization_id, role: str, monkeypatch) -> None:
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
            membership if current_user_id == user_id and current_org_id == organization_id else None
        ),
    )


# ---------------------------------------------------------------------------
# Organization Creation & Duplicate Slug Tests
# ---------------------------------------------------------------------------


def test_create_organization_succeeds(monkeypatch) -> None:
    user_id = uuid4()
    org_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id

    monkeypatch.setattr(
        organizations_api,
        "create_organization",
        lambda data, user_id: {
            "id": org_id,
            "name": data.name,
            "slug": data.slug,
            "description": data.description,
        },
    )

    try:
        response = client.post(
            "/api/v1/organizations",
            json={
                "name": "Aid Coalition",
                "slug": "aid-coalition",
                "description": "Global relief group",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(org_id)
        assert data["name"] == "Aid Coalition"
        assert data["slug"] == "aid-coalition"
    finally:
        app.dependency_overrides.clear()


def test_create_organization_duplicate_slug_returns_409(monkeypatch) -> None:
    user_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id

    def raise_duplicate(data, user_id):
        raise DuplicateSlugError(f"Organization with slug '{data.slug}' already exists")

    monkeypatch.setattr(organizations_api, "create_organization", raise_duplicate)

    try:
        response = client.post(
            "/api/v1/organizations",
            json={
                "name": "Aid Coalition",
                "slug": "aid-coalition",
                "description": None,
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Organization Lookup & Cross-Org Access Tests
# ---------------------------------------------------------------------------


def test_get_organization_member_can_access(monkeypatch) -> None:
    user_id = uuid4()
    org_id = uuid4()
    now = datetime.now(timezone.utc)
    _override_membership(user_id, org_id, "VIEWER", monkeypatch)

    monkeypatch.setattr(
        organizations_api,
        "get_organization",
        lambda target_org_id: {
            "id": org_id,
            "name": "Aid Coalition",
            "slug": "aid-coalition",
            "description": "Helping hands",
            "created_at": now,
            "updated_at": now,
        },
    )

    try:
        response = client.get(
            f"/api/v1/organizations/{org_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(org_id)
    finally:
        app.dependency_overrides.clear()


def test_get_organization_non_member_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    org_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id
    monkeypatch.setattr(
        authorization_module,
        "get_organization_membership",
        lambda current_user_id, current_org_id: None,
    )

    try:
        response = client.get(
            f"/api/v1/organizations/{org_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "User is not a member of this organization"
    finally:
        app.dependency_overrides.clear()


def test_get_organization_header_mismatch_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    org_a = uuid4()
    org_b = uuid4()
    _override_membership(user_id, org_a, "ADMIN", monkeypatch)

    try:
        response = client.get(
            f"/api/v1/organizations/{org_b}",
            headers={"X-Organization-ID": str(org_a)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Organization ID does not match X-Organization-ID"
    finally:
        app.dependency_overrides.clear()


def test_get_organization_not_found_returns_404(monkeypatch) -> None:
    user_id = uuid4()
    org_id = uuid4()
    _override_membership(user_id, org_id, "ADMIN", monkeypatch)
    monkeypatch.setattr(organizations_api, "get_organization", lambda target_id: None)

    try:
        response = client.get(
            f"/api/v1/organizations/{org_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Organization not found"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# List Members Tests
# ---------------------------------------------------------------------------


def test_list_members_member_can_access(monkeypatch) -> None:
    user_id = uuid4()
    org_id = uuid4()
    _override_membership(user_id, org_id, "VIEWER", monkeypatch)

    monkeypatch.setattr(
        organizations_api,
        "list_organization_members",
        lambda target_org_id: [
            OrganizationMembership(organization_id=org_id, user_id=user_id, role="VIEWER")
        ],
    )

    try:
        response = client.get(
            f"/api/v1/organizations/{org_id}/members",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["user_id"] == str(user_id)
    finally:
        app.dependency_overrides.clear()


def test_list_members_header_mismatch_returns_403(monkeypatch) -> None:
    user_id = uuid4()
    org_a = uuid4()
    org_b = uuid4()
    _override_membership(user_id, org_a, "VIEWER", monkeypatch)

    try:
        response = client.get(
            f"/api/v1/organizations/{org_b}/members",
            headers={"X-Organization-ID": str(org_a)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Organization ID does not match X-Organization-ID"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Member Management RBAC: Positive & Negative Tests
# ---------------------------------------------------------------------------


def test_add_member_admin_succeeds(monkeypatch) -> None:
    admin_id = uuid4()
    new_user_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)

    monkeypatch.setattr(
        organizations_api,
        "add_organization_member",
        lambda organization_id, data: OrganizationMembership(
            organization_id=organization_id,
            user_id=data.user_id,
            role=data.role.value,
        ),
    )

    try:
        response = client.post(
            f"/api/v1/organizations/{org_id}/members",
            json={"user_id": str(new_user_id), "role": "OPERATOR"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "OPERATOR"
        assert response.json()["user_id"] == str(new_user_id)
    finally:
        app.dependency_overrides.clear()


def test_add_member_non_admin_returns_403(monkeypatch) -> None:
    operator_id = uuid4()
    new_user_id = uuid4()
    org_id = uuid4()
    _override_membership(operator_id, org_id, "OPERATOR", monkeypatch)

    try:
        response = client.post(
            f"/api/v1/organizations/{org_id}/members",
            json={"user_id": str(new_user_id), "role": "VIEWER"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Only organization admins can manage members"
    finally:
        app.dependency_overrides.clear()


def test_add_member_already_exists_returns_409(monkeypatch) -> None:
    admin_id = uuid4()
    new_user_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)

    def raise_exists(organization_id, data):
        raise MemberAlreadyExistsError("User is already a member of this organization")

    monkeypatch.setattr(organizations_api, "add_organization_member", raise_exists)

    try:
        response = client.post(
            f"/api/v1/organizations/{org_id}/members",
            json={"user_id": str(new_user_id), "role": "VIEWER"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "User is already a member of this organization"
    finally:
        app.dependency_overrides.clear()


def test_update_member_role_admin_succeeds(monkeypatch) -> None:
    admin_id = uuid4()
    target_user_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)

    monkeypatch.setattr(
        organizations_api,
        "update_organization_member",
        lambda organization_id, user_id, role: OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            role=role.value,
        ),
    )

    try:
        response = client.patch(
            f"/api/v1/organizations/{org_id}/members/{target_user_id}",
            json={"role": "OPERATOR"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "OPERATOR"
    finally:
        app.dependency_overrides.clear()


def test_update_member_role_non_admin_returns_403(monkeypatch) -> None:
    field_agent_id = uuid4()
    target_user_id = uuid4()
    org_id = uuid4()
    _override_membership(field_agent_id, org_id, "FIELD_AGENT", monkeypatch)

    try:
        response = client.patch(
            f"/api/v1/organizations/{org_id}/members/{target_user_id}",
            json={"role": "ADMIN"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Only organization admins can manage members"
    finally:
        app.dependency_overrides.clear()


def test_update_member_not_found_returns_404(monkeypatch) -> None:
    admin_id = uuid4()
    target_user_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)
    monkeypatch.setattr(
        organizations_api,
        "update_organization_member",
        lambda organization_id, user_id, role: None,
    )

    try:
        response = client.patch(
            f"/api/v1/organizations/{org_id}/members/{target_user_id}",
            json={"role": "OPERATOR"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Organization member not found"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Last Admin Protection Tests
# ---------------------------------------------------------------------------


def test_cannot_demote_final_admin(monkeypatch) -> None:
    admin_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)

    def raise_last_admin(organization_id, user_id, role):
        raise LastAdminError("Organization must have at least one admin")

    monkeypatch.setattr(organizations_api, "update_organization_member", raise_last_admin)

    try:
        response = client.patch(
            f"/api/v1/organizations/{org_id}/members/{admin_id}",
            json={"role": "OPERATOR"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Organization must have at least one admin"
    finally:
        app.dependency_overrides.clear()


def test_cannot_delete_final_admin(monkeypatch) -> None:
    admin_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)

    def raise_last_admin(organization_id, user_id):
        raise LastAdminError("Organization must have at least one admin")

    monkeypatch.setattr(organizations_api, "delete_organization_member", raise_last_admin)

    try:
        response = client.delete(
            f"/api/v1/organizations/{org_id}/members/{admin_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Organization must have at least one admin"
    finally:
        app.dependency_overrides.clear()


def test_delete_member_admin_succeeds(monkeypatch) -> None:
    admin_id = uuid4()
    target_user_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)

    monkeypatch.setattr(
        organizations_api,
        "delete_organization_member",
        lambda organization_id, user_id: True,
    )

    try:
        response = client.delete(
            f"/api/v1/organizations/{org_id}/members/{target_user_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "member removed"
        assert data["organization_id"] == str(org_id)
        assert data["user_id"] == str(target_user_id)
    finally:
        app.dependency_overrides.clear()


def test_delete_member_non_admin_returns_403(monkeypatch) -> None:
    viewer_id = uuid4()
    target_user_id = uuid4()
    org_id = uuid4()
    _override_membership(viewer_id, org_id, "VIEWER", monkeypatch)

    try:
        response = client.delete(
            f"/api/v1/organizations/{org_id}/members/{target_user_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Only organization admins can manage members"
    finally:
        app.dependency_overrides.clear()


def test_delete_member_not_found_returns_404(monkeypatch) -> None:
    admin_id = uuid4()
    target_user_id = uuid4()
    org_id = uuid4()
    _override_membership(admin_id, org_id, "ADMIN", monkeypatch)

    monkeypatch.setattr(
        organizations_api,
        "delete_organization_member",
        lambda organization_id, user_id: False,
    )

    try:
        response = client.delete(
            f"/api/v1/organizations/{org_id}/members/{target_user_id}",
            headers={"X-Organization-ID": str(org_id)},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Organization member not found"
    finally:
        app.dependency_overrides.clear()


def test_delete_member_header_mismatch_returns_403(monkeypatch) -> None:
    admin_id = uuid4()
    target_user_id = uuid4()
    org_a = uuid4()
    org_b = uuid4()
    _override_membership(admin_id, org_a, "ADMIN", monkeypatch)

    try:
        response = client.delete(
            f"/api/v1/organizations/{org_b}/members/{target_user_id}",
            headers={"X-Organization-ID": str(org_a)},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Organization ID does not match X-Organization-ID"
    finally:
        app.dependency_overrides.clear()
