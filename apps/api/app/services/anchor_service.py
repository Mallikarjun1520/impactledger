"""Anchor orchestration (rulebook §22, ADR-011).

Composes: pending events → Merkle root → DB batch row → adapter submission →
receipt persistence. Never blocks the request loop on chain latency; the
confirmation check is a separate call (invoked by a scheduled worker or the
public/anchor router).
"""
from __future__ import annotations

import logging
from uuid import UUID

from app.infrastructure.database import anchor as anchor_db
from app.services.anchor import AnchorRequest, build_adapter
from app.services.merkle import merkle_root_hex


log = logging.getLogger(__name__)


def close_and_submit_batch(
    organization_id: UUID,
    contract_address: str,
    chain_id: int,
    max_events: int,
) -> anchor_db.AnchorBatchRow | None:
    """Close a batch of pending events for one org and dispatch to the chain.

    Returns the batch row (in SUBMITTED state) or None if there was nothing to
    do. On submission failure the batch is marked FAILED and member events
    revert to PENDING so a later attempt can retry them.
    """
    pending = anchor_db.fetch_pending_events(organization_id, max_events)
    if not pending:
        return None

    root_hex = merkle_root_hex([e.hash for e in pending])
    batch = anchor_db.create_batch(
        organization_id=organization_id,
        events=pending,
        merkle_root_hex=root_hex,
        chain_id=chain_id,
        contract_address=contract_address or None,
    )

    adapter = build_adapter()
    try:
        receipt = adapter.submit(
            AnchorRequest(
                batch_id=batch.id,
                merkle_root_hex=root_hex,
                event_count=batch.event_count,
            )
        )
    except Exception as exc:                             # noqa: BLE001 — chain layer
        log.exception("Anchor submission failed for batch %s", batch.id)
        anchor_db.mark_failed(batch.id, str(exc)[:500])
        return None

    anchor_db.record_submission(
        batch_id=batch.id,
        tx_hash=receipt.tx_hash,
        block_number=receipt.block_number,
        contract_address=receipt.contract_address,
    )
    return anchor_db.get_batch(batch.id)


def confirm_batch(batch_id: UUID, min_confirmations: int) -> bool:
    """Check chain confirmations; flip batch + member events on success."""
    batch = anchor_db.get_batch(batch_id)
    if batch is None or batch.tx_hash is None or batch.status != "SUBMITTED":
        return False

    adapter = build_adapter()
    from app.services.anchor import AnchorReceipt
    receipt = AnchorReceipt(
        tx_hash=batch.tx_hash,
        block_number=batch.block_number,
        chain_id=batch.chain_id,
        contract_address=batch.contract_address or "",
    )
    if adapter.confirmed(receipt, min_confirmations):
        anchor_db.mark_confirmed(batch.id, batch.block_number or 0)
        return True
    return False
