from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class DistributionCreate(BaseModel):
    relief_event_id: UUID
    resource_batch_id: UUID
    organization_id: UUID
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