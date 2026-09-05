from uuid import UUID

from fastapi import Depends, Header, HTTPException

from app.core.auth import get_current_user
from app.infrastructure.database.organization_members import (
    OrganizationMembership,
    get_organization_membership,
)


def get_current_membership(
    user_id: UUID = Depends(get_current_user),
    x_organization_id: UUID = Header(..., alias="X-Organization-ID"),
) -> OrganizationMembership:
    membership = get_organization_membership(user_id, x_organization_id)

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="User is not a member of this organization",
        )

    return membership
