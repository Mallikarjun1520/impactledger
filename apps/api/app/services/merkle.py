"""RFC 6962-style Merkle tree over SHA-256 leaf hashes (ADR-011).

Leaves are domain-event hashes (already SHA-256 hex). We rehash them under a
domain-separation prefix (``0x00``) to avoid second-preimage attacks, and
combine nodes under ``0x01``. This matches Certificate Transparency's
convention and is trivially reproducible in JavaScript for the browser
verifier (see apps/web/src/lib/merkle.ts).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence


LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_hash(event_hash_hex: str) -> bytes:
    """Compute the Merkle leaf hash for an event whose canonical hash is
    ``event_hash_hex`` (64 hex chars)."""
    raw = bytes.fromhex(event_hash_hex)
    return _sha256(LEAF_PREFIX + raw)


def node_hash(left: bytes, right: bytes) -> bytes:
    return _sha256(NODE_PREFIX + left + right)


def merkle_root(leaves: Sequence[bytes]) -> bytes:
    """Compute the Merkle root of ``leaves`` (already-hashed leaf bytes).

    Odd-length levels duplicate the last node (Bitcoin/CT convention).
    Empty input hashes the empty string with ``SHA256`` per convention.
    """
    if not leaves:
        return _sha256(b"")

    level = list(leaves)
    while len(level) > 1:
        next_level: list[bytes] = []
        it = iter(level)
        for left in it:
            right = next(it, left)  # duplicate last if odd
            next_level.append(node_hash(left, right))
        level = next_level
    return level[0]


@dataclass(frozen=True)
class MerkleProofStep:
    sibling: bytes
    is_right: bool   # True if sibling is on the RIGHT of the current node


def merkle_proof(leaves: Sequence[bytes], index: int) -> list[MerkleProofStep]:
    """Return the sibling path from leaf ``index`` up to the root."""
    if not leaves:
        raise ValueError("Cannot prove membership in empty tree")
    if not (0 <= index < len(leaves)):
        raise IndexError(f"Leaf index {index} out of range 0..{len(leaves)-1}")

    steps: list[MerkleProofStep] = []
    level = list(leaves)
    pos = index
    while len(level) > 1:
        next_level: list[bytes] = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if (i + 1) < len(level) else level[i]
            next_level.append(node_hash(left, right))

        if pos % 2 == 0:
            sibling = level[pos + 1] if (pos + 1) < len(level) else level[pos]
            steps.append(MerkleProofStep(sibling=sibling, is_right=True))
        else:
            steps.append(MerkleProofStep(sibling=level[pos - 1], is_right=False))

        pos //= 2
        level = next_level
    return steps


def verify_proof(leaf: bytes, index: int, proof: Sequence[MerkleProofStep], root: bytes) -> bool:
    """Verify that ``leaf`` at ``index`` produces ``root`` via ``proof``.

    ``index`` is included for parity — the caller must have supplied ``proof``
    with the correct ``is_right`` flags for that index.
    """
    current = leaf
    for step in proof:
        current = node_hash(current, step.sibling) if step.is_right else node_hash(step.sibling, current)
    return current == root


def merkle_root_hex(event_hashes_hex: Sequence[str]) -> str:
    leaves = [leaf_hash(h) for h in event_hashes_hex]
    return merkle_root(leaves).hex()


def merkle_proof_hex(event_hashes_hex: Sequence[str], index: int) -> list[dict]:
    leaves = [leaf_hash(h) for h in event_hashes_hex]
    proof = merkle_proof(leaves, index)
    return [{"sibling": s.sibling.hex(), "is_right": s.is_right} for s in proof]


__all__ = [
    "LEAF_PREFIX",
    "NODE_PREFIX",
    "MerkleProofStep",
    "leaf_hash",
    "node_hash",
    "merkle_root",
    "merkle_proof",
    "verify_proof",
    "merkle_root_hex",
    "merkle_proof_hex",
]
