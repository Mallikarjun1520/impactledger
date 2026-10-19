from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas_v2 import (
    CommitmentCreate,
    CommitmentResponse,
    PaymentCreate,
    PurchaseOrderCreate,
)
from app.core.authorization import get_current_membership
from app.domain.invariants import InvariantViolation
from app.infrastructure.database import finance as finance_db
from app.infrastructure.database.audit_logs import create_audit_event
from app.infrastructure.database.organization_members import OrganizationMembership

router = APIRouter(prefix="/organizations/{org_id}", tags=["procurement"])


def _require_org(membership: OrganizationMembership, org_id: UUID) -> None:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")


@router.post("/commitments", response_model=CommitmentResponse, status_code=201)
def create_commitment(
    org_id: UUID,
    body: CommitmentCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> CommitmentResponse:
    _require_org(membership, org_id)
    if membership.role not in ("ADMIN", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    try:
        row = finance_db.create_commitment(
            org_id=org_id,
            user_id=membership.user_id,
            allocation_id=body.allocation_id,
            vendor_id=body.vendor_id,
            amount=body.amount,
            description=body.description,
        )
    except InvariantViolation as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return CommitmentResponse(**row)


@router.post("/purchase-orders", status_code=201)
def create_purchase_order(
    org_id: UUID,
    body: PurchaseOrderCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    _require_org(membership, org_id)
    if membership.role not in ("ADMIN", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    try:
        return finance_db.create_purchase_order(
            org_id=org_id,
            user_id=membership.user_id,
            commitment_id=body.commitment_id,
            vendor_id=body.vendor_id,
            po_number=body.po_number,
            total_amount=body.total_amount,
            tax_amount=body.tax_amount,
            shipping_amount=body.shipping_amount,
            line_items=[li.model_dump(mode="json") for li in body.line_items],
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/purchase-orders/{po_id}/approve", status_code=200)
def approve_purchase_order(
    org_id: UUID,
    po_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    _require_org(membership, org_id)
    if membership.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN may approve POs")
    create_audit_event(
        organization_id=org_id,
        event_type="PO_APPROVAL_ATTEMPTED",
        user_id=membership.user_id,
        details={
            "entity_type": "purchase_order",
            "entity_id": str(po_id),
        },
    )
    try:
        finance_db.approve_purchase_order(
            org_id=org_id,
            approving_user_id=membership.user_id,
            po_id=po_id,
        )
    except InvariantViolation as e:
        if e.rule == "S.1":
            create_audit_event(
                organization_id=org_id,
                event_type="PO_APPROVAL_DENIED_SELF",
                user_id=membership.user_id,
                details={
                    "entity_type": "purchase_order",
                    "entity_id": str(po_id),
                    "reason": str(e),
                },
            )
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "APPROVED"}


@router.post("/payments", status_code=201)
def record_payment(
    org_id: UUID,
    body: PaymentCreate,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> dict:
    _require_org(membership, org_id)
    if membership.role not in ("ADMIN", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    try:
        return finance_db.record_payment(
            org_id=org_id,
            user_id=membership.user_id,
            po_id=body.purchase_order_id,
            amount=body.amount,
            method=body.method,
            reference=body.reference,
        )
    except InvariantViolation as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
