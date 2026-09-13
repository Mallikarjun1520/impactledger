
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class DistributionCreate(BaseModel):
    relief_event_id: UUID
    resource_batch_id: UUID
    quantity: float = Field(gt=0)
    destination: str
    beneficiary_count: int = Field(ge=0)
    notes: str | None = None


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None


class OrganizationRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    FIELD_AGENT = "FIELD_AGENT"
    AUDITOR = "AUDITOR"
    DONOR = "DONOR"
    VIEWER = "VIEWER"


class OrganizationMemberCreate(BaseModel):
    user_id: UUID
    role: OrganizationRole


class OrganizationMemberUpdate(BaseModel):
    role: OrganizationRole


# ---------------------------------------------------------------------------
# Day 2: Resource Types, Batches, Events, Contributions, Allocations, Inventory
# ---------------------------------------------------------------------------


class ResourceTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    unit: str = Field(min_length=1, max_length=50)
    description: str | None = None


class ResourceTypeResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    unit: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class ResourceBatchCreate(BaseModel):
    resource_type_id: UUID
    batch_code: str = Field(min_length=1, max_length=100)
    quantity: float = Field(gt=0)
    source_description: str | None = None
    location: str | None = None


class ResourceBatchResponse(BaseModel):
    id: UUID
    resource_type_id: UUID
    organization_id: UUID
    batch_code: str
    quantity: float
    source_description: str | None = None
    received_at: datetime
    location: str | None = None
    created_at: datetime
    updated_at: datetime


class ResourceEventType(str, Enum):
    RECEIVED = "RECEIVED"
    TRANSFER_OUT = "TRANSFER_OUT"
    TRANSFER_IN = "TRANSFER_IN"
    DISTRIBUTED = "DISTRIBUTED"
    DAMAGED = "DAMAGED"
    ADJUSTED = "ADJUSTED"


class ResourceEventCreate(BaseModel):
    resource_batch_id: UUID
    event_type: ResourceEventType
    quantity: float = Field(gt=0)
    location: str = Field(min_length=1)
    reason: str | None = None
    transfer_id: UUID | None = None


class ResourceEventResponse(BaseModel):
    id: UUID
    resource_batch_id: UUID
    event_type: ResourceEventType
    quantity: float
    location: str
    performed_by: UUID | None = None
    reason: str | None = None
    transfer_id: UUID | None = None
    created_at: datetime


class ContributionVisibility(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    ANONYMOUS = "ANONYMOUS"


class ContributionStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class ContributionCreate(BaseModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    visibility: ContributionVisibility = ContributionVisibility.PRIVATE
    status: ContributionStatus = ContributionStatus.PENDING
    contributor_user_id: UUID | None = None
    received_at: datetime | None = None


class ContributionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    contributor_user_id: UUID | None = None
    amount: float
    currency: str
    visibility: ContributionVisibility
    status: ContributionStatus
    received_at: datetime | None = None
    created_at: datetime


class AllocationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"


class AllocationCreate(BaseModel):
    contribution_id: UUID
    amount: float = Field(gt=0)
    purpose: str = Field(min_length=1)
    status: AllocationStatus = AllocationStatus.PENDING


class AllocationResponse(BaseModel):
    id: UUID
    contribution_id: UUID
    organization_id: UUID
    amount: float
    purpose: str
    status: AllocationStatus
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class InventoryItemResponse(BaseModel):
    resource_batch_id: UUID
    batch_code: str
    resource_type_id: UUID
    resource_type_name: str
    unit: str
    available_quantity: float