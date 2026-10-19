from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.authorization import get_current_membership
from app.infrastructure.database.allocations import list_allocations
from app.infrastructure.database.contribution_trace import get_contribution_resources
from app.infrastructure.database.contributions import get_contribution
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter()


@router.get("/trace/contribution/{contribution_id}")
def trace_contribution(
    contribution_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
):
    org_id = membership.organization_id

    # Verify contribution belongs to this organization
    contribution = get_contribution(
        organization_id=org_id,
        contribution_id=contribution_id,
    )
    if contribution is None:
        raise HTTPException(
            status_code=404,
            detail="Contribution not found",
        )

    # Get allocations for this contribution
    allocations = list_allocations(
        organization_id=org_id,
        contribution_id=contribution_id,
    )

    related_resources = get_contribution_resources(
        organization_id=org_id,
        contribution_id=contribution_id,
    )

    return {
        "contribution": contribution,
        "allocations": allocations,
        **related_resources,
    }
