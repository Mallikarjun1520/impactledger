"""Pydantic schemas for the rulebook-aligned modules added in slice 1.

Kept separate from the legacy ``schemas.py`` so existing tests don't move.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InitiativeStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class InitiativeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    category: str | None = Field(default=None, max_length=64)


class InitiativeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str | None
    category: str | None
    status: InitiativeStatus
    starts_at: datetime | None
    closes_at: datetime | None
    created_at: datetime


class RestrictionScope(str, Enum):
    UNRESTRICTED = "UNRESTRICTED"
    INITIATIVE = "INITIATIVE"
    CATEGORY = "CATEGORY"


class FundPoolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    restriction_scope: RestrictionScope = RestrictionScope.UNRESTRICTED
    initiative_id: UUID | None = None
    category: str | None = Field(default=None, max_length=64)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class FundPoolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: str | None
    restriction_scope: RestrictionScope
    initiative_id: UUID | None
    category: str | None
    currency: str
    is_closed: bool
    created_at: datetime


class PoolContributionCreate(BaseModel):
    fund_pool_id: UUID
    amount: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="INR", min_length=3, max_length=3)
    visibility: str = Field(default="PRIVATE", pattern=r"^(PUBLIC|PRIVATE|ANONYMOUS)$")
    contributor_metadata: dict | None = None       # PII; RLS-protected
    external_reference: str | None = None

    @field_validator("amount")
    @classmethod
    def _quantize(cls, v: Decimal) -> Decimal:
        # Enforce 2-decimal money precision to keep hashing deterministic.
        return v.quantize(Decimal("0.01"))


class PoolAllocationCreate(BaseModel):
    fund_pool_id: UUID
    amount: Decimal = Field(gt=Decimal("0"))
    purpose: str = Field(min_length=1)
    initiative_id: UUID | None = None
    purpose_category: str | None = Field(default=None, max_length=64)

    @field_validator("amount")
    @classmethod
    def _quantize(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))


class CommitmentCreate(BaseModel):
    allocation_id: UUID
    vendor_id: UUID | None = None
    amount: Decimal = Field(gt=Decimal("0"))
    description: str = Field(min_length=1)


class CommitmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    allocation_id: UUID
    vendor_id: UUID | None
    amount: Decimal
    currency: str
    description: str
    status: str
    created_at: datetime


class PurchaseOrderLineItem(BaseModel):
    description: str
    quantity: Decimal = Field(gt=Decimal("0"))
    unit_price: Decimal = Field(ge=Decimal("0"))
    resource_type_id: UUID | None = None


class PurchaseOrderCreate(BaseModel):
    commitment_id: UUID
    vendor_id: UUID
    po_number: str = Field(min_length=1, max_length=64)
    total_amount: Decimal = Field(gt=Decimal("0"))
    tax_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    shipping_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    line_items: list[PurchaseOrderLineItem] = Field(default_factory=list)


class PaymentCreate(BaseModel):
    purchase_order_id: UUID
    amount: Decimal = Field(gt=Decimal("0"))
    method: str = Field(pattern=r"^(BANK_TRANSFER|UPI|CARD|CASH|CHEQUE|OTHER)$")
    reference: str | None = None
    paid_at: datetime | None = None


class EvidenceUploadResponse(BaseModel):
    id: UUID
    organization_id: UUID
    kind: str
    filename: str
    content_type: str
    size_bytes: int
    content_sha256: str
    storage_path: str
    status: str
    uploaded_at: datetime


class AnchorBatchResponse(BaseModel):
    id: UUID
    organization_id: UUID
    merkle_root: str
    event_count: int
    chain_id: int
    contract_address: str | None
    tx_hash: str | None
    block_number: int | None
    status: str
    submitted_at: datetime | None
    confirmed_at: datetime | None


class MerkleProofStepDto(BaseModel):
    sibling: str
    is_right: bool


class MerkleProofResponse(BaseModel):
    batch_id: UUID
    event_id: UUID
    leaf_hash: str
    leaf_index: int
    merkle_root: str
    proof: list[MerkleProofStepDto]
