from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas_v2 import (
    FundPoolCreate,
    FundPoolResponse,
    PoolAllocationCreate,
    PoolContributionCreate,
)
from app.core.authorization import get_current_membership
from app.domain.invariants import InvariantViolation
from app.infrastructure.database import finance as finance_db
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter(prefix="/organizations/{org_id}/fund-pools", tags=["fund-pools"])


@router.post("", response_model=FundPoolResponse, status_code=status.HTTP_201_CREATED)
def create_pool(
    org_id: UUID,
    body: FundPoolCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> FundPoolResponse:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if membership.role not in ("ADMIN", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")

    if body.restriction_scope == "INITIATIVE" and body.initiative_id is None:
        raise HTTPException(status_code=422, detail="initiative_id required for INITIATIVE scope")
    if body.restriction_scope == "CATEGORY" and not body.category:
        raise HTTPException(status_code=422, detail="category required for CATEGORY scope")

    row = finance_db.create_fund_pool(
        org_id=org_id,
        user_id=membership.user_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        restriction_scope=body.restriction_scope.value,
        initiative_id=body.initiative_id,
        category=body.category,
        currency=body.currency,
    )
    return FundPoolResponse(**row)


@router.post("/{pool_id}/contributions", status_code=status.HTTP_201_CREATED)
def record_contribution(
    org_id: UUID,
    pool_id: UUID,
    body: PoolContributionCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if body.fund_pool_id != pool_id:
        raise HTTPException(status_code=422, detail="fund_pool_id mismatch")

    try:
        row = finance_db.record_pool_contribution(
            org_id=org_id,
            user_id=membership.user_id,
            pool_id=pool_id,
            amount=body.amount,
            currency=body.currency,
            visibility=body.visibility,
            contributor_metadata=body.contributor_metadata,
            external_reference=body.external_reference,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return row


@router.post("/{pool_id}/allocations", status_code=status.HTTP_201_CREATED)
def record_allocation(
    org_id: UUID,
    pool_id: UUID,
    body: PoolAllocationCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if membership.role not in ("ADMIN", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    if body.fund_pool_id != pool_id:
        raise HTTPException(status_code=422, detail="fund_pool_id mismatch")

    try:
        row = finance_db.record_pool_allocation(
            org_id=org_id,
            user_id=membership.user_id,
            pool_id=pool_id,
            amount=body.amount,
            purpose=body.purpose,
            initiative_id=body.initiative_id,
            purpose_category=body.purpose_category,
        )
    except InvariantViolation as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return row
