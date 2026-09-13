from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas import ContributionCreate, ContributionResponse
from app.core.authorization import get_current_membership, require_role
from app.infrastructure.database.contributions import (
    create_contribution,
    get_contribution,
    list_contributions,
)
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter()

CONTRIBUTION_CREATE_ROLES = ("ADMIN", "OPERATOR", "DONOR")


@router.post("/contributions", response_model=ContributionResponse)
def create_contribution_endpoint(
    data: ContributionCreate,
    membership: OrganizationMembership = Depends(
        require_role(*CONTRIBUTION_CREATE_ROLES)
    ),
):
    try:
        return create_contribution(
            organization_id=membership.organization_id,
            data=data,
            user_id=membership.user_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/contributions", response_model=list[ContributionResponse])
def list_contributions_endpoint(
    membership: OrganizationMembership = Depends(get_current_membership),
):
    return list_contributions(organization_id=membership.organization_id)


@router.get("/contributions/{contribution_id}", response_model=ContributionResponse)
def get_contribution_endpoint(
    contribution_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
):
    contribution = get_contribution(
        organization_id=membership.organization_id,
        contribution_id=contribution_id,
    )
    if contribution is None:
        raise HTTPException(
            status_code=404,
            detail="Contribution not found",
        )
    return contribution
