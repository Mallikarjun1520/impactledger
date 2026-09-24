# ADR-010 — Blockchain as integrity anchor

Status: Accepted
Date: 2026-09-24

## Context

The rulebook is explicit that blockchain does not prove real-world truth; it
proves that our recorded history has not been silently rewritten. Everything
else the marketing might tempt us into (payments, identity, on-chain
operational state) is scope creep and legal risk.

## Decision

Blockchain performs one job: it stores Merkle roots (one 32-byte hash + a
batch id + a timestamp per anchor tx). Nothing operational goes on-chain.
The contract has one method: `anchorBatch(bytes32 batchId, bytes32 merkleRoot,
uint256 eventCount)`.

## Reason

Rulebook Rule 04, Rule 05, §22.

## Consequences

- Easier: privacy, cost, contract simplicity, testability.
- Harder: cannot use the chain to move money or represent identity. Not a
  goal.

## Revisit conditions

None.
