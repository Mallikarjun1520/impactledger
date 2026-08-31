from fastapi import APIRouter, HTTPException

from app.api.v1.schemas import DistributionCreate
from app.infrastructure.database.distributions import (
    create_distribution,
    get_distributions,
    get_inventory,
)

router = APIRouter()


@router.post("/distributions")
def create_distribution_endpoint(
    data: DistributionCreate,
) -> dict[str, str]:
    try:
        distribution_id = create_distribution(data)

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