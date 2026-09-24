# ADR-002 — Batch-level physical tracking

Status: Accepted
Date: 2026-09-24

## Context

Relief resources arrive by the pallet: 500 blankets, 2000 food kits. Serial
tracking every item would triple the schema (item / lot / batch), the storage
volume, and the field-agent data entry burden — for questionable operational
gain in the disaster-relief use case.

## Options considered

1. **Serialized items** — one row per physical unit.
2. **Batch only** — one row per received lot, quantities tracked at batch
   level.
3. **Hybrid** — batches by default, opt-in serialization for high-value items.

## Decision

Batch only for MVP. `resource_batches` rows carry a numeric `quantity`;
movement is recorded on `resource_events` referring to a batch.

## Reason

- Matches how relief logistics actually happen: pallets in, pallets out.
- Storage and UX savings are large; verification loss is small at MVP scale.
- The event log preserves per-movement provenance, which is what public
  verification actually needs.

## Consequences

- Easier: bulk operations, faster public projections.
- Harder: recall of a single defective unit within a batch. Documented as
  deferred; the hybrid model in option 3 is a future extension without
  schema surgery to existing tables.

## Revisit conditions

- A partner demands per-item traceability (e.g., serialized pharma).
- A regulator requires it.
