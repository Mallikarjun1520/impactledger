from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.infrastructure.database.organization_members import OrganizationMembership
from app.main import app


client = TestClient(app)


def test_auth_me_without_token_returns_401() -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_auth_me_with_invalid_token_returns_401() -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


def test_auth_me_with_valid_user_returns_user_id() -> None:
    user_id = uuid4()
    app.dependency_overrides[get_current_user] = lambda: user_id
    try:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        assert response.json() == {"user_id": str(user_id)}
    finally:
        app.dependency_overrides.clear()
