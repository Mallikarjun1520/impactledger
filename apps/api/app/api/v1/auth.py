from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.authorization import get_current_membership
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter()


@router.get("/auth/me")
def get_me(
    user_id: UUID = Depends(get_current_user),
) -> dict[str, str]:
    return {
        "user_id": str(user_id),
    }


@router.get("/auth/membership")
def get_membership(
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict[str, str]:
    return {
        "organization_id": str(membership.organization_id),
        "user_id": str(membership.user_id),
        "role": membership.role,
    }
