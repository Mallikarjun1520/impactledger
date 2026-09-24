# ADR-004 — Separate financial and physical lifecycles

Status: Accepted
Date: 2026-09-24

## Context

Money and matter have different natural rhythms: money is fungible and moves
through allocations/POs/payments; matter is countable and moves through
receipts/transfers/distributions. Conflating them into a single lifecycle
tempts developers to derive one from the other, which produces silent
inconsistency.

## Decision

Two lifecycles, one bridge:

```
FINANCIAL: contribution → pool → allocation → commitment → PO → payment
PHYSICAL:  receipt → batch → transfer → dispatch → delivery → distribution
BRIDGE:    purchase_order → receipt (creates a resource_batch)
```

## Reason

- Reconciliation stays honest — the system does not invent "cash spent"
  from "items received" (see rulebook §9).
- Taxes, shipping, discounts, packaging live cleanly on the financial side.
- Physical damage / loss does not corrupt financial state.

## Consequences

- Easier: correct discrepancy detection (a PO paid ₹55k, evidence says
  ₹52k → mismatch; distinct from "500 blankets ordered, 480 received").
- Harder: some queries need to join across sides. Views in migration `021`
  precompute the common ones.

## Revisit conditions

None expected. This is a foundational modeling decision.
