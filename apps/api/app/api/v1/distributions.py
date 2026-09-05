from fastapi import APIRouter, HTTPException, Depends

from app.api.v1.schemas import DistributionCreate
from app.core.authorization import require_role
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
    if data.organization_id != membership.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Distribution organization does not match X-Organization-ID",
        )

    try:
        distribution_id = create_distribution(data, created_by=membership.user_id)

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
def list_distributions() -> list[dict]:
    return get_distributions()


@router.get("/inventory/{resource_batch_id}")
def inventory(resource_batch_id: str) -> dict[str, str | float]:
    quantity = get_inventory(resource_batch_id)

    return {
        "resource_batch_id": resource_batch_id,
        "available_quantity": quantity,
    }
