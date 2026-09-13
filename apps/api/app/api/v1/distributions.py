
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from app.api.v1.schemas import DistributionCreate
from app.core.authorization import get_current_membership, require_role
from app.infrastructure.database.distributions import (
    create_distribution,
    get_distributions,
    get_inventory,
)
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter()

DISTRIBUTION_CREATE_ROLES = ("ADMIN", "OPERATOR", "FIELD_AGENT")


@router.post("/distributions")
def create_distribution_endpoint(
    data: DistributionCreate,
    membership: OrganizationMembership = Depends(
        require_role(*DISTRIBUTION_CREATE_ROLES)
    ),
) -> dict[str, str]:
    try:
        distribution_id = create_distribution(
            data,
            created_by=membership.user_id,
            organization_id=membership.organization_id,
        )

        return {
            "status": "distribution created",
            "distribution_id": distribution_id,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/distributions")
def list_distributions(
    membership: OrganizationMembership = Depends(get_current_membership),
) -> list[dict]:
    return get_distributions(organization_id=membership.organization_id)


@router.get("/inventory/{resource_batch_id}")
def inventory(
    resource_batch_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict[str, str | float]:
    quantity = get_inventory(
        resource_batch_id=resource_batch_id,
        organization_id=membership.organization_id,
    )

    if quantity is None:
        raise HTTPException(
            status_code=404,
            detail="Resource batch not found",
        )

    return {
        "resource_batch_id": str(resource_batch_id),
        "available_quantity": quantity,
    }
