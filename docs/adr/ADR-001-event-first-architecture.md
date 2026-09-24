# ADR-001 — Event-first architecture

Status: Accepted
Date: 2026-09-24

## Context

ImpactLedger's core claim is that it tracks and verifies the *recorded*
lifecycle of funds and resources. A user must be able to answer "what happened
and when did it become so?" for any figure the system displays.

## Options considered

1. **State-first (CRUD)** — mutate rows for contributions, allocations, etc.
   Cheap, but destroys history; corrections overwrite.
2. **State-first + audit table** — keep a side audit log. Better, but the
   canonical figures still come from mutable rows, and the audit log is not
   the source of truth.
3. **Event-first (chosen)** — all state changes are appended as immutable
   `domain_events` rows; operational tables are read-optimized projections.

## Decision

Every state-changing operation writes exactly one `domain_events` row inside
the same transaction as the operational INSERT. The event's `canonical_json`
is the record; operational tables are projections that can be rebuilt from
the event log.

## Reason

- Corrections and reversals become new events referring to old ones — the
  history is preserved (rulebook Rule 01).
- The event stream feeds Merkle batching (ADR-011) trivially.
- Auditors and public verifiers only need to trust the append-only log plus
  the on-chain root.

## Consequences

- Easier: replaying history, reconciling, blockchain anchoring, auditor UX.
- Harder: schema changes to event shapes require versioning + a migration
  strategy. Mitigation: `domain_events.schema_version` column.

## Revisit conditions

If write throughput ever exceeds ~1000 events/sec on the free-tier DB, we
would consider outbox → external event store. Not a concern for MVP.
