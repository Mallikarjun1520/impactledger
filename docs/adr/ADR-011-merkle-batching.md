# ADR-011 — Merkle batching

Status: Accepted
Date: 2026-09-24

## Context

Anchoring one blockchain tx per domain event is prohibitively expensive
(rulebook §22) and wastes finality latency. Merkle batching lets us prove
individual event integrity with an O(log n) proof against a single anchored
root.

## Decision

- A scheduled backend job runs every `ANCHOR_BATCH_INTERVAL_SECONDS`
  (default 300s) and any time an org reaches `ANCHOR_MAX_PENDING_EVENTS`
  (default 512).
- It closes a batch of `domain_events` in `anchor_status = 'PENDING'`,
  computes `merkle_root = merkle(sha256(canonical_json_i))` using RFC 6962
  double-hashing (SHA-256, `0x00` for leaves, `0x01` for internal nodes),
  writes an `anchor_batches` row, and dispatches to the EVM adapter.
- On confirmation, `anchor_batches.status = 'CONFIRMED'` with the tx hash
  and block number; member events have `anchor_status = 'ANCHORED'`.
- The client verifier reconstructs `sha256(canonical_json)`, walks the
  Merkle proof, and compares against the on-chain root read from
  `ImpactAnchor.getRoot(batchId)`.

## Reason

- Cost: one tx anchors thousands of events.
- Privacy: only hashes leave the platform.
- Verifiability: standard, well-analyzed construction (Certificate
  Transparency uses it).

## Consequences

- Easier: cost, privacy, batching semantics.
- Harder: verification requires the platform to serve the leaf +
  intermediate hashes. Documented and served under
  `GET /public/anchors/{batch_id}/proof/{event_id}`.

## Revisit conditions

If a partner requires a different Merkle convention (e.g., OpenZeppelin
`MerkleProof.sol` default), we would add an alternate scheme flagged per
batch. RFC 6962 is the default because it is domain-separated and immune
to second-preimage attacks that plain unordered hash trees admit.
