# ADR-003 — Fund Pools for micro-donations

Status: Accepted
Date: 2026-09-24

## Context

An emergency campaign can produce tens of thousands of ₹40–₹1,000 donations.
Anchoring one blockchain transaction per contribution is economically and
technically infeasible, and downstream reconciliation would drown in noise.

## Options considered

1. **1:1 allocation** — each contribution funds specific expenses. Simple,
   dishonest at scale (donor ₹50 does not "buy" a specific item).
2. **Fund pools** — logically compatible contributions aggregate into a pool;
   allocations draw from the pool.
3. **Global org bucket** — one bucket per org. Loses restriction semantics.

## Decision

Option 2. `fund_pools` groups contributions with compatible restrictions
(unrestricted / initiative-scoped / category-scoped). Allocations draw from
a pool, not from individual contributions.

## Reason

- Reflects reality: money is fungible within its restriction scope.
- Anchoring compacts naturally.
- Micro-donations remain individually traceable up to the pool level
  (rulebook §6 fungibility rule).

## Consequences

- Easier: batching, invariant checks, dashboard aggregations.
- Harder: reporting on "where did *my* ₹50 go" — surfaced as "your ₹50 went
  into Pool X, which funded these purchases".

## Revisit conditions

If donors regulatorily require dollar-for-dollar traceability, we would add
an optional stronger `contribution_lineage` table alongside — not replace.
