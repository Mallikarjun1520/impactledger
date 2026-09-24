from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas_v2 import InitiativeCreate, InitiativeResponse
from app.core.authorization import get_current_membership
from app.infrastructure.database import finance as finance_db
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter(prefix="/organizations/{org_id}/initiatives", tags=["initiatives"])


@router.post(
    "",
    response_model=InitiativeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_initiative(
    org_id: UUID,
    body: InitiativeCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> InitiativeResponse:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if membership.role not in ("ADMIN", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")

    row = finance_db.create_initiative(
        org_id=org_id,
        user_id=membership.user_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        category=body.category,
    )
    return InitiativeResponse(**row)
