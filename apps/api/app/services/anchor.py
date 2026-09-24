"""Blockchain anchor adapter interface (rulebook §22, ADR-010, ADR-012).

The core is deliberately chain-agnostic: the FastAPI monolith only knows how
to hand a batch to an adapter and record the resulting tx.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class AnchorReceipt:
    tx_hash: str
    block_number: int | None            # None while pending inclusion
    chain_id: int
    contract_address: str


@dataclass(frozen=True)
class AnchorRequest:
    batch_id: UUID
    merkle_root_hex: str                 # 64 hex chars
    event_count: int


class AnchorAdapter(Protocol):
    """Adapter contract. Implementations MUST NOT raise on transient RPC
    errors below the confirmation threshold; return a receipt with
    ``block_number = None`` so the caller can retry the confirmation check."""

    def submit(self, request: AnchorRequest) -> AnchorReceipt: ...

    def confirmed(self, receipt: AnchorReceipt, min_confirmations: int) -> bool: ...


def build_adapter() -> AnchorAdapter:
    """Construct the configured adapter. Kept lazy so tests can override."""
    from app.core.config import settings

    if settings.anchor_adapter == "evm":
        from app.services.anchor_evm import EvmAnchorAdapter
        return EvmAnchorAdapter(
            rpc_url=settings.anchor_rpc_url,
            chain_id=settings.anchor_chain_id,
            contract_address=settings.anchor_contract_address,
            private_key=settings.anchor_runtime_private_key,
        )
    from app.services.anchor_noop import NoopAnchorAdapter
    return NoopAnchorAdapter(chain_id=settings.anchor_chain_id)


__all__ = [
    "AnchorReceipt",
    "AnchorRequest",
    "AnchorAdapter",
    "build_adapter",
]
