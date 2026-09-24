# ADR-006 — Immutable domain events

Status: Accepted
Date: 2026-09-24

## Context

If a "committed" event can be edited later, then nothing the system claims
is trustworthy: the on-chain anchor, the reconciliation figures, and the
auditor trail all rest on the append-only property.

## Decision

`domain_events` rows are strictly INSERT-only. Enforced by:

1. Application code: no ORM `UPDATE` / `DELETE` paths for the table.
2. DB trigger `domain_events_forbid_mutation` that raises on any
   `UPDATE`/`DELETE` (migration `019`).
3. RLS: no role has UPDATE/DELETE grants on `domain_events`.

Corrections and reversals are represented as **new** events with a
`provenance_edges` row of relation `CORRECTS` or `REVERSES` pointing to
the prior event.

## Reason

Rulebook Rule 01. The trigger is a belt-and-suspenders defense against
future maintenance mistakes.

## Consequences

- Easier: audit narrative writes itself.
- Harder: schema evolution for old event shapes. Mitigation:
  `schema_version` column and forward-compatible readers.

## Revisit conditions

Never.
