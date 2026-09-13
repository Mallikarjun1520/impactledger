from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.schemas import (
    InventoryItemResponse,
    ResourceBatchCreate,
    ResourceBatchResponse,
    ResourceEventCreate,
    ResourceEventResponse,
    ResourceTypeCreate,
    ResourceTypeResponse,
)
from app.core.authorization import get_current_membership, require_role
from app.core.exceptions import (
    DuplicateBatchCodeError,
    DuplicateResourceTypeError,
    InsufficientInventoryError,
    ResourceBatchNotFoundError,
    ResourceTypeNotFoundError,
)
from app.infrastructure.database.organization_members import OrganizationMembership
from app.infrastructure.database.resources import (
    create_resource_batch,
    create_resource_event,
    create_resource_type,
    get_resource_batch,
    get_resource_type,
    list_organization_inventory,
    list_resource_batches,
    list_resource_events,
    list_resource_types,
)

router = APIRouter()

RESOURCE_TYPE_CREATE_ROLES = ("ADMIN", "OPERATOR")
RESOURCE_BATCH_CREATE_ROLES = ("ADMIN", "OPERATOR")
RESOURCE_EVENT_CREATE_ROLES = ("ADMIN", "OPERATOR", "FIELD_AGENT")


# ---------------------------------------------------------------------------
# Resource Types Endpoints
# ---------------------------------------------------------------------------


@router.post("/resource-types", response_model=ResourceTypeResponse)
def create_resource_type_endpoint(
    data: ResourceTypeCreate,
    membership: OrganizationMembership = Depends(
        require_role(*RESOURCE_TYPE_CREATE_ROLES)
    ),
):
    try:
        return create_resource_type(
            organization_id=membership.organization_id,
            data=data,
        )
    except DuplicateResourceTypeError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/resource-types", response_model=list[ResourceTypeResponse])
def list_resource_types_endpoint(
    membership: OrganizationMembership = Depends(get_current_membership),
):
    return list_resource_types(organization_id=membership.organization_id)


@router.get("/resource-types/{resource_type_id}", response_model=ResourceTypeResponse)
def get_resource_type_endpoint(
    resource_type_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
):
    resource_type = get_resource_type(
        organization_id=membership.organization_id,
        resource_type_id=resource_type_id,
    )
    if resource_type is None:
        raise HTTPException(
            status_code=404,
            detail="Resource type not found",
        )
    return resource_type


# ---------------------------------------------------------------------------
# Resource Batches Endpoints
# ---------------------------------------------------------------------------


@router.post("/resource-batches", response_model=ResourceBatchResponse)
def create_resource_batch_endpoint(
    data: ResourceBatchCreate,
    membership: OrganizationMembership = Depends(
        require_role(*RESOURCE_BATCH_CREATE_ROLES)
    ),
):
    try:
        return create_resource_batch(
            organization_id=membership.organization_id,
            data=data,
            user_id=membership.user_id,
        )
    except ResourceTypeNotFoundError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
    except DuplicateBatchCodeError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/resource-batches", response_model=list[ResourceBatchResponse])
def list_resource_batches_endpoint(
    membership: OrganizationMembership = Depends(get_current_membership),
):
    return list_resource_batches(organization_id=membership.organization_id)


@router.get("/resource-batches/{batch_id}", response_model=ResourceBatchResponse)
def get_resource_batch_endpoint(
    batch_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
):
    batch = get_resource_batch(
        organization_id=membership.organization_id,
        batch_id=batch_id,
    )
    if batch is None:
        raise HTTPException(
            status_code=404,
            detail="Resource batch not found",
        )
    return batch


# ---------------------------------------------------------------------------
# Resource Events Endpoints
# ---------------------------------------------------------------------------


@router.post("/resource-events", response_model=ResourceEventResponse)
def create_resource_event_endpoint(
    data: ResourceEventCreate,
    membership: OrganizationMembership = Depends(
        require_role(*RESOURCE_EVENT_CREATE_ROLES)
    ),
):
    try:
        return create_resource_event(
            organization_id=membership.organization_id,
            data=data,
            performed_by=membership.user_id,
        )
    except ResourceBatchNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )
    except InsufficientInventoryError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get("/resource-events", response_model=list[ResourceEventResponse])
def list_resource_events_endpoint(
    resource_batch_id: UUID | None = Query(None),
    membership: OrganizationMembership = Depends(get_current_membership),
):
    try:
        return list_resource_events(
            organization_id=membership.organization_id,
            resource_batch_id=resource_batch_id,
        )
    except ResourceBatchNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


# ---------------------------------------------------------------------------
# Organization Inventory Endpoint
# ---------------------------------------------------------------------------


@router.get("/inventory", response_model=list[InventoryItemResponse])
def list_inventory_endpoint(
    membership: OrganizationMembership = Depends(get_current_membership),
):
    return list_organization_inventory(organization_id=membership.organization_id)
