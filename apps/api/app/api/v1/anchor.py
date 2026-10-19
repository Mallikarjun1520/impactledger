from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas_v2 import (
    AnchorBatchResponse,
    MerkleProofResponse,
    MerkleProofStepDto,
)
from app.core.authorization import get_current_membership
from app.core.config import settings
from app.infrastructure.database import anchor as anchor_db
from app.infrastructure.database.organization_members import OrganizationMembership
from app.services import anchor_service
from app.services.merkle import merkle_proof_hex, merkle_root_hex

router = APIRouter(prefix="/organizations/{org_id}/anchor", tags=["anchor"])


@router.post("/batches", response_model=AnchorBatchResponse, status_code=status.HTTP_201_CREATED)
def close_batch(
    org_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> AnchorBatchResponse:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if membership.role not in ("ADMIN", "AUDITOR", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")

    batch = anchor_service.close_and_submit_batch(
        organization_id=org_id,
        contract_address=settings.anchor_contract_address,
        chain_id=settings.anchor_chain_id,
        max_events=settings.anchor_max_pending_events,
        performed_by=membership.user_id,
    )
    if batch is None:
        raise HTTPException(status_code=409, detail="No pending events or submission failed")
    return AnchorBatchResponse(
        id=batch.id,
        organization_id=batch.organization_id,
        merkle_root=batch.merkle_root,
        event_count=batch.event_count,
        chain_id=batch.chain_id,
        contract_address=batch.contract_address,
        tx_hash=batch.tx_hash,
        block_number=batch.block_number,
        status=batch.status,
        submitted_at=batch.submitted_at,
        confirmed_at=batch.confirmed_at,
    )


@router.post("/batches/{batch_id}/confirm", response_model=AnchorBatchResponse)
def confirm(
    org_id: UUID,
    batch_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> AnchorBatchResponse:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    if membership.role not in ("ADMIN", "AUDITOR", "OPERATOR"):
        raise HTTPException(status_code=403, detail="Insufficient role")

    batch = anchor_db.get_batch(batch_id)
    if batch is None or batch.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Batch not found")
    anchor_service.confirm_batch(batch_id, settings.anchor_confirmations_required)
    batch = anchor_db.get_batch(batch_id)
    if batch is None or batch.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Batch not found")
    return AnchorBatchResponse(
        id=batch.id,
        organization_id=batch.organization_id,
        merkle_root=batch.merkle_root,
        event_count=batch.event_count,
        chain_id=batch.chain_id,
        contract_address=batch.contract_address,
        tx_hash=batch.tx_hash,
        block_number=batch.block_number,
        status=batch.status,
        submitted_at=batch.submitted_at,
        confirmed_at=batch.confirmed_at,
    )


@router.get("/batches/{batch_id}/proof/{event_id}", response_model=MerkleProofResponse)
def proof(
    org_id: UUID,
    batch_id: UUID,
    event_id: UUID,
    membership: OrganizationMembership = Depends(get_current_membership),
) -> MerkleProofResponse:
    if membership.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Org mismatch")
    batch = anchor_db.get_batch(batch_id)
    if batch is None or batch.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Batch not found")

    leaves = anchor_db.get_batch_leaves(batch_id)
    idx = anchor_db.get_leaf_index(batch_id, event_id)
    if idx is None:
        raise HTTPException(status_code=404, detail="Event not in this batch")

    root_hex = merkle_root_hex(leaves)
    proof_steps = [MerkleProofStepDto(**s) for s in merkle_proof_hex(leaves, idx)]
    return MerkleProofResponse(
        batch_id=batch_id,
        event_id=event_id,
        leaf_hash=leaves[idx],
        leaf_index=idx,
        merkle_root=root_hex,
        proof=proof_steps,
    )
