from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.schemas import AllocationCreate, AllocationResponse
from app.core.authorization import get_current_membership, require_role
from app.core.exceptions import (
    AllocationNotFoundError,
    ContributionNotFoundError,
    InvalidAllocationError,
)
from app.infrastructure.database.allocations import (
    create_allocation,
    get_allocation,
    list_allocations,
)
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter()

ALLOCATION_CREATE_ROLES = ("ADMIN", "OPERATOR")


@router.post("/allocations", response_model=AllocationResponse)
def create_allocation_endpoint(
    data: AllocationCreate,
    membership: OrganizationMembership = Depends(
        require_role(*ALLOCATION_CREATE_ROLES)
    ),
):
    try:
        return create_allocation(
            organization_id=membership.organization_id,
            data=data,
            user_id=membership.user_id,
        )
    except ContributionNotFoundError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
    except InvalidAllocationError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/allocations", response_model=list[AllocationResponse])
def list_allocations_endpoint(
    contribution_id: UUID | None = Query(None),
    membership: OrganizationMembership = Depends(get_current_membership),
):
    try:
        return list_allocations(
            organization_id=membership.organization_id,
            contribution_id=contribution_id,
        )
    except ContributionNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


@router.get("/allocations/{allocation_id}", response_model=AllocationResponse)
def get_allocation_endpoint(
    allocation_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
):
    allocation = get_allocation(
        organization_id=membership.organization_id,
        allocation_id=allocation_id,
    )
    if allocation is None:
        raise HTTPException(
            status_code=404,
            detail="Allocation not found",
        )
    return allocation
