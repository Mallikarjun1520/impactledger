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