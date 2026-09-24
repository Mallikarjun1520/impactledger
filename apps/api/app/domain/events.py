"""Domain event vocabulary (rulebook §10, migration 016)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class DomainEventType(str, Enum):
    CONTRIBUTION_RECORDED = "CONTRIBUTION_RECORDED"
    CONTRIBUTION_CANCELLED = "CONTRIBUTION_CANCELLED"
    FUND_POOL_CREATED = "FUND_POOL_CREATED"
    ALLOCATION_RECORDED = "ALLOCATION_RECORDED"
    ALLOCATION_CANCELLED = "ALLOCATION_CANCELLED"
    COMMITMENT_CREATED = "COMMITMENT_CREATED"
    COMMITMENT_CANCELLED = "COMMITMENT_CANCELLED"
    PURCHASE_ORDER_CREATED = "PURCHASE_ORDER_CREATED"
    PURCHASE_ORDER_APPROVED = "PURCHASE_ORDER_APPROVED"
    PURCHASE_ORDER_CANCELLED = "PURCHASE_ORDER_CANCELLED"
    PAYMENT_RECORDED = "PAYMENT_RECORDED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"
    RESOURCE_RECEIVED = "RESOURCE_RECEIVED"
    RESOURCE_TRANSFERRED = "RESOURCE_TRANSFERRED"
    RESOURCE_DISPATCHED = "RESOURCE_DISPATCHED"
    RESOURCE_DELIVERED = "RESOURCE_DELIVERED"
    RESOURCE_DISTRIBUTED = "RESOURCE_DISTRIBUTED"
    RESOURCE_LOST = "RESOURCE_LOST"
    RESOURCE_DAMAGED = "RESOURCE_DAMAGED"
    RESOURCE_DISPOSED = "RESOURCE_DISPOSED"
    RESOURCE_ADJUSTED = "RESOURCE_ADJUSTED"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
    EVIDENCE_LINKED = "EVIDENCE_LINKED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    CORRECTION_RECORDED = "CORRECTION_RECORDED"
    REVERSAL_RECORDED = "REVERSAL_RECORDED"


@dataclass(frozen=True)
class DomainEventInput:
    """A domain event ready to be canonicalized, hashed, and inserted."""
    organization_id: UUID
    event_type: DomainEventType
    aggregate_type: str
    aggregate_id: UUID | None
    performed_by: UUID | None
    payload: dict[str, Any]
    schema_version: int = 1

    def canonical_payload(self, seq: int, prev_hash: str | None,
                          occurred_at: datetime | None = None) -> dict[str, Any]:
        """Return the exact JSON that will be hashed.

        The canonical payload deliberately excludes ``id`` (assigned by the DB),
        ``created_at`` (server clock), and includes ``occurred_at`` supplied by
        the caller so the same event serialized in two languages produces the
        same hash.
        """
        occurred = occurred_at or datetime.now(timezone.utc)
        return {
            "aggregate_id": str(self.aggregate_id) if self.aggregate_id else None,
            "aggregate_type": self.aggregate_type,
            "event_type": self.event_type.value,
            "occurred_at": occurred.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "organization_id": str(self.organization_id),
            "payload": self.payload,
            "performed_by": str(self.performed_by) if self.performed_by else None,
            "prev_hash": prev_hash,
            "schema_version": self.schema_version,
            "seq": seq,
        }


def coerce_amount(value: Any) -> Decimal:
    """Normalize a numeric input to Decimal for hashing.

    Floats are rejected upstream by the hasher, so we reject them here too
    with a clear message.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        return Decimal(value)
    raise TypeError(
        "Amount must be Decimal, int, or numeric string; got "
        f"{type(value).__name__}"
    )


__all__ = [
    "DomainEventType",
    "DomainEventInput",
    "coerce_amount",
]
