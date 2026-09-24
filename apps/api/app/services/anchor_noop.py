"""No-op anchor adapter (default for local dev & tests; ADR-012 requires the
system to keep committing events even when the chain is unavailable)."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from app.services.anchor import AnchorReceipt, AnchorRequest


@dataclass
class NoopAnchorAdapter:
    chain_id: int
    contract_address: str = "0x0000000000000000000000000000000000000000"

    def submit(self, request: AnchorRequest) -> AnchorReceipt:
        # Deterministic pseudo tx-hash so tests can assert on it.
        material = f"{request.batch_id}:{request.merkle_root_hex}:{time.time_ns()}".encode()
        tx_hash = "0x" + hashlib.sha256(material).hexdigest()
        return AnchorReceipt(
            tx_hash=tx_hash,
            block_number=1,               # pretend it landed instantly
            chain_id=self.chain_id,
            contract_address=self.contract_address,
        )

    def confirmed(self, receipt: AnchorReceipt, min_confirmations: int) -> bool:
        return True
